from collections.abc import Awaitable, Callable


async def run_cli(
    message_handler: Callable[[str, str, str], Awaitable[str]],
    user_id: str = "cli:local",
    conversation_id: str = "cli:local",
) -> None:
    print("Pensabot local interface. Type /quit to exit.")

    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if text in {"/quit", "/exit"}:
            return

        print(await message_handler(text, user_id, conversation_id))
