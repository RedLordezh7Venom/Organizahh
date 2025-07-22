from llama_cpp import Llama
from langchain.llms.base import LLM
from typing import Optional, List, Any
from pydantic import PrivateAttr  # ✅ Use for non-validated attributes


class MyQwenLLM(LLM):
    """
    Custom LangChain-compatible LLM wrapper for Qwen GGUF via llama.cpp
    """

    # ✅ Properly define as a private attribute (not validated by Pydantic)
    _model: Llama = PrivateAttr()

    def __init__(self, model: Llama, **kwargs):
        super().__init__(**kwargs)
        self._model = model

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        output = self._model(
            prompt,
            max_tokens=200
        )
        return output["choices"][0]["text"].strip()

    @property
    def _llm_type(self) -> str:
        return "custom-qwen"


# ✅ Initialize the llama.cpp model (only once)
qwen_model = Llama.from_pretrained(
    repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
    filename="*q4_0.gguf",
    verbose=False,
    n_ctx=4096
)

# ✅ LangChain-compatible LLM instance
llm = MyQwenLLM(model=qwen_model)


def generate_file_names() -> str:
    """Example function to test the base LLM."""
    return llm.invoke("Generate 3 realistic file names for documents, like reports or notes. " )


if __name__ == "__main__":
    print("Running standalone test...\n")
    print(generate_file_names())
