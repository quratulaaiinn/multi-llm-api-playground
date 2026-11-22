"""
main.py - The terminal app the user interacts with.

This file handles the menu, reads prompts, and prints results.
It never talks to an LLM directly: it calls providers.ask_provider()
and gets back a standardized result dictionary.
"""

from providers import ask_provider

LINE = "-" * 40
DOUBLE_LINE = "=" * 40

# Menu number -> provider name. Adding a provider means adding one line here.
PROVIDER_MENU_OPTIONS = {"1": "OpenAI", "2": "Gemini", "3": "Claude"}
EXIT_OPTION = "4"


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
    """Print token counts, skipping any value that is unknown (None)."""
    if result["input_tokens"] is not None:
        print(f"Input Tokens: {result['input_tokens']}")
    if result["output_tokens"] is not None:
        print(f"Output Tokens: {result['output_tokens']}")


def print_result_body(result):
    """Print the response text."""
    print("Response:\n")
    print(result["text"])
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


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_single_provider(provider_name):
    prompt = read_prompt()
    if prompt is None:
        return
    print(f"\nAsking {provider_name}... please wait.")
    result = ask_provider(provider_name, prompt)
    display_single_result(result)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice in PROVIDER_MENU_OPTIONS:
            run_single_provider(PROVIDER_MENU_OPTIONS[choice])
        elif choice == EXIT_OPTION:
            print("\nGoodbye!")
            break
        else:
            print(f"\n'{choice}' is not a valid option. Please choose 1-{EXIT_OPTION}.")
            continue  # Show the menu again right away.

        wait_for_enter()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or a closed input stream: exit quietly instead of a traceback.
        print("\n\nExiting. Goodbye!")
