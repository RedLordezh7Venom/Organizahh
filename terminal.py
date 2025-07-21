import os
import sys
import json
import regex as re
import subprocess
from dotenv import load_dotenv

try:
    from langchain_google_genai import GoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: Langchain or Google GenAI not installed. LLM features will be disabled.")
    class GoogleGenerativeAI: pass
    class PromptTemplate: pass
from scripts.prompt_templates import prompt_template_gemini

load_dotenv()

def get_files_in_folder(folder_path):
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

def generate_structure_with_gemini(files):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not LANGCHAIN_AVAILABLE or not api_key:
        print("Gemini/Google GenAI not available. Falling back to extension-based organization.")
        return None
    llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
    prompt = PromptTemplate.from_template(prompt_template_gemini)
    chain = prompt | llm
    files_list_str = "\n".join(files)
    response = chain.invoke({"files_list": files_list_str})
    llm_output = response.strip()
    if not llm_output.startswith('{') or not llm_output.endswith('}'):
        match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if match:
            llm_output = match.group(0)
        else:
            print("Failed to extract JSON from Gemini output.")
            return None
    try:
        structure = json.loads(llm_output)
        return structure
    except Exception as e:
        print(f"Error parsing Gemini output: {e}")
        return None

def move_files_according_to_structure(folder_path, structure):
    moves = []
    for category, contents in structure.items():
        if isinstance(contents, dict):
            for subcat, files in contents.items():
                target_dir = os.path.join(folder_path, category, subcat)
                os.makedirs(target_dir, exist_ok=True)
                for file in files:
                    src = os.path.join(folder_path, file)
                    dst = os.path.join(target_dir, file)
                    if os.path.exists(src):
                        os.rename(src, dst)
                        moves.append((dst, src))  # Record move for undo
        elif isinstance(contents, list):
            target_dir = os.path.join(folder_path, category)
            os.makedirs(target_dir, exist_ok=True)
            for file in contents:
                src = os.path.join(folder_path, file)
                dst = os.path.join(target_dir, file)
                if os.path.exists(src):
                    os.rename(src, dst)
                    moves.append((dst, src))  # Record move for undo
    return moves

def main():
    if len(sys.argv) < 2:
        print("Usage: python terminal.py <folder_path>")
        sys.exit(1)
    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print("Invalid folder path.")
        sys.exit(1)
    files = get_files_in_folder(folder_path)
    if not files:
        print("No files found in the folder.")
        sys.exit(0)
    print(f"Found {len(files)} files. Generating organization structure with Gemini...")
    structure = generate_structure_with_gemini(files)
    if not structure:
        print("Failed to generate structure with Gemini. Exiting.")
        sys.exit(1)
    print("\nProposed Organization Structure:")
    print(json.dumps(structure, indent=2))
    # Save structure to temp file for editing
    temp_json = os.path.join(folder_path, "_organization_structure.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)
    # Choose default editor based on OS
    if os.name == "nt":
        default_editor = "notepad"
    else:
        default_editor = "nano"
    editor = os.environ.get("EDITOR", default_editor)
    print(f"\nYou can edit the structure using {editor}. Press Enter to continue, or Ctrl+C to abort.")
    input()
    subprocess.call([editor, temp_json])
    with open(temp_json, "r", encoding="utf-8") as f:
        edited_structure = json.load(f)
    print("\nUsing edited structure to organize files...")
    moves = move_files_according_to_structure(folder_path, edited_structure)
    print("Organization complete.")

    # Offer undo option
    undo = input("\nWould you like to undo the organization and restore files to their original locations? (y/N): ").strip().lower()
    if undo == "y":
        for src, dst in moves:
            if os.path.exists(src):
                os.rename(src, dst)
        print("Undo complete. Files restored to their original locations.")

if __name__ == "__main__":
    main()
