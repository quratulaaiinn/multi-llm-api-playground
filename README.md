# Multi-LLM API Playground

A lightweight Python playground for integrating and comparing OpenAI, Gemini, and Claude APIs.

> **Notice:** This application requires API keys from the providers you want to use. Users are responsible for their own API usage and associated costs.

---

## Overview

OpenAI, Google, and Anthropic all offer large language models through APIs, but each provider's SDK has its own request format, response structure, and error types.

This project is a small terminal app that calls all three through their **official Python SDKs** and converts their different responses into **one common format**. You can ask a single provider a question, or send the same prompt to every configured provider and compare the answers side by side.

It's intentionally small and framework-free (no LangChain or similar), so the direct API integration is easy to read and learn from.

## Features

- **Single-provider mode**: ask OpenAI, Gemini, or Claude a prompt.
- **Compare mode**: send one prompt to every configured provider and view the results together, plus a summary table.
- **Standardized results**: every provider returns the same dictionary shape.
- **Response metadata**: execution time, plus input/output token counts when the provider reports them.
- **Works with any subset of providers**: configure one, two, or all three. Unconfigured providers are clearly reported and skipped.
- **Friendly error handling** for missing configuration, invalid keys, wrong model names, rate limits, timeouts, network problems, and provider outages.
- **Privacy-conscious logging** to `logs/playground.log`. API keys and prompt text are never logged.
- **Offline test suite**: 16 `unittest` tests that use mocks and need no API keys.
- **Evaluation template** in `experiments/model_comparison.md` for comparing models across six task types.

## Technologies used

- Python 3.10+
- [`openai`](https://github.com/openai/openai-python): OpenAI SDK, **Responses API**
- [`google-genai`](https://github.com/googleapis/python-genai): Google Gen AI SDK for Gemini
- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python): Anthropic SDK, **Messages API**
- [`python-dotenv`](https://github.com/theskumar/python-dotenv): loads settings from a `.env` file
- Standard library: `logging`, `unittest`, `time`, `os`, `pathlib`

## Project structure

```
multi-llm-api-playground/
├── main.py                       # Terminal app: menu, user input, displaying results
├── providers.py                  # Provider layer: config, SDK calls, standard results, errors
├── .env.example                  # Template for your own .env file (placeholders only)
├── .gitignore                    # Keeps .env, virtual environments, and logs out of Git
├── requirements.txt              # Python dependencies
├── README.md
├── experiments/
│   └── model_comparison.md       # Template for evaluating and comparing models
└── tests/
    └── test_response_format.py   # Offline tests (no API keys needed)
```

A `logs/` folder is created automatically the first time you run the app.

## How it works

The app is split into two layers with a single connection point:

```
┌──────────────────────────────┐
│           main.py            │  What does the user want?
│   menu · input · display     │
└──────────────┬───────────────┘
               │  ask_provider("Gemini", prompt)  →  standardized result dict
               ▼
┌──────────────────────────────┐
│         providers.py         │  How do I talk to this provider?
│ config · SDK calls · errors  │
└──────────────┬───────────────┘
               │  official SDKs
               ▼
     OpenAI · Google Gemini · Anthropic
```

- **`main.py`** contains no provider-specific code. It calls `ask_provider()` and prints whatever dictionary comes back.
- **`providers.py`** contains no `print()` or `input()`. It reads configuration, calls the SDK, measures latency, catches errors, and returns a result.

What happens on each request:

1. `main.py` checks that the chosen provider is configured. If it isn't, it explains what's missing and doesn't ask for a prompt.
2. It reads your prompt and calls `ask_provider(provider_name, prompt)`.
3. `ask_provider` looks up the provider's function (`call_openai`, `call_gemini`, or `call_claude`), starts a timer, and calls it.
4. The provider function sends the request with the official SDK and extracts the text and token counts.
5. Any exception is caught and turned into a friendly message. `ask_provider` never raises.
6. The result is returned in the standard format below and displayed.

### Standardized result

```python
{
    "provider": "Gemini",          # Which provider answered
    "model": "model-name",         # Model name from your .env
    "text": "Generated response",  # None if the request failed
    "latency_seconds": 2.45,       # Time spent on the API call
    "input_tokens": 120,           # None if the provider didn't report it
    "output_tokens": 250,          # None if the provider didn't report it
    "status": "success",           # "success" or "error"
    "error": None                  # Friendly error message when status is "error"
}
```

Token counts are never estimated or invented. If a provider doesn't return them, they stay `None`.

## How each provider is integrated

| Provider | SDK call | Text comes from | Token counts come from |
|---|---|---|---|
| OpenAI | `client.responses.create(model=..., input=prompt)` | `response.output_text` | `response.usage.input_tokens` / `output_tokens` |
| Gemini | `client.models.generate_content(model=..., contents=prompt)` | `response.text` | `response.usage_metadata.prompt_token_count` / `candidates_token_count` |
| Claude | `client.messages.create(model=..., max_tokens=1024, messages=[...])` | the `text` blocks in `response.content` | `response.usage.input_tokens` / `output_tokens` |

All three use a 60-second timeout (`REQUEST_TIMEOUT_SECONDS` in `providers.py`). Model names come from environment variables, never from the code, because providers add and retire models regularly.

## Installation

You need **Python 3.10 or newer** (`python --version`) and **Git**.

**1. Clone the repository**

```bash
git clone https://github.com/quratulaaiinn/multi-llm-api-playground.git
cd multi-llm-api-playground
```

**2. Create a virtual environment**

```bash
python -m venv .venv
```

**3. Activate it**

Windows (Command Prompt or PowerShell):

```powershell
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Your prompt will show `(.venv)` when the environment is active.

> **Windows PowerShell says "running scripts is disabled"?** Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once, or use Command Prompt instead.

**4. Install dependencies**

```bash
pip install -r requirements.txt
```

The first install can take a few minutes. Last checked with `openai 3.57.0`, `google-genai 3.6.1`, `anthropic 2.12.0`, and `python-dotenv 1.2.4` on Python 3.12.

## Environment setup

**5. Create your `.env` file from the template**

Windows:

```powershell
copy .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder values for the providers you want to use:

| Variable | What to put there |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Your OpenAI key and a model your account can access |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Your Gemini key and a Gemini model name |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Your Anthropic key and a Claude model name |

**Get your API keys from:**

- OpenAI: https://platform.openai.com/api-keys
- Google AI Studio (Gemini): https://aistudio.google.com/
- Anthropic: https://console.anthropic.com/

**Find current model names:** [OpenAI models](https://platform.openai.com/docs/models) · [Gemini models](https://ai.google.dev/gemini-api/docs/models) · [Claude models](https://docs.anthropic.com/en/docs/about-claude/models)

Notes:

- **You don't need all three providers.** Leave unused providers as they are; the app treats placeholder values as "not configured".
- `.env` is listed in `.gitignore`. **Never commit it or share it.** If a key leaks, revoke it in the provider's dashboard and create a new one.
- After editing `.env`, **restart the app**. Settings are read once at startup.

## Running the application

**6. Start the app**

```bash
python main.py
```

On startup, the app shows which providers are ready, then the main menu. Press `Ctrl+C` at any time to quit.

### Single-provider mode

1. Choose `1` (OpenAI), `2` (Gemini), or `3` (Claude).
2. Type your prompt and press Enter.
3. The response is shown with the provider, model, execution time, and token counts (when available).
4. Press Enter to return to the menu.

If the provider isn't configured, the app tells you which `.env` values are missing instead of asking for a prompt.

### Compare mode

1. Choose `4`.
2. The app lists any providers it will skip because they aren't configured.
3. Type one prompt. It's sent to each configured provider **one after another**.
4. Each response is shown in turn, followed by a summary table.

If one provider fails, its error is shown and the others still run. The app does not pick a winner; judging the answers is up to you. See `experiments/model_comparison.md` for a structured way to do that.

## Example terminal interaction

The example below shows a session with only Claude configured. Response text and numbers are illustrative.

```
Provider setup check:
  [!] OpenAI: OPENAI_API_KEY still has the placeholder value from .env.example; OPENAI_MODEL still has the placeholder value from .env.example
  [!] Gemini: GEMINI_API_KEY still has the placeholder value from .env.example; GEMINI_MODEL still has the placeholder value from .env.example
  [OK] Claude: ready

========================================
        MULTI-LLM PLAYGROUND
========================================

1. Ask OpenAI
2. Ask Gemini
3. Ask Claude
4. Compare all providers
5. Exit

Choose an option: 4

Skipping (not configured): OpenAI, Gemini
Comparing: Claude

Enter your prompt: Explain what an API is in one sentence.
Asking Claude... please wait.

========================================
         MODEL COMPARISON
========================================

Prompt:
Explain what an API is in one sentence.

----------------------------------------
CLAUDE  (your-claude-model)
----------------------------------------
Response:

An API is a set of rules that lets one piece of software request data or services from another.

Execution Time: 1.84 seconds
Input Tokens: 16
Output Tokens: 24

----------------------------------------
SUMMARY
----------------------------------------
Provider  Status   Time      In tok   Out tok
Claude    success  1.84s     16       24
----------------------------------------
Not included (not configured): OpenAI, Gemini

Press Enter to return to the menu...
```

## Running tests (no API keys needed)

```bash
python -m unittest discover -s tests
```

Run this from the project folder with the virtual environment active. The 16 tests replace the real SDK clients with mocks, so **no network requests are made and nothing is billed**. They check:

- the standardized result structure for successful and failed requests
- that unknown token counts stay `None`
- configuration checks, including placeholder values and single-provider setups
- that missing configuration never triggers an API call
- that exceptions become error results instead of crashing (and raw error text isn't exposed)
- that text and token counts are extracted correctly from each provider's response shape
- that HTTP errors map to the right categories

The tests don't verify live API behavior. That requires your own keys.

## Error handling and troubleshooting

Every error is caught inside `ask_provider()`, so the app keeps running. Raw SDK error messages are never shown or logged, because they can contain request details or partial keys.

| Message | Likely cause | What to do |
|---|---|---|
| `... is not configured` / `still has the placeholder value` | `.env` missing, or values not filled in | Create `.env` from `.env.example`, fill in values, restart |
| `authentication failed (HTTP 401)` | Wrong or revoked API key | Check the key in `.env`; create a new one if needed |
| `access denied (HTTP 403)` | Key lacks access to that model or feature | Check your account's permissions or choose another model |
| `model not found (HTTP 404)` | Model name is wrong or unavailable | Check the provider's model list and update `*_MODEL` |
| `rejected as invalid (HTTP 400)` | Invalid request or model settings | Check the model name and prompt |
| `rate limit or quota reached (HTTP 429)` | Too many requests, or no credit or quota left | Wait and retry; check billing and usage limits |
| `server error (HTTP 5xx)` | Provider outage or overload | Try again later |
| `request timed out` | No response within 60 seconds | Retry; try a shorter prompt |
| `could not connect` | No internet, firewall, or proxy issue | Check your network connection |
| `returned no text` | Answer was blocked (e.g. safety filters) or empty | Rephrase the prompt |

**Logs:** `logs/playground.log` records request start and finish, provider, model, prompt length, timing, token counts, and error categories. It never records API keys, prompt text, or responses. You can delete the file at any time.

**Retries:** the app has no retry logic of its own. The OpenAI and Anthropic SDKs automatically retry some temporary failures before reporting an error.

## API usage and cost

**Every request made through this app uses your own API account and may be billed by the provider.** Compare mode sends one request to *each* configured provider.

- Providers charge per **token** (a chunk of text, roughly ¾ of an English word). Input tokens (your prompt) and output tokens (the answer) are usually priced differently, and output often costs more.
- Prices vary widely between models and change over time, so this app **shows token counts but does not calculate cost**. Check each provider's pricing page for current rates.
- Some models use internal "reasoning" tokens, which may be billed even though they aren't shown as text.
- Consider setting spending limits in each provider's dashboard.

## Current limitations

- No conversation memory: each prompt is independent.
- Compare mode runs providers one after another, so total time is the sum of all requests.
- No streaming: responses appear only when complete.
- Generation settings (temperature, etc.) use provider defaults. Claude responses are capped at 1024 output tokens (`CLAUDE_MAX_OUTPUT_TOKENS`), so very long Claude answers may be cut off.
- No cost calculation; token counts only.
- Terminal output only. Markdown in responses is shown as plain text.
- A new SDK client is created for each request. That's simple, but not optimal for heavy use.
- Live API calls are not covered by the automated tests.

## Future improvements

Possible next steps (not implemented):

- Streaming responses
- Concurrent (async) requests in compare mode
- System prompts and configurable generation settings (temperature, max tokens)
- Token-based cost estimation
- Structured JSON outputs
- Function/tool calling
- Conversation history
