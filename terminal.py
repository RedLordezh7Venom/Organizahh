import os
import sys
import json
import regex as re
import subprocess
import argparse
from dotenv import load_dotenv

# --- LangChain Imports ---
try:
    from langchain_ollama.llms import OllamaLLM
    from langchain_google_genai.llms import GoogleGenerativeAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain or Qwen not installed. LLM features will be disabled.")
    class OllamaLLM: pass

load_dotenv()

# --- Utils ---
def get_files_in_folder(folder_path):
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

from scripts.llama_cpp_custom import get_qllm  # ✅ Same as you used

# --- Step 1: Folder structure generation ---
def generate_folder_structure(files, user_instructions, llm):
    prompt_text = f"""
You are an expert file organizer.

User's specific instructions (override defaults if applicable):
{user_instructions}

Generate ONLY a JSON folder structure (categories + subcategories) based on these files.
Do not assign files yet, keep arrays empty.

Files: {json.dumps(files, indent=2)}

STRICTLY return valid JSON, no extra text.
"""
    response = llm.invoke(prompt_text)
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        print("⚠️ Failed to extract JSON for folder structure.")
        print(response)
        return None
    return json.loads(match.group(0))

# --- Step 2: File assignment ---
def assign_files_to_structure(files, existing_structure, user_instructions, llm):
    prompt_text = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:

                        {{
                          "Topic_1": {{
                            "Subtopic_1": [ "file1.txt", "file2.pdf" ],
                            "Subtopic_2": [ "imageA.jpg" ]
                          }},
                          "Topic_2": [ "archive.zip", "installer.exe" ]
                        }}
Also , if user calls for specific instructions, follow them too:
                        User's specific instructions:
{user_instructions}

Assign the following files into the given folder structure by filling ONLY the arrays. 
DO NOT create new folders. If no suitable folder exists, place the file under "Miscellaneous".

FOLDER STRUCTURE:
{json.dumps(existing_structure, indent=2)}

FILES:
{json.dumps(files, indent=2)}

Return ONLY updated JSON.
"""
    response = llm.invoke(prompt_text)
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        print("⚠️ Failed to extract JSON for file assignment.")
        return None
    return json.loads(match.group(0))

# --- Merge updated batches into main structure ---
def merge_structures(base, new):
    for cat, content in new.items():
        if cat not in base:
            base[cat] = content
            continue

        if isinstance(base[cat], dict) and isinstance(content, dict):
            for subcat, subfiles in content.items():
                if subcat not in base[cat]:
                    base[cat][subcat] = subfiles
                else:
                    if isinstance(base[cat][subcat], list):
                        base[cat][subcat].extend(subfiles)
        elif isinstance(base[cat], list) and isinstance(content, list):
            base[cat].extend(content)
    return base

# --- File Moving ---
def move_files_according_to_structure(folder_path, structure, current_path=""):
    moves = []
    base_path = os.path.join(folder_path, current_path) if current_path else folder_path
    os.makedirs(base_path, exist_ok=True)

    for category, contents in structure.items():
        target_path = os.path.join(base_path, category)

        if isinstance(contents, list):
            os.makedirs(target_path, exist_ok=True)
            for file in contents:
                if isinstance(file, str):
                    src = os.path.join(folder_path, file)
                    dst = os.path.join(target_path, file)
                    if os.path.exists(src):
                        os.rename(src, dst)
                        moves.append((dst, src))
        elif isinstance(contents, dict):
            os.makedirs(target_path, exist_ok=True)
            moves.extend(move_files_according_to_structure(folder_path, contents, os.path.join(current_path, category)))
    return moves

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Reactive File Organizer")
    parser.add_argument("folder_path", help="Folder to organize")
    parser.add_argument("--instruction", type=str, default="Organize files intelligently.",
                        help="Custom instruction for organizing files")
    parser.add_argument("--offline", nargs='?', const='qwen', default=None,
                        help='Use an offline model. Specify "ollama" for Ollama, otherwise Qwen is used.')
    args = parser.parse_args()

    folder_path = args.folder_path
    if not os.path.isdir(folder_path):
        print("Invalid folder path.")
        sys.exit(1)

    # --- LLM Initialization ---
    llm = None
    model_name = ""
    if args.offline == 'ollama':
        model_name = "Ollama"
        print(f"Using {model_name} model.")
        llm = OllamaLLM(model="gemma3:270m")  # Assuming a default model for ollama
    elif args.offline == 'qwen':
        model_name = "Qwen"
        print(f"Using {model_name} model.")
        llm = get_qllm()
    else:
        model_name = "Gemini"
        print(f"Using {model_name} model.")
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            api_key = input("Please enter your Google Gemini API key: ").strip()
            if api_key:
                with open(".env", "a") as f:
                    f.write(f"\nGOOGLE_API_KEY={api_key}")
                load_dotenv() # Reload .env to make the new key available
                api_key = os.getenv('GOOGLE_API_KEY')
            else:
                print("API key is required for Gemini. Exiting.")
                sys.exit(1)
        llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)


    files = get_files_in_folder(folder_path)
    if not files:
        print("No files found.")
        sys.exit(0)

    print(f"📂 Found {len(files)} files. Generating structure with {model_name}...")
    structure = generate_folder_structure(files, args.instruction, llm)
    if not structure:
        print("❌ Failed to generate folder structure.")
        sys.exit(1)

    print("✅ Folder structure generated. Assigning files...")
    batch_size = 15
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        print(f"Assigning batch {i//batch_size + 1}/{(len(files)+batch_size-1)//batch_size}...")
        updated = assign_files_to_structure(batch, structure, args.instruction, llm)
        if updated:
            structure = merge_structures(structure, updated)

    print("\n✅ Final Proposed Organization Structure:")
    print(json.dumps(structure, indent=2))

    temp_json = os.path.join(folder_path, "_organization_structure.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)

    editor = "notepad" if os.name == "nt" else "nano"
    subprocess.call([editor, temp_json])

    with open(temp_json, "r", encoding="utf-8") as f:
        edited_structure = json.load(f)

    print("\n🚀 Organizing files...")
    moves = move_files_according_to_structure(folder_path, edited_structure)
    print(f"✅ Done. Moved {len(moves)} files.")

    if input("Undo organization? (y/N): ").strip().lower() == "y":
        for src, dst in moves:
            if os.path.exists(src):
                os.rename(src, dst)
        print("↩️ Undo complete.")

if __name__ == "__main__":
    main()
