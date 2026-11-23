# Multi-LLM API Playground

A small Python terminal app for calling OpenAI, Gemini and Claude through their official SDKs and comparing their answers side by side.

Each provider's SDK has a different request format, response shape and error types. This project wraps all three behind one function, `ask_provider(provider, prompt)`, that always returns the same result format. It uses no frameworks such as LangChain.

## Features

- Ask one provider, or send the same prompt to every configured provider (compare mode)
- Response time and input/output token counts for each answer
- Works with any subset of providers; unconfigured ones are skipped with a clear message
- Friendly messages for bad keys, wrong model names, rate limits, timeouts and network errors
- Logs to `logs/playground.log` without recording API keys or prompt text
- 16 offline tests (mocked SDKs, no API keys needed)

## Project structure

```
main.py            # Terminal menu, input and output
providers.py       # Config, SDK calls, standard result format, error handling
tests/             # Offline unit tests
experiments/       # Template for comparing models on six task types
.env.example       # Template for your API keys and model names
```

## How it works

`main.py` never talks to an API directly. It calls `ask_provider()` in `providers.py`, which reads the config, calls the right SDK, times the request, catches any error and returns:

```python
{
    "provider": "Claude",
    "model": "model-name",
    "text": "Generated response",   # None on error
    "latency_seconds": 1.84,
    "input_tokens": 16,             # None if the provider didn't report it
    "output_tokens": 24,
    "status": "success",            # or "error"
    "error": None,
}
```

| Provider | SDK call | Text | Tokens |
|---|---|---|---|
| OpenAI | `responses.create` | `output_text` | `usage.input_tokens` / `output_tokens` |
| Gemini | `models.generate_content` | `text` | `usage_metadata.prompt_token_count` / `candidates_token_count` |
| Claude | `messages.create` | text blocks in `content` | `usage.input_tokens` / `output_tokens` |

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/quratulaaiinn/multi-llm-api-playground.git
cd multi-llm-api-playground
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
copy .env.example .env        # cp on macOS / Linux
```

Fill in `.env` for the providers you want to use. You don't need all three. Model names are set in `.env`, not hard-coded, because providers change them often.

- Keys: [OpenAI](https://platform.openai.com/api-keys) · [Google AI Studio](https://aistudio.google.com/) · [Anthropic](https://console.anthropic.com/)
- Models: [OpenAI](https://platform.openai.com/docs/models) · [Gemini](https://ai.google.dev/gemini-api/docs/models) · [Claude](https://docs.anthropic.com/en/docs/about-claude/models)

## Usage

```bash
python main.py
```

```
1. Ask OpenAI
2. Ask Gemini
3. Ask Claude
4. Compare all providers
5. Exit
```

Compare mode sends the prompt to each configured provider one after another, shows every answer and ends with a summary table:

```
Provider  Status   Time      In tok   Out tok
Claude    success  1.84s     16       24
```

## Tests

```bash
python -m unittest discover -s tests
```

The tests mock the SDK clients, so no requests are sent and nothing is billed. They don't cover live API behaviour.

## Notes

- Every request uses your own API account and may be billed. Compare mode makes one request per provider.
- Token counts are shown, but cost is not calculated because prices change.
- Limitations: no conversation history, no streaming, compare mode runs sequentially, and Claude output is capped at 1024 tokens.
