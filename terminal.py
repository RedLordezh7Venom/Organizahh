import os
import sys
import json
import regex as re
import subprocess
from dotenv import load_dotenv

# --- LangChain Imports ---
try:
    from langchain_google_genai import GoogleGenerativeAI
    from langchain_ollama.llms import OllamaLLM
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain or Google GenAI not installed. LLM features will be disabled.")
    class GoogleGenerativeAI: pass

load_dotenv()

# --- Utility Functions ---
def get_files_in_folder(folder_path):
    """Return list of files in the given folder."""
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]


# --- LLM Functions ---
def generate_folder_structure_with_gemini():
    """Step 1: Generate only folder/subfolder structure with empty lists."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not LANGCHAIN_AVAILABLE or not api_key:
        print("Gemini/Google GenAI not available.")
        return None

    from scripts.llama_cpp_custom import get_qllm
    # llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
    # llm = OllamaLLM(model = "qwen2.5:3b")
    llm = get_qllm()
    prompt_text = r"""
    You are an expert file organizer. 
    Generate a JSON folder structure with categories and subcategories based only on common types of files 
    (Documents, Media, Code, Executables, Archives, etc.).
    All lists should be empty for now. STRICTLY return valid JSON only.
    Example:
    {
      "Documents": {
        "Finance": [],
        "Planning": []
      },
      "Media": {
        "Images": [],
        "Videos": []
      },
      "Executables": [],
      "Miscellaneous": []
    }
    """
    prompt_template_reactive = r"""
You are an expert file organizer. Given a list of filenames, you will create a JSON structure organizing them intelligently.

User's specific instructions (override defaults if needed):
{user_instructions}

Follow these rules:
{format_instructions}

Example:
Files: ["budget_2024.xlsx", "team_photo.jpg"]
Output:
{{
  "Finance": ["budget_2024.xlsx"],
  "Media": ["team_photo.jpg"]
}}

Here is the list of files:
{files_chunk}
"""
    response = llm.invoke(prompt_text)
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if not match:
        print("Failed to extract JSON for folder structure.")
        return None
    return json.loads(match.group(0))


def assign_files_to_structure_with_gemini(files, existing_structure):
    """Step 2: Assign given files into existing folder structure."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not LANGCHAIN_AVAILABLE or not api_key:
        print("Gemini/Google GenAI not available.")
        return None

    llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
    prompt_text = f"""
    You are an expert file organizer.

    Put the following files into this folder structure by filling the arrays only. 
    DO NOT create new folders. If no suitable folder exists, put the file under "Miscellaneous".

    FOLDER STRUCTURE:
    {json.dumps(existing_structure, indent=2)}

    FILES:
    {json.dumps(files, indent=2)}

    Return ONLY the updated JSON structure.
    """
    response = llm.invoke(prompt_text)
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if not match:
        print("Failed to extract JSON for file assignment.")
        return None
    return json.loads(match.group(0))

def merge_structures(base, new):
    """Merge updated structure into the main one safely."""
    for cat, content in new.items():
        if cat not in base:
            base[cat] = content
            continue

        # Case 1: Both are dicts
        if isinstance(base[cat], dict) and isinstance(content, dict):
            for subcat, subfiles in content.items():
                if subcat not in base[cat]:
                    base[cat][subcat] = subfiles
                else:
                    if isinstance(base[cat][subcat], list) and isinstance(subfiles, list):
                        base[cat][subcat].extend(subfiles)
                    elif isinstance(base[cat][subcat], dict) and isinstance(subfiles, dict):
                        base[cat][subcat].update(subfiles)
                    else:
                        # Convert everything to list if mixed types
                        base[cat][subcat] = list(base[cat][subcat]) + list(subfiles)

        # Case 2: Both are lists
        elif isinstance(base[cat], list) and isinstance(content, list):
            base[cat].extend(content)

        # Case 3: Mixed types (convert to list)
        else:
            if not isinstance(base[cat], list):
                base[cat] = [base[cat]]
            if isinstance(content, list):
                base[cat].extend(content)
            else:
                base[cat].append(content)
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
                if isinstance(file, (str, bytes)):
                    src = os.path.join(folder_path, file)
                    dst = os.path.join(target_path, file)
                    if os.path.exists(src) and os.path.isfile(src):
                        os.rename(src, dst)
                        moves.append((dst, src))
                else:
                    print(f"⚠️ Skipping invalid file entry in {category}: {file}")

        elif isinstance(contents, dict):
            os.makedirs(target_path, exist_ok=True)
            sub_moves = move_files_according_to_structure(folder_path, contents, os.path.join(current_path, category))
            moves.extend(sub_moves)

        else:
            print(f"⚠️ Unexpected type in structure for {category}: {type(contents)}")

    return moves

# --- Main Program ---
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

    print(f"Found {len(files)} files. Generating folder structure with Gemini...")

    # Step 1: Get folder structure
    structure = generate_folder_structure_with_gemini()
    if not structure:
        print("Failed to generate folder structure. Exiting.")
        sys.exit(1)

    print("Folder structure generated. Assigning files in batches...")
    batch_size = 15
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        print(f"Assigning batch {i//batch_size + 1}/{(len(files)+batch_size-1)//batch_size} ({len(batch)} files)...")
        updated = assign_files_to_structure_with_gemini(batch, structure)
        if updated:
            structure = merge_structures(structure, updated)

    print("\nFinal Proposed Organization Structure:")
    print(json.dumps(structure, indent=2))

    # Save structure to temp file for editing
    temp_json = os.path.join(folder_path, "_organization_structure.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)

    # Let user edit structure
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

    print("\nOrganizing files...")
    moves = move_files_according_to_structure(folder_path, edited_structure)
    print(f"Organization complete. Moved {len(moves)} files.")

    # Offer undo option
    undo = input("\nWould you like to undo the organization and restore files to their original locations? (y/N): ").strip().lower()
    if undo == "y":
        for src, dst in moves:
            if os.path.exists(src):
                os.rename(src, dst)
        print("Undo complete. Files restored to their original locations.")


if __name__ == "__main__":
    main()
