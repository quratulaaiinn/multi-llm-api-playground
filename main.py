"""
main.py - The terminal app the user interacts with.

This file handles the menu, reads prompts, and prints results.
It never talks to an LLM directly: it calls providers.ask_provider()
and gets back a standardized result dictionary.
"""

import logging
from pathlib import Path

from providers import PROVIDER_NAMES, ask_provider, get_config_problems, is_configured

logger = logging.getLogger(__name__)

LOG_FILE = Path(__file__).parent / "logs" / "playground.log"
LINE = "-" * 40
DOUBLE_LINE = "=" * 40

# Menu number -> provider name. Adding a provider means adding one line here.
PROVIDER_MENU_OPTIONS = {"1": "OpenAI", "2": "Gemini", "3": "Claude"}
COMPARE_OPTION = "4"
EXIT_OPTION = "5"


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_logging():
    """Send log messages to logs/playground.log (not to the screen)."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        encoding="utf-8",
    )
    # The SDKs' HTTP libraries log every request URL at INFO level.
    # We only want our own messages, so we quiet them down.
    for noisy_logger in ("httpx", "httpx2", "httpcore", "httpcore2",
                         "openai", "anthropic", "google_genai"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def show_configuration_status():
    """At startup, tell the user which providers are ready to use."""
    print("\nProvider setup check:")
    for provider_name in PROVIDER_NAMES:
        problems = get_config_problems(provider_name)
        if problems:
            print(f"  [!] {provider_name}: " + "; ".join(problems))
        else:
            print(f"  [OK] {provider_name}: ready")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def show_menu():
    print()
    print(DOUBLE_LINE)
    print("        MULTI-LLM PLAYGROUND")
    print(DOUBLE_LINE)
    print()
    for number, provider_name in PROVIDER_MENU_OPTIONS.items():
        print(f"{number}. Ask {provider_name}")
    print(f"{COMPARE_OPTION}. Compare all providers")
    print(f"{EXIT_OPTION}. Exit")
    print()


def read_prompt():
    """Ask the user for a prompt. Returns None if they enter nothing."""
    prompt = input("\nEnter your prompt: ").strip()
    if not prompt:
        print("Prompt cannot be empty. Returning to the menu.")
        return None
    return prompt


def wait_for_enter():
    input("\nPress Enter to return to the menu...")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_metadata(result):
    """Print time and token counts, skipping any value that is unknown (None)."""
    if result["latency_seconds"] is not None:
        print(f"Execution Time: {result['latency_seconds']:.2f} seconds")
    if result["input_tokens"] is not None:
        print(f"Input Tokens: {result['input_tokens']}")
    if result["output_tokens"] is not None:
        print(f"Output Tokens: {result['output_tokens']}")


def print_result_body(result):
    """Print the response text, or the error message if the request failed."""
    if result["status"] == "success":
        print("Response:\n")
        print(result["text"])
    else:
        print("Error:\n")
        print(result["error"])
    print()
    print_metadata(result)


def display_single_result(result):
    print()
    print(LINE)
    print(f"Provider: {result['provider']}")
    print(f"Model: {result['model']}")
    print(LINE)
    print()
    print_result_body(result)
    print(LINE)


def display_comparison(prompt, results, skipped_providers):
    print()
    print(DOUBLE_LINE)
    print("         MODEL COMPARISON")
    print(DOUBLE_LINE)
    print(f"\nPrompt:\n{prompt}\n")

    for result in results:
        print(LINE)
        print(f"{result['provider'].upper()}  ({result['model']})")
        print(LINE)
        print_result_body(result)
        print()

    print_comparison_summary(results)
    if skipped_providers:
        print(f"Not included (not configured): {', '.join(skipped_providers)}")


def format_optional(value, suffix=""):
    """Show 'n/a' for unknown values instead of pretending we know them."""
    return "n/a" if value is None else f"{value}{suffix}"


def print_comparison_summary(results):
    """A compact table of the numbers side by side. It does not pick a winner."""
    print(LINE)
    print("SUMMARY")
    print(LINE)
    print(f"{'Provider':<10}{'Status':<9}{'Time':<10}{'In tok':<9}{'Out tok':<9}")
    for result in results:
        print(f"{result['provider']:<10}"
              f"{result['status']:<9}"
              f"{format_optional(result['latency_seconds'], 's'):<10}"
              f"{format_optional(result['input_tokens']):<9}"
              f"{format_optional(result['output_tokens']):<9}")
    print(LINE)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def explain_missing_configuration(provider_name):
    """Tell the user exactly what to add to .env for this provider."""
    print(f"\n{provider_name} is not configured yet:")
    for problem in get_config_problems(provider_name):
        print(f"  - {problem}")
    print("Add the missing values to your .env file (see .env.example), then restart the app.")


def run_single_provider(provider_name):
    # Check the configuration before asking for a prompt, so the user
    # doesn't type a prompt only to be told the provider can't be used.
    if not is_configured(provider_name):
        explain_missing_configuration(provider_name)
        return

    prompt = read_prompt()
    if prompt is None:
        return
    print(f"\nAsking {provider_name}... please wait.")
    result = ask_provider(provider_name, prompt)
    display_single_result(result)


def run_comparison():
    available = [name for name in PROVIDER_NAMES if is_configured(name)]
    skipped = [name for name in PROVIDER_NAMES if not is_configured(name)]

    if not available:
        print("\nNo providers are configured, so there is nothing to compare.")
        print("Add at least one API key and model to your .env file (see .env.example), then restart the app.")
        return
    if skipped:
        print(f"\nSkipping (not configured): {', '.join(skipped)}")
        print(f"Comparing: {', '.join(available)}")

    prompt = read_prompt()
    if prompt is None:
        return

    # Requests run one after another (sequentially) to keep things simple.
    # ask_provider never raises, so a failure in one provider doesn't stop the loop.
    results = []
    for provider_name in available:
        print(f"Asking {provider_name}... please wait.")
        results.append(ask_provider(provider_name, prompt))

    display_comparison(prompt, results, skipped)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    setup_logging()
    logger.info("Application started")
    show_configuration_status()

    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice in PROVIDER_MENU_OPTIONS:
            provider_name = PROVIDER_MENU_OPTIONS[choice]
            logger.info("Provider selected: %s", provider_name)
            run_single_provider(provider_name)
        elif choice == COMPARE_OPTION:
            logger.info("Comparison mode selected")
            run_comparison()
        elif choice == EXIT_OPTION:
            print("\nGoodbye!")
            break
        else:
            print(f"\n'{choice}' is not a valid option. Please choose 1-{EXIT_OPTION}.")
            continue  # Show the menu again right away.

        wait_for_enter()

    logger.info("Application exited")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or a closed input stream: exit quietly instead of a traceback.
        print("\n\nExiting. Goodbye!")
