from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from listdir import list_files_and_folders
import os
import json

directory = "D:/Users/prabh/Downloads - Copy"
files_and_folders = list_files_and_folders(directory)

api_key = os.getenv('GOOGLE_API_KEY')
llm = GoogleGenerativeAI(model="gemini-2.0-flash", api_key=api_key)
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
chain = PromptTemplate.from_template(prompt) | llm

response = chain.invoke({"files_and_folders": files_and_folders})
 
try:
    generated_json = json.loads(response)
except json.JSONDecodeError:
    # Try to extract JSON from the response if extra text is present
    import re
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        generated_json = json.loads(match.group(0))
    else:
        raise

print(json.dumps(generated_json, indent=2))