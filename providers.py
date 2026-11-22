"""
providers.py - Everything that talks to the LLM providers lives here.

This file knows HOW to call OpenAI, Gemini and Claude. It does NOT know
anything about menus or user input; that's main.py's job.

The single public entry point is ask_provider(provider_name, prompt).
Whichever provider you pick, it always returns the same dictionary
shape (see build_result), so main.py can display any provider's answer
with the same code.
"""

import os
from pathlib import Path

import anthropic
import openai
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

# Load the .env file that sits next to this file. Using an absolute path
# means it works even if you run `python main.py` from another folder.
load_dotenv(Path(__file__).parent / ".env")

# How long to wait for a provider before giving up.
REQUEST_TIMEOUT_SECONDS = 60

# Claude's Messages API requires you to set an upper limit on output length.
CLAUDE_MAX_OUTPUT_TOKENS = 1024

# Which environment variables hold each provider's settings.
# The order here is also the order used in "compare all" mode.
PROVIDER_SETTINGS = {
    "OpenAI": {"key_variable": "OPENAI_API_KEY", "model_variable": "OPENAI_MODEL"},
    "Gemini": {"key_variable": "GEMINI_API_KEY", "model_variable": "GEMINI_MODEL"},
    "Claude": {"key_variable": "ANTHROPIC_API_KEY", "model_variable": "ANTHROPIC_MODEL"},
}

PROVIDER_NAMES = list(PROVIDER_SETTINGS.keys())

# ---------------------------------------------------------------------------
# Standardized result
# ---------------------------------------------------------------------------

def build_result(provider, model, text=None, latency_seconds=None,
                 input_tokens=None, output_tokens=None, error=None):
    """
    Build the common result dictionary that every provider returns.

    Each SDK returns a completely different response object. Converting them
    all into this one shape is what lets main.py treat providers the same.
    Values we don't know stay None; we never invent numbers.
    """
    return {
        "provider": provider,
        "model": model,
        "text": text,
        "latency_seconds": latency_seconds,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "status": "error" if error else "success",
        "error": error,
    }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_api_key_and_model(provider_name):
    """Read a provider's API key and model name from the environment."""
    settings = PROVIDER_SETTINGS[provider_name]
    api_key = os.getenv(settings["key_variable"], "").strip()
    model = os.getenv(settings["model_variable"], "").strip()
    return api_key, model


# ---------------------------------------------------------------------------
# Provider-specific calls
#
# Each function below does exactly one thing: send the prompt using that
# provider's official SDK and pull out (text, input_tokens, output_tokens).
# Timing, logging and error handling are done once, in ask_provider().
# ---------------------------------------------------------------------------

def call_openai(prompt, api_key, model):
    """Send a prompt to OpenAI using the Responses API."""
    client = openai.OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)

    response = client.responses.create(model=model, input=prompt)

    # output_text is a convenience property that joins all text output together.
    text = response.output_text
    usage = response.usage  # Can be None, so check before reading it.
    input_tokens = usage.input_tokens if usage else None
    output_tokens = usage.output_tokens if usage else None
    return text, input_tokens, output_tokens


def call_gemini(prompt, api_key, model):
    """Send a prompt to Google Gemini using the Google Gen AI SDK."""
    # The Gen AI SDK measures its timeout in milliseconds.
    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000),
    )

    response = client.models.generate_content(model=model, contents=prompt)

    # response.text is None when Gemini returns no text, for example
    # when a safety filter blocks the answer.
    text = response.text
    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count if usage else None
    output_tokens = usage.candidates_token_count if usage else None
    return text, input_tokens, output_tokens


def call_claude(prompt, api_key, model):
    """Send a prompt to Anthropic Claude using the Messages API."""
    client = anthropic.Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)

    response = client.messages.create(
        model=model,
        max_tokens=CLAUDE_MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    # Claude's answer is a list of "content blocks". We keep only the text blocks.
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    input_tokens = usage.input_tokens if usage else None
    output_tokens = usage.output_tokens if usage else None
    return text, input_tokens, output_tokens


# Maps each provider name to the function that calls it. This dictionary is
# why main.py never needs an if/elif chain to pick a provider.
PROVIDER_FUNCTIONS = {
    "OpenAI": call_openai,
    "Gemini": call_gemini,
    "Claude": call_claude,
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ask_provider(provider_name, prompt):
    """Send `prompt` to one provider and return a standardized result dictionary."""
    api_key, model = get_api_key_and_model(provider_name)
    provider_function = PROVIDER_FUNCTIONS[provider_name]
    text, input_tokens, output_tokens = provider_function(prompt, api_key, model)
    return build_result(provider_name, model, text=text,
                        input_tokens=input_tokens, output_tokens=output_tokens)
