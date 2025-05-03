# prompt: use ollama model
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
def list_files_and_folders(directory):
    return os.listdir(directory)

directory = "D:/Users/prabh/Downloads - Copy"

files_and_folders = list_files_and_folders(directory)

import json
# Assuming you've already installed and started the Ollama server as shown in the original code.

from langchain_ollama  import OllamaLLM

ollama_llm = OllamaLLM(model="gemma3:1b-it-q8_0") # Replace with your model name

prompt = r"""
You are given a list of files and folders from a directory:
{files_and_folders}

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
"""


# Use LangChain to interact with Google GenAI
chain = LLMChain(llm=ollama_llm, prompt=PromptTemplate.from_template(prompt))
# Pass the 'files_and_folders' variable as input to the chain
response = chain.run({"files_and_folders": files_and_folders})
response = response[7:-4]
generated_json = json.loads(response)
print(response)