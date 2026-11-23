"""Provider layer: calls OpenAI, Gemini and Claude and returns one common result format."""

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

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60
CLAUDE_MAX_OUTPUT_TOKENS = 1024  # Required by the Messages API.

# Order here is also the order used in compare mode.
PROVIDER_SETTINGS = {
    "OpenAI": {"key_variable": "OPENAI_API_KEY", "model_variable": "OPENAI_MODEL"},
    "Gemini": {"key_variable": "GEMINI_API_KEY", "model_variable": "GEMINI_MODEL"},
    "Claude": {"key_variable": "ANTHROPIC_API_KEY", "model_variable": "ANTHROPIC_MODEL"},
}

PROVIDER_NAMES = list(PROVIDER_SETTINGS.keys())

# Values copied unchanged from .env.example start with this.
PLACEHOLDER_PREFIX = "your_"


def build_result(provider, model, text=None, latency_seconds=None,
                 input_tokens=None, output_tokens=None, error=None):
    """Common result dict returned for every provider. Unknown values stay None."""
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


# --- Configuration ---------------------------------------------------------

def get_config_problems(provider_name):
    """Return a list of missing or placeholder settings (empty if configured)."""
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
    return not get_config_problems(provider_name)


def get_api_key_and_model(provider_name):
    settings = PROVIDER_SETTINGS[provider_name]
    api_key = os.getenv(settings["key_variable"], "").strip()
    model = os.getenv(settings["model_variable"], "").strip()
    return api_key, model


# --- Provider calls ---------------------------------------------------------
# Each returns (text, input_tokens, output_tokens). Timing, logging and
# error handling happen once, in ask_provider().

def call_openai(prompt, api_key, model):
    client = openai.OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
    response = client.responses.create(model=model, input=prompt)

    usage = response.usage
    input_tokens = usage.input_tokens if usage else None
    output_tokens = usage.output_tokens if usage else None
    return response.output_text, input_tokens, output_tokens


def call_gemini(prompt, api_key, model):
    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000),  # milliseconds
    )
    response = client.models.generate_content(model=model, contents=prompt)

    # response.text is None if the answer was blocked (e.g. by safety filters).
    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count if usage else None
    output_tokens = usage.candidates_token_count if usage else None
    return response.text, input_tokens, output_tokens


def call_claude(prompt, api_key, model):
    client = anthropic.Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
    response = client.messages.create(
        model=model,
        max_tokens=CLAUDE_MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    input_tokens = usage.input_tokens if usage else None
    output_tokens = usage.output_tokens if usage else None
    return text, input_tokens, output_tokens


PROVIDER_FUNCTIONS = {
    "OpenAI": call_openai,
    "Gemini": call_gemini,
    "Claude": call_claude,
}


# --- Error handling ---------------------------------------------------------

def get_http_status(error):
    """OpenAI/Anthropic use .status_code, Google uses .code."""
    if isinstance(error, (openai.APIStatusError, anthropic.APIStatusError)):
        return error.status_code
    if isinstance(error, genai_errors.APIError):
        return error.code
    return None


def get_error_family_names(error):
    # Google's SDK lets HTTP library errors (e.g. ReadTimeout) pass through
    # unwrapped, so we match them by class name instead of importing httpx.
    return {cls.__name__ for cls in type(error).__mro__}


def classify_error(error):
    """Map an exception to (category, message). Raw SDK messages are never
    included, since they can contain request details or part of a key."""
    family_names = get_error_family_names(error)

    # Timeouts first: in the OpenAI/Anthropic SDKs they subclass connection errors.
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


# --- Public entry point -----------------------------------------------------

def ask_provider(provider_name, prompt):
    """Send a prompt to one provider. Never raises: failures come back as error results."""
    api_key, model = get_api_key_and_model(provider_name)

    problems = get_config_problems(provider_name)
    if problems:
        logger.warning("%s not configured: %s", provider_name, "; ".join(problems))
        message = f"{provider_name} is not configured: " + "; ".join(problems) + "."
        return build_result(provider_name, model or "not configured", error=message)

    # Log prompt length only, never its content.
    logger.info("Request started | provider=%s | model=%s | prompt_chars=%d",
                provider_name, model, len(prompt))

    start_time = time.perf_counter()
    try:
        text, input_tokens, output_tokens = PROVIDER_FUNCTIONS[provider_name](prompt, api_key, model)
    except Exception as error:
        latency = round(time.perf_counter() - start_time, 2)
        category, friendly_message = classify_error(error)
        logger.error("Request failed | provider=%s | model=%s | category=%s | error_type=%s | seconds=%.2f",
                     provider_name, model, category, type(error).__name__, latency)
        return build_result(provider_name, model, latency_seconds=latency,
                            error=f"{provider_name} request failed: {friendly_message}")

    latency = round(time.perf_counter() - start_time, 2)

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
