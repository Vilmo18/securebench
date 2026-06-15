import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


import main  # noqa: E402


class TestMainCli(unittest.TestCase):
    def test_should_continue_after_phase(self) -> None:
        self.assertFalse(main._should_continue_after_phase(1, 1))
        self.assertTrue(main._should_continue_after_phase(1, 2))
        self.assertFalse(main._should_continue_after_phase(2, 2))
        self.assertTrue(main._should_continue_after_phase(2, 3))

    def test_parser_accepts_stop_after_phase(self) -> None:
        parser = main.build_arg_parser()
        args = parser.parse_args(["--mode", "vuln", "--stop-after-phase", "1"])

        self.assertEqual(args.mode, "vuln")
        self.assertEqual(args.stop_after_phase, 1)


if __name__ == "__main__":
    unittest.main()
