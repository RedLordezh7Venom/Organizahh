from llama_cpp import Llama

mistral = Llama.from_pretrained(repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
                                filename="*q4_0.gguf",
                                verbose=False
                               ) 
           
resp = mistral("Generate 3 file names",
           max_tokens=256,
           stop=["Q:", "\n"])

print(resp)