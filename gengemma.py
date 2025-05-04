from langchain_community.llms.llamafile import Llamafile

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from listdir import list_files_and_folders
import os


directory = "D:/Users/prabh/Downloads - Copy"

files_and_folders = list_files_and_folders(directory)

import json

# Initialize Google GenAI model (replace with the actual setup for Google GenAI)
llm = Llamafile()
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
#add chunking for huge directories

# Use LangChain to interact with Google GenAI
chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(prompt))
# Pass the 'files_and_folders' variable as input to the chain
response = chain.run({"files_and_folders": files_and_folders})
response = response[7:-4]
generated_json = json.loads(response)

print(json.dumps(generated_json, indent=2))
