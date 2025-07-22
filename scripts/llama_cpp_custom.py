# scripts/llama_cpp_custom.py
from llama_cpp import Llama
from langchain.llms.base import LLM
from typing import Optional, List
from pydantic import PrivateAttr

class MyQwenLLM(LLM):
    _model: Llama = PrivateAttr()

    def __init__(self, model: Llama, **kwargs):
        super().__init__(**kwargs)
        self._model = model

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        output = self._model(prompt, max_tokens=200)
        return output["choices"][0]["text"].strip()

    @property
    def _llm_type(self) -> str:
        return "custom-qwen"


# ✅ Lazy Singleton (model loads only when first called)
_qwen_instance: Optional[MyQwenLLM] = None

def get_qllm() -> MyQwenLLM:
    global _qwen_instance
    if _qwen_instance is None:
        print("🔄 Initializing Qwen model...")
        qwen_model = Llama.from_pretrained(
            repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
            filename="*q4_0.gguf",
            verbose=False,
            n_ctx=8192
        )
        _qwen_instance = MyQwenLLM(model=qwen_model)
        print("✅ Qwen model initialized.")
    return _qwen_instance
