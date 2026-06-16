import os
import sys
import unittest
from unittest.mock import patch

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
    def test_huggingface_provider_uses_hf_token_and_router(self) -> None:
        interface = LLMInterface.__new__(LLMInterface)
        interface.api_keys = {"huggingface": "hf-test-token"}
        interface.api_bases = {
            "huggingface": "https://router.huggingface.co/v1"
        }

        api_key, api_base = interface._resolve_api_credentials(
            {
                "model_name": "Qwen/Qwen2.5-Coder-32B-Instruct:fastest",
                "provider": "huggingface",
                "local": False,
            }
        )

        self.assertEqual(api_key, "hf-test-token")
        self.assertEqual(api_base, "https://router.huggingface.co/v1")

    def test_huggingface_role_requires_a_token(self) -> None:
        class _PromptManager:
            def get_prompt_template(self, _role):
                return "System prompt"

            def get_interaction_template(self, _role):
                return []

            def get_llm_config(self, _role):
                return {
                    "model_name": "openai/gpt-oss-20b:nscale",
                    "provider": "huggingface",
                    "params": {},
                    "local": False,
                }

        interface = LLMInterface.__new__(LLMInterface)
        interface.prompt_manager = _PromptManager()
        interface.verbose = False
        interface.api_keys = {"huggingface": None}
        interface.api_bases = {
            "huggingface": "https://router.huggingface.co/v1"
        }

        with patch("llm_interface.ChatOpenAI") as chat_openai:
            self.assertFalse(interface.set_role("challenge_designer"))
            chat_openai.assert_not_called()

    def test_local_huggingface_provider_is_not_openai_compatible_api(self) -> None:
        interface = LLMInterface.__new__(LLMInterface)

        for provider in ("local-hf", "hf-local", "huggingface-local", "transformers"):
            self.assertTrue(interface._is_local_hf_provider({"provider": provider}))

        self.assertFalse(interface._is_local_hf_provider({"provider": "huggingface"}))

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
