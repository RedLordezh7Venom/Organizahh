from llama_cpp import Llama

mistral = Llama.from_pretrained(repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
                                filename="*q4_0.gguf",
                                verbose=False
                               ) 

resp = mistral("Q: Write a short paragraph introducing Elon Musk. A: ",
           max_tokens=256,
           stop=["Q:", "\n"])
           
resp = mistral("Give folder names for these files  :  result.xslx, marks.pdf, icecream.png, student.sqlite",
           max_tokens=256,
           stop=["Q:", "\n"])

print(resp)