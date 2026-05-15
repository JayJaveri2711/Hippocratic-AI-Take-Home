import argparse
import json

from story_agent import run_story_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a judged bedtime story.")
    parser.add_argument("request", nargs="*", help="The bedtime story request.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show judge output and orchestration metadata.",
    )
    return parser.parse_args()


def get_user_request(args: argparse.Namespace) -> str:
    if args.request:
        return " ".join(args.request).strip()
    return input("What bedtime story would you like to hear? ").strip()


def print_result(result, debug: bool) -> None:
    if result.story:
        print(result.story)
    else:
        message = result.warnings[0] if result.warnings else "No story was returned."
        print(message)

    if debug:
        print("\n--- Debug Info ---")
        print(f"Status: {result.status}")
        print(f"Attempts used: {result.attempts_used}")
        print(f"Used fallback: {result.used_fallback}")
        if result.error:
            print(f"Error: {result.error}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        print("Final judgment:")
        print(json.dumps(result.final_judgment, indent=2))
        print("Debug metadata:")
        print(json.dumps(result.debug_info, indent=2))


def main() -> None:
    args = parse_args()
    user_request = get_user_request(args)
    result = run_story_agent(user_request, debug=args.debug)
    print_result(result, args.debug)


if __name__ == "__main__":
    main()
