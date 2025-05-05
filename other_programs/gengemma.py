from langchain_community.llms.llamafile import Llamafile
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from listdir import list_files_and_folders
import os
import json
from collections import defaultdict

# Load directory contents
directory = "D:/Users/prabh/Downloads"
files_and_folders = list_files_and_folders(directory)

# Initialize LLM and Prompt
llm = Llamafile()
prompt = r"""
You are given a list of files and folders from a directory:
Your task is to generate a JSON structure that organizes the files into topics and subtopics. 
Give the output JSON only, not any other text.
Group similar files together under the appropriate categories. The structure should look like this:

"""

chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(prompt))

# Chunking utility
def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

# Merge logic for combining JSON results
def deep_merge(d1, d2):
    for key, value in d2.items():
        if key in d1:
            if isinstance(d1[key], dict) and isinstance(value, dict):
                deep_merge(d1[key], value)
            else:
                d1[key] = value
        else:
            d1[key] = value
    return d1

# Process in batches
batch_size = 10  # Adjust based on token limits
final_result = {}

for batch in chunk_list(files_and_folders, batch_size):
    input_str = "\n".join(batch)
    response = chain.run({"files_and_folders": input_str})

    # Optionally clean the response
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        cleaned_json_str = response[json_start:json_end]
        batch_json = json.loads(cleaned_json_str)
        final_result = deep_merge(final_result, batch_json)
    except Exception as e:
        print("Error processing batch:", e)
        print("Raw response:", response)

# Output final merged JSON
print(json.dumps(final_result, indent=2))
