import unittest
from unittest.mock import AsyncMock, Mock, call, patch

from pensabot.interfaces.cli import run_cli


class RunCliTests(unittest.IsolatedAsyncioTestCase):
    @patch("builtins.print")
    @patch("builtins.input", side_effect=["an idea", "/quit"])
    async def test_passes_input_to_core_and_prints_result(
        self,
        input_mock: Mock,
        print_mock: Mock,
    ) -> None:
        message_handler = AsyncMock(return_value="processed idea")

        await run_cli(message_handler)

        message_handler.assert_awaited_once_with(
            "an idea",
            "cli:local",
            "cli:local",
        )
        self.assertEqual(
            print_mock.call_args_list,
            [
                call("Pensabot local interface. Type /quit to exit."),
                call("processed idea"),
            ],
        )
        self.assertEqual(input_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
