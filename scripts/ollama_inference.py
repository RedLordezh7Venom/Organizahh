# prompt: use ollama model
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import json
import time
import sys

def list_files_and_folders(directory):
    return os.listdir(directory)

# Directory to analyze
directory = "C:/Users/prabh/Downloads" 

# Get files and folders
try:
    files_and_folders = list_files_and_folders(directory)
    print(f"Found {len(files_and_folders)} files and folders in {directory}")
except Exception as e:
    print(f"Error listing directory: {e}")
    sys.exit(1)

# Limit the number of files to process (to avoid overwhelming the model)
MAX_FILES = 200
if len(files_and_folders) > MAX_FILES:
    print(f"Limiting to {MAX_FILES} files for processing")
    files_and_folders = files_and_folders[:MAX_FILES]

# Create the prompt template with properly escaped curly braces
prompt_template = PromptTemplate.from_template("""
You are an expert file organizer. Given a list of filenames  :  {files_and_folders} from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        The output MUST be ONLY a valid JSON object, starting with {{ and ending with }}. Do not include any explanations, markdown formatting (like ```json), or other text outside the JSON structure.
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:

                        {{
                          "Topic_1": {{
                            "Subtopic_1": [ "file1.txt", "file2.pdf" ],
                            "Subtopic_2": [ "imageA.jpg" ]
                          }},
                          "Topic_2": [ "archive.zip", "installer.exe" ]
                        }}

""")

# Function to initialize Ollama with retry logic
def initialize_ollama(max_retries=3, retry_delay=2):
    from langchain_ollama.llms import OllamaLLM
    
    for attempt in range(max_retries):
        try:
            print(f"Initializing Ollama (attempt {attempt+1}/{max_retries})...")
            ollama_llm = OllamaLLM(model="llama3.1:8b",temperature=0.3)
            
            # Test the connection with a simple query
            print("Testing Ollama connection...")
            test_response = ollama_llm.invoke("Hello")
            print(f"Connection test successful: {test_response[:20]}...")
            
            return ollama_llm
        
        except Exception as e:
            print(f"Error initializing Ollama (attempt {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("Max retries reached. Could not connect to Ollama.")
                raise

# Main execution with error handling
try:
    # Initialize Ollama
    ollama_llm = initialize_ollama()
    
    # Create and run the chain
    print("Creating LangChain chain...")
    chain = prompt_template | ollama_llm
    
    # Run the chain with the new invoke method
    print("Running inference (this may take a while)...")
    response = chain.invoke({"files_and_folders": files_and_folders})
    
    # Process the response
    print("Processing response...")
    
    # Clean up response if needed (extract JSON)
    if isinstance(response, str):
        response_text = response
    else:
        # Try to get a string representation
        response_text = str(response)
    
    # Extract JSON from the response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    # Try to parse JSON
    try:
        if response_text.startswith("{") and response_text.endswith("}"):
            generated_json = json.loads(response_text)
        else:
            # Try to extract JSON
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                generated_json = json.loads(json_str)
            else:
                print("Could not find valid JSON in the response")
                print("Raw response:", response_text)
                sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Raw response:", response_text)
        sys.exit(1)
    
    # Print the result
    print("\nGenerated organization structure:")
    print(json.dumps(generated_json, indent=2))
    
    # Save to file
    output_file = "ollama_organization.json"
    with open(output_file, "w") as f:
        json.dump(generated_json, f, indent=2)
    print(f"\nSaved organization structure to {output_file}")

except KeyboardInterrupt:
    print("\nOperation cancelled by user")
    sys.exit(1)
except Exception as e:
    print(f"\nError during execution: {e}")
    sys.exit(1)