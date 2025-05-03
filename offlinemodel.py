from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForCausalLM
import torch
import json

# Load model and tokenizer
model_name = "optimum/gpt-2"  # or a local path to your ONNX model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = ORTModelForCausalLM.from_pretrained(model_name)

# Your directory listing logic (example stub)
def list_files_and_folders(directory):
    import os
    items = os.listdir(directory)
    return "\n".join(items)

directory = "D:/Users/prabh/Downloads - Copy"
files_and_folders = list_files_and_folders(directory)

# Prompt
prompt = r"""
You are given a list of files and folders from a directory:
{files_and_folders}

Your task is to generate a JSON structure that organizes the files into topics and subtopics.
Give the output JSON only, nothing else.
Your task is to generate a JSON structure that organizes the files into topics and subtopics. 
give the output json only , not any other text
Group similar files together under the appropriate categories. The structure should look like this:

{{
  "Topic_1": {{
    "Subtopic_1": {{
      "file1.txt": "document",
      "file2.pdf": "document"
    }},
    "Subtopic_2": {{
      "file3.zip": "archive"
    }}
  }},
  "Topic_2": {{
    "Subtopic_1": {{
      "file4.exe": "installer"
    }}
  }}
}}
"
"""

# Tokenize and generate
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=512)
generated = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Try to extract JSON (very primitive cleaning)
try:
    json_str = generated[generated.find("{"):generated.rfind("}")+1]
    generated_json = json.loads(json_str)
    print(json.dumps(generated_json, indent=2))
except Exception as e:
    print("Raw output:\n", generated)
    print("\nFailed to parse JSON:", e)
