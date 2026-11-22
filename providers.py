"""
providers.py - Everything that talks to the LLM providers lives here.

This file knows HOW to call OpenAI, Gemini and Claude. It does NOT know
anything about menus or user input; that's main.py's job.

The single public entry point is ask_provider(provider_name, prompt).
Whichever provider you pick, it always returns the same dictionary
shape (see build_result), so main.py can display any provider's answer
with the same code.
"""

import logging
import os
import time
from pathlib import Path

import anthropic
import openai
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

# Load the .env file that sits next to this file. Using an absolute path
# means it works even if you run `python main.py` from another folder.
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

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

# Values in .env.example start with this, e.g. "your_openai_api_key".
# A value that still starts with it hasn't been filled in yet.
PLACEHOLDER_PREFIX = "your_"


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

def get_config_problems(provider_name):
    """
    Return a list of human-readable problems with a provider's configuration.
    An empty list means the API key and model are both set.
    """
    settings = PROVIDER_SETTINGS[provider_name]
    problems = []
    for variable in (settings["key_variable"], settings["model_variable"]):
        value = os.getenv(variable, "").strip()
        if not value:
            problems.append(f"{variable} is not set in your .env file")
        elif value.startswith(PLACEHOLDER_PREFIX):
            problems.append(f"{variable} still has the placeholder value from .env.example")
    return problems


def is_configured(provider_name):
    """True if the provider has a real API key and model name set."""
    return not get_config_problems(provider_name)


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
# Error handling
# ---------------------------------------------------------------------------

def get_http_status(error):
    """
    Return the HTTP status code carried by an SDK error, or None.

    OpenAI and Anthropic put it in `.status_code`; Google's SDK uses `.code`.
    Reading it in one place lets us treat all three providers' errors alike.
    """
    if isinstance(error, (openai.APIStatusError, anthropic.APIStatusError)):
        return error.status_code
    if isinstance(error, genai_errors.APIError):
        return error.code
    return None


def get_error_family_names(error):
    """
    Return the class names of an error and all of its parent classes.

    OpenAI and Anthropic wrap network problems in their own error classes,
    but Google's SDK lets the HTTP library's errors (e.g. "ReadTimeout",
    a kind of "TimeoutException") pass straight through. Checking names
    lets us recognize those without importing the HTTP library ourselves.
    """
    return {cls.__name__ for cls in type(error).__mro__}


def classify_error(error):
    """
    Turn any exception into (category, friendly_message).

    The friendly message never includes the raw SDK message, because raw
    messages can contain request details or part of an API key.
    """
    family_names = get_error_family_names(error)

    # Check timeouts first: in the OpenAI/Anthropic SDKs a timeout error is
    # a special kind of connection error, so the order matters.
    if (isinstance(error, (openai.APITimeoutError, anthropic.APITimeoutError, TimeoutError))
            or "TimeoutException" in family_names):
        return "timeout", "the request timed out. The provider may be slow; please try again."

    if (isinstance(error, (openai.APIConnectionError, anthropic.APIConnectionError, ConnectionError))
            or "NetworkError" in family_names):
        return "network", "could not connect to the provider. Check your internet connection."

    status = get_http_status(error)
    if status == 400:
        return "invalid_request", "the request was rejected as invalid (HTTP 400). Check your prompt and model settings."
    if status == 401:
        return "authentication", "authentication failed (HTTP 401). Check that your API key is correct."
    if status == 403:
        return "permission", "access denied (HTTP 403). Your key may not have access to this model."
    if status == 404:
        return "not_found", "model not found (HTTP 404). Check the model name in your .env file."
    if status == 429:
        return "rate_limit", "API rate limit or quota reached (HTTP 429). Please try again later."
    if status is not None and status >= 500:
        return "server_error", f"the provider had a server error (HTTP {status}). Please try again later."
    if status is not None:
        return "api_error", f"the provider returned an error (HTTP {status})."

    return "unexpected", f"an unexpected error occurred ({type(error).__name__})."


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ask_provider(provider_name, prompt):
    """
    Send `prompt` to one provider and return a standardized result dictionary.

    This function never raises: every failure is caught and returned as an
    error result, so one broken provider can't crash the app.
    """
    api_key, model = get_api_key_and_model(provider_name)
    model_label = model or "not configured"

    # 1. Stop early with a clear message if the .env file is incomplete.
    problems = get_config_problems(provider_name)
    if problems:
        logger.warning("%s not configured: %s", provider_name, "; ".join(problems))
        message = f"{provider_name} is not configured: " + "; ".join(problems) + "."
        return build_result(provider_name, model_label, error=message)

    # We log the prompt's length, not its content, to protect user data.
    logger.info("Request started | provider=%s | model=%s | prompt_chars=%d",
                provider_name, model, len(prompt))

    # 2. Call the provider and time how long it takes.
    provider_function = PROVIDER_FUNCTIONS[provider_name]
    start_time = time.perf_counter()
    try:
        text, input_tokens, output_tokens = provider_function(prompt, api_key, model)
    except Exception as error:  # Catch everything so the app keeps running.
        latency = round(time.perf_counter() - start_time, 2)
        category, friendly_message = classify_error(error)
        logger.error("Request failed | provider=%s | model=%s | category=%s | error_type=%s | seconds=%.2f",
                     provider_name, model, category, type(error).__name__, latency)
        return build_result(provider_name, model, latency_seconds=latency,
                            error=f"{provider_name} request failed: {friendly_message}")

    latency = round(time.perf_counter() - start_time, 2)

    # 3. A successful HTTP call can still come back with no text.
    if not text:
        logger.warning("Empty response | provider=%s | model=%s | seconds=%.2f",
                       provider_name, model, latency)
        return build_result(
            provider_name, model, latency_seconds=latency,
            input_tokens=input_tokens, output_tokens=output_tokens,
            error=f"{provider_name} returned no text. The answer may have been blocked or cut off.",
        )

    logger.info("Request completed | provider=%s | model=%s | seconds=%.2f | input_tokens=%s | output_tokens=%s",
                provider_name, model, latency, input_tokens, output_tokens)
    return build_result(provider_name, model, text=text, latency_seconds=latency,
                        input_tokens=input_tokens, output_tokens=output_tokens)
