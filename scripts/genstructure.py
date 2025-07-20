from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_core.output_parsers import JsonOutputParser
from listdir import list_files_and_folders
import os
import json
from dotenv import load_dotenv
from pydantic import RootModel
from typing import Dict, Any

load_dotenv()

directory = "C:/Users/prabh/Downloads"
files_and_folders = list_files_and_folders(directory)

# Define the expected output structure using Pydantic
# Using RootModel to directly represent the structure without a wrapper
class FileOrganization(RootModel):
    """File organization structure with topics and subtopics."""
    root: Dict[str, Any]

# Initialize the JSON output parser
parser = JsonOutputParser(pydantic_object=FileOrganization)

# Get the API key and initialize the LLM
api_key = os.getenv('GOOGLE_API_KEY')
llm = GoogleGenerativeAI(model="gemini-2.0-flash", api_key=api_key)

# Create a text splitter for handling large file lists
text_splitter = RecursiveJsonSplitter(
    max_chunk_size=4000  # Adjust based on model's context window
)

# Split the files_and_folders list into manageable chunks
if isinstance(files_and_folders, list):
    # Convert list to a dictionary for the splitter
    files_dict = {"files": files_and_folders}
    chunks = text_splitter.split_json(files_dict, convert_lists=True)
else:
    # If already a dictionary or other structure, split directly
    chunks = text_splitter.split_json(files_and_folders, convert_lists=True)

print(f"Split input into {len(chunks)} chunks for processing")

# Create the prompt template with format instructions from the parser
prompt = PromptTemplate(
    template=r"""
You are given a list of files and folders from a directory:
{files_chunk}

Your task is to generate a JSON structure that organizes the files into topics and subtopics.
{format_instructions}
Group similar files together under the appropriate categories.

The structure should look like this:
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
""",
    input_variables=["files_chunk"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

# Process each chunk and merge the results
all_results = {}

for i, chunk in enumerate(chunks):
    print(f"Processing chunk {i+1}/{len(chunks)}...")

    # Create the chain for this chunk
    chain = prompt | llm | parser

    # Process the chunk
    try:
        result = chain.invoke({"files_chunk": json.dumps(chunk, indent=2)})

        # Merge the result into the overall structure
        if not all_results:
            # Check if result is a RootModel or a dict
            all_results = result.root if hasattr(result, 'root') else result
        else:
            # Get the structure from the result
            result_struct = result.root if hasattr(result, 'root') else result
            # Merge the new structure with the existing one
            for topic, content in result_struct.items():
                if topic in all_results:
                    # If topic already exists, merge subtopics
                    if isinstance(content, dict) and isinstance(all_results[topic], dict):
                        for subtopic, files in content.items():
                            if subtopic in all_results[topic]:
                                # Merge files in existing subtopic
                                all_results[topic][subtopic].update(files)
                            else:
                                # Add new subtopic
                                all_results[topic][subtopic] = files
                    else:
                        # If not a dict, just update
                        all_results[topic].update(content)
                else:
                    # Add new topic
                    all_results[topic] = content
    except Exception as e:
        print(f"Error processing chunk {i+1}: {e}")
        # Continue with other chunks even if one fails

# Print the final organized structure
print(json.dumps(all_results, indent=2))