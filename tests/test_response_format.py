"""
Lightweight tests that run WITHOUT API keys and WITHOUT network access.

Real SDK clients are replaced with fakes (mocks), so no request ever leaves
your machine and no API usage is billed.

Run from the project folder:
    python -m unittest discover -s tests
"""

import logging
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import providers

# Keep test output clean: providers.py logs every request, which we don't need here.
logging.disable(logging.CRITICAL)

EXPECTED_KEYS = {
    "provider", "model", "text", "latency_seconds",
    "input_tokens", "output_tokens", "status", "error",
}

# A fully configured environment with obviously fake values.
FAKE_ENV = {
    "OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-openai-model",
    "GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-gemini-model",
    "ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "test-claude-model",
}


class TestBuildResult(unittest.TestCase):
    """The standardized result dictionary."""

    def test_success_result_has_all_keys(self):
        result = providers.build_result("Gemini", "m", text="Hi", latency_seconds=1.5,
                                        input_tokens=3, output_tokens=5)
        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["error"])

    def test_error_result_has_all_keys(self):
        result = providers.build_result("Claude", "m", error="Something failed")
        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["text"])

    def test_unknown_token_counts_stay_none(self):
        result = providers.build_result("OpenAI", "m", text="Hi")
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["output_tokens"])


class TestConfiguration(unittest.TestCase):
    """Reading API keys and model names from the environment."""

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_missing_values_are_reported(self):
        problems = providers.get_config_problems("OpenAI")
        self.assertEqual(len(problems), 2)
        self.assertFalse(providers.is_configured("OpenAI"))

    @mock.patch.dict(os.environ, {"GEMINI_API_KEY": "your_gemini_api_key",
                                  "GEMINI_MODEL": "your_available_gemini_model"}, clear=True)
    def test_placeholder_values_count_as_not_configured(self):
        problems = providers.get_config_problems("Gemini")
        self.assertEqual(len(problems), 2)
        self.assertIn("placeholder", problems[0])

    @mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key",
                                  "ANTHROPIC_MODEL": "test-claude-model"}, clear=True)
    def test_one_provider_can_be_configured_alone(self):
        self.assertTrue(providers.is_configured("Claude"))
        self.assertFalse(providers.is_configured("OpenAI"))
        self.assertFalse(providers.is_configured("Gemini"))


class TestAskProvider(unittest.TestCase):
    """The public entry point used by main.py."""

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_missing_config_returns_error_without_calling_api(self):
        fake_call = mock.Mock()
        with mock.patch.dict(providers.PROVIDER_FUNCTIONS, {"OpenAI": fake_call}):
            result = providers.ask_provider("OpenAI", "Hello")
        fake_call.assert_not_called()
        self.assertEqual(result["status"], "error")
        self.assertIn("OPENAI_API_KEY", result["error"])

    @mock.patch.dict(os.environ, FAKE_ENV, clear=True)
    def test_successful_call_is_standardized(self):
        fake_call = mock.Mock(return_value=("Hello there!", 4, 7))
        with mock.patch.dict(providers.PROVIDER_FUNCTIONS, {"Gemini": fake_call}):
            result = providers.ask_provider("Gemini", "Hello")
        fake_call.assert_called_once_with("Hello", "test-key", "test-gemini-model")
        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "Hello there!")
        self.assertEqual(result["model"], "test-gemini-model")
        self.assertEqual((result["input_tokens"], result["output_tokens"]), (4, 7))
        self.assertIsInstance(result["latency_seconds"], float)

    @mock.patch.dict(os.environ, FAKE_ENV, clear=True)
    def test_exception_becomes_error_result_instead_of_crashing(self):
        fake_call = mock.Mock(side_effect=ValueError("secret detail sk-abc123"))
        with mock.patch.dict(providers.PROVIDER_FUNCTIONS, {"Claude": fake_call}):
            result = providers.ask_provider("Claude", "Hello")
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("Claude request failed:"))
        self.assertNotIn("sk-abc123", result["error"])  # Raw messages are never shown.

    @mock.patch.dict(os.environ, FAKE_ENV, clear=True)
    def test_empty_text_is_reported_as_error(self):
        fake_call = mock.Mock(return_value=(None, 4, 0))
        with mock.patch.dict(providers.PROVIDER_FUNCTIONS, {"Gemini": fake_call}):
            result = providers.ask_provider("Gemini", "Hello")
        self.assertEqual(result["status"], "error")
        self.assertIn("no text", result["error"])


class TestProviderResponseParsing(unittest.TestCase):
    """Each provider function pulls text and tokens out of a (fake) SDK response."""

    def test_openai_parsing(self):
        fake_response = SimpleNamespace(
            output_text="OpenAI answer",
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
        )
        with mock.patch("providers.openai.OpenAI") as fake_client_class:
            fake_client_class.return_value.responses.create.return_value = fake_response
            result = providers.call_openai("Hi", "test-key", "test-model")
        self.assertEqual(result, ("OpenAI answer", 10, 20))

    def test_gemini_parsing(self):
        fake_response = SimpleNamespace(
            text="Gemini answer",
            usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=21),
        )
        with mock.patch("providers.genai.Client") as fake_client_class:
            fake_client_class.return_value.models.generate_content.return_value = fake_response
            result = providers.call_gemini("Hi", "test-key", "test-model")
        self.assertEqual(result, ("Gemini answer", 11, 21))

    def test_claude_parsing_keeps_only_text_blocks(self):
        fake_response = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Claude "),
                SimpleNamespace(type="thinking", thinking="(hidden)"),
                SimpleNamespace(type="text", text="answer"),
            ],
            usage=SimpleNamespace(input_tokens=12, output_tokens=22),
        )
        with mock.patch("providers.anthropic.Anthropic") as fake_client_class:
            fake_client_class.return_value.messages.create.return_value = fake_response
            result = providers.call_claude("Hi", "test-key", "test-model")
        self.assertEqual(result, ("Claude answer", 12, 22))

    def test_missing_usage_gives_none_tokens(self):
        fake_response = SimpleNamespace(output_text="Answer", usage=None)
        with mock.patch("providers.openai.OpenAI") as fake_client_class:
            fake_client_class.return_value.responses.create.return_value = fake_response
            result = providers.call_openai("Hi", "test-key", "test-model")
        self.assertEqual(result, ("Answer", None, None))


class TestClassifyError(unittest.TestCase):
    """Turning exceptions into friendly categories."""

    def test_http_status_codes_map_to_categories(self):
        cases = {401: "authentication", 404: "not_found", 429: "rate_limit", 503: "server_error"}
        for status, expected_category in cases.items():
            with self.subTest(status=status):
                error = providers.genai_errors.APIError(status, {"error": {"message": "x"}})
                category, _ = providers.classify_error(error)
                self.assertEqual(category, expected_category)

    def test_unknown_exception_is_unexpected(self):
        category, message = providers.classify_error(RuntimeError("boom"))
        self.assertEqual(category, "unexpected")
        self.assertIn("RuntimeError", message)


if __name__ == "__main__":
    unittest.main()
