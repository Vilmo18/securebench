import os
import sys
import unittest

from langchain_core.messages import AIMessage


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from llm_interface import LLMInterface  # noqa: E402


class _AsyncOnlyDummyLLM:
    def __init__(self) -> None:
        self.invoked = 0
        self.ainvoked = 0

    def invoke(self, _messages):
        self.invoked += 1
        raise ValueError(
            "Sync client is not available. This happens when an async callable was provided for the API key."
        )

    async def ainvoke(self, _messages):
        self.ainvoked += 1
        return AIMessage(content="<pattern_analysis>{\"summary\":\"ok\"}</pattern_analysis>")


class TestLLMInterface(unittest.TestCase):
    def test_interact_falls_back_to_ainvoke_when_sync_client_is_unavailable(self) -> None:
        interface = LLMInterface.__new__(LLMInterface)
        interface.llm = _AsyncOnlyDummyLLM()
        interface.system_prompt = "System prompt"
        interface.conversation_history = []
        interface.verbose = False
        interface.role = "pattern_analyzer"
        interface.interaction_string = None
        interface.interaction_template = [
            {
                "required_keys": ["problem_statement"],
                "template": "Scenario:\n{problem_statement}",
            }
        ]

        content = interface.interact(problem_statement="Analyze this.")

        self.assertEqual(
            content,
            "<pattern_analysis>{\"summary\":\"ok\"}</pattern_analysis>",
        )
        self.assertEqual(interface.llm.invoked, 1)
        self.assertEqual(interface.llm.ainvoked, 1)
        self.assertEqual(len(interface.conversation_history), 2)


if __name__ == "__main__":
    unittest.main()
