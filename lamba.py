import os
import sys
import json
import time
import argparse

# Import required libraries with error handling
try:
    from listdir import list_files_and_folders
    import requests
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please install the required packages with:")
    print("pip install requests")
    sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Organize files using LLM")
    parser.add_argument("--directory", "-d", type=str,
                        default="C:/Users/prabh/Downloads",
                        help="Directory to organize")
    parser.add_argument("--timeout", "-t", type=int, default=300,
                        help="Timeout in seconds for LLM request (default: 300)")
    parser.add_argument("--url", "-u", type=str,
                        default="http://localhost:8080",
                        help="Base URL for Llamafile server (default: http://localhost:8080)")
    parser.add_argument("--temperature", type=float, default=0,
                        help="Temperature for LLM generation (default: 0)")
    parser.add_argument("--seed", type=int, default=0,
                        help="Seed for LLM generation (default: 0)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file for JSON result (default: None)")
    return parser.parse_args()

def check_server(base_url, timeout=5):
    """Check if the Llamafile server is running"""
    try:
        import requests
        response = requests.get(f"{base_url}/v1/models", timeout=timeout)
        if response.status_code == 200:
            models = response.json().get("data", [])
            model_names = [model.get("id") for model in models]
            print(f"✅ Connected to Llamafile server at {base_url}")
            print(f"📋 Available models: {', '.join(model_names)}")
            return True
    except Exception as e:
        print(f"❌ Error connecting to Llamafile server: {e}")
        print(f"Please make sure the server is running at {base_url}")
        return False

def main():
    """Main function"""
    args = parse_arguments()

    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        return

    # Check if server is running
    if not check_server(args.url):
        return

    try:
        # Get files and folders
        print(f"📂 Scanning directory: {args.directory}")
        files_and_folders = list_files_and_folders(args.directory)

        # Create prompt
        prompt = f"""
        You are given a list of files and folders from a directory:
        {files_and_folders}

        Your task is to generate a JSON structure that organizes the files into topics and subtopics.
        Give the output JSON only, not any other text.
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

        # Send request to LLM
        print("🤖 Sending request to LLM...")
        print("⏳ This may take a while depending on the number of files...")
        start_time = time.time()

        try:
            # Use a direct API call instead of the llama_index library
            print("Using direct API call to avoid timeout issues...")

            # Prepare the payload
            payload = {
                "model": "gemma-2-2b-it.Q8_0.gguf",  # Use the model name from the server
                "messages": [
                    {"role": "system", "content": "You are a file assistant. Help the user organize files using good semantic understanding of file names."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": args.temperature,
                "stream": False
            }

            # Make the API call directly
            import requests
            response = requests.post(
                f"{args.url}/v1/chat/completions",
                json=payload,
                timeout=args.timeout
            )

            # Check if the request was successful
            if response.status_code == 200:
                elapsed_time = time.time() - start_time
                print(f"✅ Response received in {elapsed_time:.2f} seconds")

                # Parse the response
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Print response
                print("\n📝 Organization structure:")
                print(content)

                # Save to file if requested
                if args.output:
                    try:
                        # Try to parse as JSON to validate
                        json_obj = json.loads(content)

                        # Save to file
                        with open(args.output, 'w') as f:
                            json.dump(json_obj, f, indent=2)
                        print(f"✅ Saved organization structure to {args.output}")
                    except json.JSONDecodeError:
                        print("⚠️ Response is not valid JSON. Saving raw response instead.")
                        with open(args.output, 'w') as f:
                            f.write(content)
                        print(f"✅ Saved raw response to {args.output}")
                    except Exception as e:
                        print(f"❌ Error saving to file: {e}")
            else:
                print(f"❌ API request failed with status code: {response.status_code}")
                print(f"Response: {response.text}")

        except requests.exceptions.Timeout:
            print("❌ Request timed out. The model is taking too long to respond.")
            print(f"   Try increasing the timeout (current: {args.timeout} seconds)")
            print("   Or reduce the number of files being processed")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
        except Exception as e:
            print(f"❌ Error during LLM request: {e}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
