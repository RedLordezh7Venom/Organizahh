from llama_cpp import Llama

qwen = Llama.from_pretrained(repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
                                filename="*q4_0.gguf",
                                verbose=False
                               ) 
           
if __name__ == "__main__":
    resp = qwen("Generate 3 file names",
            max_tokens=2048,)

    print(resp)