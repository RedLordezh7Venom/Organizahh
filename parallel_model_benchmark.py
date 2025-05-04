"""
Benchmark script to compare Groq, Gemini, and Llamafile performance in parallel.
"""
import os
import time
import json
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from datetime import datetime

# Import model-specific libraries
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAI
from langchain_community.llms.llamafile import Llamafile
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough

# Import directory listing function
from listdir import list_files_and_folders

# Load environment variables
load_dotenv()

# Directory to analyze
directory = "D:/Users/prabh/Downloads - Copy"

# Get files and folders
files_and_folders = list_files_and_folders(directory)

# Create the prompt template - Note the double curly braces to escape them
prompt_template = PromptTemplate.from_template("""
You are given a list of files and folders from a directory:
{files_and_folders}

Your task is to generate a JSON structure that organizes the files into topics and subtopics. 
Give the output json only, not any other text.
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
""")

# Function to run a model and measure execution time
def run_model(model_name, model_instance):
    print(f"Starting {model_name}...")
    start_time = time.time()
    
    try:
        # Create runnable chain using the new LangChain syntax
        chain = prompt_template | model_instance
        
        # Run the chain
        response = chain.invoke({"files_and_folders": files_and_folders})
        
        # Get the text from the response (handling different response types)
        if hasattr(response, 'content'):
            # For ChatGroq which returns a message
            response_text = response.content
        elif isinstance(response, str):
            # For models that return a string directly
            response_text = response
        else:
            # Try to get a string representation
            response_text = str(response)
        
        # Clean up response if needed
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Try to parse JSON
        try:
            if response_text.startswith("{") and response_text.endswith("}"):
                json_data = json.loads(response_text)
                json_valid = True
            else:
                # Try to extract JSON
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    json_data = json.loads(json_str)
                    json_valid = True
                else:
                    json_valid = False
                    json_data = None
        except json.JSONDecodeError:
            json_valid = False
            json_data = None
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            "model": model_name,
            "execution_time": execution_time,
            "success": True,
            "json_valid": json_valid,
            "categories": len(json_data) if json_valid else 0,
            "error": None,
            "raw_response": response_text[:500]  # Store first 500 chars for debugging
        }
    
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            "model": model_name,
            "execution_time": execution_time,
            "success": False,
            "json_valid": False,
            "categories": 0,
            "error": str(e),
            "raw_response": None
        }

# Main function to run all models in parallel
def run_benchmark():
    # Initialize models
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_model = ChatGroq(
            api_key=groq_api_key,
            model_name="gemma2-9b-it"
        )
    except Exception as e:
        print(f"Error initializing Groq: {e}")
        groq_model = None
    
    try:
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        gemini_model = GoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=gemini_api_key
        )
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        gemini_model = None
    
    try:
        llamafile_model = Llamafile()
    except Exception as e:
        print(f"Error initializing Llamafile: {e}")
        llamafile_model = None
    
    # Create list of models to run
    models_to_run = []
    if groq_model:
        models_to_run.append(("Groq (gemma2-9b-it)", groq_model))
    if gemini_model:
        models_to_run.append(("Gemini 2.0 Pro", gemini_model))
    if llamafile_model:
        models_to_run.append(("Llamafile", llamafile_model))
    
    if not models_to_run:
        print("No models available to run. Please check your API keys and model configurations.")
        return
    
    # Run models in parallel using ThreadPoolExecutor
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_model = {
            executor.submit(run_model, name, model): name
            for name, model in models_to_run
        }
        
        for future in concurrent.futures.as_completed(future_to_model):
            model_name = future_to_model[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✅ {model_name} completed in {result['execution_time']:.2f} seconds")
            except Exception as e:
                print(f"❌ {model_name} failed: {e}")
    
    # Sort results by execution time
    results.sort(key=lambda x: x["execution_time"])
    
    # Print results
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    
    for i, result in enumerate(results):
        print(f"{i+1}. {result['model']}:")
        print(f"   Time: {result['execution_time']:.2f} seconds")
        print(f"   Success: {result['success']}")
        print(f"   Valid JSON: {result['json_valid']}")
        if result['json_valid']:
            print(f"   Categories: {result['categories']}")
        if result['error']:
            print(f"   Error: {result['error']}")
        print()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_{timestamp}.json"
    
    # Get file count - handle both list and string return types from list_files_and_folders
    if isinstance(files_and_folders, list):
        file_count = len(files_and_folders)
    else:
        file_count = len(files_and_folders.split("\n"))
    
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "directory": directory,
            "file_count": file_count,
            "results": results
        }, f, indent=2)
    
    print(f"Results saved to {results_file}")

if __name__ == "__main__":
    print("Starting parallel model benchmark...")
    run_benchmark()