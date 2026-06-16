import asyncio
import json
import os
import threading
from typing import Any, Dict, List, Optional, Union

from langchain_core.callbacks import StdOutCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from prompt_manager import PromptManager

from dotenv import load_dotenv

load_dotenv()

_HF_MODEL_CACHE: Dict[str, Any] = {}
_HF_MODEL_CACHE_LOCK = threading.Lock()


class LocalHuggingFaceChatModel:
    """Minimal LangChain-like chat wrapper for local Transformers causal LMs."""

    def __init__(
        self,
        *,
        model_name: str,
        params: Optional[Dict[str, Any]] = None,
        hf_local: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model_name = model_name
        self.params = dict(params or {})
        self.hf_local = dict(hf_local or {})
        self.tokenizer, self.model = self._load_model()

    def _load_model(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:
            raise RuntimeError(
                "Local Hugging Face backend requires torch and transformers. "
                "Install them with: pip install torch transformers accelerate"
            ) from exc

        cache_key = json.dumps(
            {
                "model_name": self.model_name,
                "device_map": self.hf_local.get("device_map", "auto"),
                "torch_dtype": self.hf_local.get("torch_dtype", "auto"),
                "trust_remote_code": bool(self.hf_local.get("trust_remote_code", False)),
                "local_files_only": bool(self.hf_local.get("local_files_only", False)),
            },
            sort_keys=True,
        )
        with _HF_MODEL_CACHE_LOCK:
            cached = _HF_MODEL_CACHE.get(cache_key)
            if cached is not None:
                return cached

            torch_dtype = self.hf_local.get("torch_dtype", "auto")
            if isinstance(torch_dtype, str) and torch_dtype != "auto":
                torch_dtype = getattr(torch, torch_dtype)

            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=bool(self.hf_local.get("trust_remote_code", False)),
                local_files_only=bool(self.hf_local.get("local_files_only", False)),
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=self.hf_local.get("device_map", "auto"),
                dtype=torch_dtype,
                trust_remote_code=bool(self.hf_local.get("trust_remote_code", False)),
                local_files_only=bool(self.hf_local.get("local_files_only", False)),
            )
            model.eval()
            _HF_MODEL_CACHE[cache_key] = (tokenizer, model)
            return tokenizer, model

    def _message_to_dict(self, message) -> Dict[str, str]:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = "user"
        return {"role": role, "content": str(message.content or "")}

    def _generation_kwargs(self) -> Dict[str, Any]:
        allowed = {
            "do_sample",
            "temperature",
            "top_p",
            "top_k",
            "repetition_penalty",
            "num_beams",
        }
        out = {k: v for k, v in self.params.items() if k in allowed}
        max_new_tokens = self.params.get("max_new_tokens", self.params.get("max_tokens", 1024))
        out["max_new_tokens"] = int(max_new_tokens)
        temperature = float(out.get("temperature", 0.0) or 0.0)
        if temperature <= 0.0:
            out.pop("temperature", None)
            out["do_sample"] = False
        elif "do_sample" not in out:
            out["do_sample"] = True
        return out

    def invoke(self, messages):
        import torch

        chat_messages = [self._message_to_dict(message) for message in messages]
        try:
            input_ids = self.tokenizer.apply_chat_template(
                chat_messages,
                add_generation_prompt=True,
                return_tensors="pt",
            )
            attention_mask = torch.ones_like(input_ids)
        except Exception:
            prompt = "\n".join(
                f"{item['role'].upper()}: {item['content']}" for item in chat_messages
            )
            prompt = prompt + "\nASSISTANT:"
            encoded = self.tokenizer(prompt, return_tensors="pt")
            input_ids = encoded["input_ids"]
            attention_mask = encoded.get("attention_mask")
        device = next(self.model.parameters()).device
        input_ids = input_ids.to(device)
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        else:
            attention_mask = attention_mask.to(device)

        pad_token_id = self.tokenizer.pad_token_id
        if pad_token_id is None:
            pad_token_id = self.tokenizer.eos_token_id

        with torch.inference_mode():
            generated = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                pad_token_id=pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                **self._generation_kwargs(),
            )

        new_tokens = generated[0][input_ids.shape[-1] :]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        return AIMessage(content=text)


class LLMInterface:
    """
    The LLMInterface class provides an interface for interacting with a Language Model (LLM).
    It allows setting the role, configuring the LLM, sending input to the LLM, and retrieving the LLM's response.

    Attributes:
        prompt_manager (PromptManager): The PromptManager instance for managing prompt configurations.
        role (Optional[str]): The current role set for the LLM interface.
        llm (Optional[ChatOpenAI]): The ChatOpenAI instance for interacting with the LLM.
        system_prompt (Optional[str]): The system prompt template for the current role.
        conversation_history (List[Union[HumanMessage, AIMessage]]): The conversation history.
        verbose (bool): Flag to enable verbose logging.

    Methods:
        __init__(self, json_file_path: str, verbose: bool = False)

        set_role(self, role: str) -> bool:

        interact(self, input_text: str, **kwargs) -> Optional[str]:

        get_current_role(self) -> Optional[str]:

        get_available_roles(self) -> List[str]:

        get_conversation_history(self) -> List[Dict[str, str]]:

        clear_memory(self) -> None:
    """

    def __init__(self, config_file_path: str, verbose: bool = False):
        """
        Initialize the LLMInterface with configurations from a JSON file.

        Args:
            config_file_path (str): Path to the JSON file containing prompt and LLM configurations.
            verbose (bool): Flag to enable verbose logging. Defaults to False.
        """
        self.prompt_manager: PromptManager = PromptManager(config_file_path)
        self.role: Optional[str] = None
        self.llm: Optional[ChatOpenAI] = None
        self.system_prompt: Optional[str] = None
        self.conversation_history: List[Union[HumanMessage, AIMessage]] = []
        self.verbose: bool = verbose
        self.interaction_string = None
        # Load API keys from environment
        load_dotenv()
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
            "lamma-chat": os.getenv("TOGETHER_API_KEY"),
            "openrouter": os.getenv("OPENROUTER_API_KEY"),
            "huggingface": os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            "local": os.getenv("LOCAL_API_KEY", "local_key"),
        }
        self.api_bases = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "lamma-chat": "https://api.together.xyz/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "huggingface": os.getenv(
                "HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1"
            ).rstrip("/"),
            "local": os.getenv(
                "LOCAL_AI_BASE_URL", "http://localhost:1234/v1"
            ).rstrip("/"),
        }

    def _resolve_api_credentials(self, llm_config):
        provider = str(llm_config.get("provider", "")).lower()
        model_name = str(llm_config["model_name"])
        model_name_lower = model_name.lower()

        if provider in {"huggingface", "hf"}:
            return self.api_keys["huggingface"], self.api_bases["huggingface"]
        if llm_config.get("local", False):
            return self.api_keys["local"], self.api_bases["local"]
        if provider == "openrouter" or "openrouter" in model_name_lower:
            return self.api_keys["openrouter"], self.api_bases["openrouter"]
        if "deepseek" in model_name_lower:
            return self.api_keys["deepseek"], self.api_bases["deepseek"]
        if any(
            model in model_name_lower
            for model in ["llama", "gemma", "qwen", "mistral", "mixtral"]
        ):
            return self.api_keys["lamma-chat"], self.api_bases["lamma-chat"]
        return self.api_keys["openai"], self.api_bases["openai"]

    def _is_local_hf_provider(self, llm_config) -> bool:
        provider = str(llm_config.get("provider", "")).lower()
        return provider in {
            "local-hf",
            "hf-local",
            "huggingface-local",
            "transformers",
        }

    def set_role(self, role: str) -> bool:
        """
        Set the current role and configure the LLM accordingly.

        This method sets up the LLM and prompt template for the specified role.
        It uses the configurations from the JSON file loaded by the PromptManager.

        Args:
            role (str): The role to set for the LLM interface.

        Returns:
            bool: True if the role was successfully set, False otherwise.
        """
        self.role = role
        self.system_prompt = self.prompt_manager.get_prompt_template(role)
        self.interaction_template = self.prompt_manager.get_interaction_template(role)
        llm_config = self.prompt_manager.get_llm_config(role)

        if self.system_prompt and llm_config:
            callbacks = [StdOutCallbackHandler()] if self.verbose else None
            provider = str(llm_config.get("provider", "")).lower()

            if self._is_local_hf_provider(llm_config):
                self.llm = LocalHuggingFaceChatModel(
                    model_name=llm_config["model_name"],
                    params=llm_config.get("params", {}),
                    hf_local=llm_config.get("hf_local", {}),
                )
                self.conversation_history = []
                logger.info(
                    f"Local Hugging Face model '{llm_config['model_name']}' loaded "
                    f"for role '{role}'."
                )
                return True

            api_key, api_base = self._resolve_api_credentials(llm_config)
            if provider in {"huggingface", "hf"} and not api_key:
                logger.error(
                    "HF_TOKEN is required for Hugging Face Inference Providers."
                )
                return False

            self.llm = ChatOpenAI(
                api_key=api_key,
                base_url=api_base,
                model_name=llm_config["model_name"],
                callbacks=callbacks,
                **llm_config["params"],
            )
            self.conversation_history = []  # Clear history when changing roles
            logger.info(
                f"Model '{llm_config['model_name']}' loaded for role '{role}'. - {api_base}"
            )
            return True
        else:
            logger.opt(exception=True).error(
                f"Role '{role}' not found in the configuration file."
            )
            return False

    def interact(self, **kwargs) -> Optional[str]:
        """
        Interact with the LLM using the current role and configuration.

        This method sends the input to the LLM and returns its response. It handles
        the necessary formatting of inputs based on the current prompt template and
        includes the conversation history.

        Args:

            **kwargs: Additional keyword arguments required by the prompt template.

        Returns:
            Optional[str]: The LLM's response, or None if an error occurred.
        """

        if not self.llm or not self.system_prompt:
            logger.opt(exception=True).error("LLM or system prompt not configured.")
            return None

        try:
            for template in self.interaction_template:
                if all(key in kwargs.keys() for key in template["required_keys"]):
                    self.interaction_string = template["template"]
                    input_text = self.interaction_string.format(**kwargs)
                    break
        except KeyError:
            logger.opt(exception=True).error(
                f"Template not found for the given arguments: {kwargs}"
            )

        try:
            messages = (
                [SystemMessage(content=self.system_prompt)]
                + self.conversation_history
                + [HumanMessage(content=input_text)]
            )

            if self.verbose:
                logger.info("\n--- Sending to LLM ---")
                logger.info(json.dumps([m.dict() for m in messages], indent=2))

            # Get the response from the LLM
            ai_message = self._invoke_with_fallback(messages)

            if self.verbose:
                logger.info("\n--- Received from LLM ---")
                logger.info(json.dumps(ai_message.dict(), indent=2))

            # Update the conversation history
            self.conversation_history.extend(
                [HumanMessage(content=input_text), ai_message]
            )

            return ai_message.content
        except Exception as e:
            logger.opt(exception=True).error(f"Error interacting with LLM: {e}.")
            return None

    def _invoke_with_fallback(self, messages: List[Union[HumanMessage, AIMessage, SystemMessage]]):
        try:
            return self.llm.invoke(messages)
        except ValueError as e:
            error_text = str(e or "")
            if "Sync client is not available" not in error_text or not hasattr(
                self.llm, "ainvoke"
            ):
                raise

            logger.warning(
                "Sync invoke unavailable for role '{}'; falling back to async ainvoke.",
                self.role,
            )
            return self._run_async_llm_call(self.llm.ainvoke(messages))

    def _run_async_llm_call(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result_holder = {}
        error_holder = {}

        def _runner() -> None:
            try:
                result_holder["value"] = asyncio.run(coroutine)
            except Exception as exc:
                error_holder["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_holder:
            raise error_holder["error"]
        return result_holder.get("value")

    def get_current_role(self) -> Optional[str]:
        """
        Get the current role of the LLM interface.

        Returns:
            Optional[str]: The current role, or None if no role is set.
        """
        return self.role

    def get_available_roles(self) -> List[str]:
        """
        Get a list of all available roles from the configuration.

        Returns:
            List[str]: A list of available role names.
        """
        return self.prompt_manager.get_roles()

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Retrieve the conversation history.

        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the conversation history.
            Each dictionary contains 'role' (either 'human' or 'ai') and 'content' keys.
        """
        return [
            {
                "role": "human" if isinstance(msg, HumanMessage) else "ai",
                "content": msg.content,
            }
            for msg in self.conversation_history
        ]

    def clear_memory(self) -> None:
        """
        Clear the conversation history.
        """
        self.conversation_history = []
        logger.info("Conversation history cleared.")


# Usage example
if __name__ == "__main__":
    # Set up environment variables for the OpenAI API
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize the LLMInterface with the configuration file and verbose logging
    json_file_path = "src/agent_config_v6.yml"
    agent = LLMInterface(json_file_path, verbose=False)

    logger.info(f"Available roles: {agent.get_available_roles()}")
    # Example usage with the "question_designer" role
    if agent.set_role("challenge_designer"):
        response = agent.interact(
            input_text="Generate a coding problem for the following concept: two sum and the difficulty: very hard",
        )
        logger.info(f"Question Designer response: {response}")
        response = agent.interact(
            input_text="Generate a coding problem for the following concept: binary search",
        )

        logger.info(f"Question Designer response: {response}")
        print(agent.get_conversation_history())
        # Store the question for use with the test generator
        question = response
