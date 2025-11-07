import os
import sys
import json
import regex as re
import subprocess
import argparse
import shutil
from typing import Any, Dict, List
from dotenv import load_dotenv

from langchain.agents import initialize_agent, Tool, AgentType
from langchain.schema import SystemMessage
from langchain_google_genai.llms import GoogleGenerativeAI
from langchain.callbacks import StdOutCallbackHandler

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

class FileOrganizerAgent:
    def __init__(self, folder_path: str, user_instructions: str):
        self.folder_path = folder_path
        self.user_instructions = user_instructions
        self.llm = GoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key)
        self.current_structure = {}
        self.moves_history = []
        
    def get_files_in_folder(self, dummy_input: str = "") -> str:
        """Tool to list all files in the target folder."""
        try:
            files = [f for f in os.listdir(self.folder_path) 
                    if os.path.isfile(os.path.join(self.folder_path, f))]
            result = {
                "status": "success",
                "files": files,
                "count": len(files)
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def generate_folder_structure(self, files_json: str) -> str:
        """Tool to generate folder structure based on files and user instructions."""
        try:
            files_data = json.loads(files_json)
            files = files_data.get("files", [])
            
            prompt_text = f"""
You are an expert file organizer creating a folder structure.

User's specific instructions: {self.user_instructions}

Generate ONLY a JSON folder structure (categories + subcategories) based on these files.
Do not assign files yet, keep arrays empty for now.

Files to consider: {json.dumps(files, indent=2)}

Rules:
1. Create logical categories based on file types, topics, or patterns
2. Use nested structures where appropriate (category -> subcategory)
3. Keep all arrays empty for now
4. Return STRICT JSON only, no explanation

Example format:
{
  "Documents": {
    "Reports": [],
    "Notes": []
  },
  "Media": {
    "Images": [],
    "Videos": []
  },
  "Code": [],
  "Miscellaneous": []
}
"""
            
            response = self.llm.invoke(prompt_text)
            match = re.search(r"\{.*\}", response, re.DOTALL)
            
            if not match:
                return json.dumps({
                    "status": "error", 
                    "message": "Failed to extract JSON structure",
                    "raw_response": response
                })
            
            structure = json.loads(match.group(0))
            self.current_structure = structure
            
            return json.dumps({
                "status": "success",
                "structure": structure,
                "message": "Folder structure generated successfully"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def assign_files_to_structure(self, batch_info: str) -> str:
        """Tool to assign files to the existing folder structure."""
        try:
            batch_data = json.loads(batch_info)
            files_batch = batch_data.get("files", [])
            
            if not self.current_structure:
                return json.dumps({
                    "status": "error", 
                    "message": "No structure available. Generate structure first."
                })
            
            prompt_text = f"""
You are an expert file organizer assigning files to folders.

User's specific instructions: {self.user_instructions}

Assign the following files into the given folder structure by filling ONLY the arrays.
DO NOT create new folders or modify structure. If no suitable folder exists, place file in "Miscellaneous".

EXISTING FOLDER STRUCTURE:
{json.dumps(self.current_structure, indent=2)}

FILES TO ASSIGN:
{json.dumps(files_batch, indent=2)}

Rules:
1. Only fill the empty arrays with appropriate files
2. Don't modify folder names or create new ones
3. Analyze file names, extensions, and content patterns
4. Return the COMPLETE structure with files assigned
5. Return STRICT JSON only

Return the complete updated structure.
"""
            
            response = self.llm.invoke(prompt_text)
            match = re.search(r"\{.*\}", response, re.DOTALL)
            
            if not match:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to assign files",
                    "raw_response": response
                })
            
            updated_structure = json.loads(match.group(0))
            self.current_structure = self._merge_structures(self.current_structure, updated_structure)
            
            return json.dumps({
                "status": "success",
                "assigned_files": len(files_batch),
                "updated_structure": self.current_structure
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def preview_organization(self, dummy_input: str = "") -> str:
        """Tool to preview the current organization structure."""
        if not self.current_structure:
            return json.dumps({
                "status": "error",
                "message": "No structure available yet"
            })
        
        return json.dumps({
            "status": "success",
            "structure": self.current_structure,
            "message": "Current organization preview"
        }, indent=2)

    def save_and_edit_structure(self, dummy_input: str = "") -> str:
        """Tool to save structure to file and allow manual editing."""
        try:
            if not self.current_structure:
                return json.dumps({
                    "status": "error",
                    "message": "No structure to save"
                })
            
            temp_json = os.path.join(self.folder_path, "_organization_structure.json")
            with open(temp_json, "w", encoding="utf-8") as f:
                json.dump(self.current_structure, f, indent=2)
            
            # Open in editor
            editor = "notepad" if os.name == "nt" else "nano"
            subprocess.call([editor, temp_json])
            
            # Read back the edited structure
            with open(temp_json, "r", encoding="utf-8") as f:
                edited_structure = json.load(f)
            
            self.current_structure = edited_structure
            os.remove(temp_json)  # Clean up temp file
            
            return json.dumps({
                "status": "success",
                "message": "Structure edited and updated",
                "structure": edited_structure
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def move_files(self, dummy_input: str = "") -> str:
        """Tool to physically move files according to the current structure."""
        try:
            if not self.current_structure:
                return json.dumps({
                    "status": "error",
                    "message": "No structure available for moving files"
                })
            
            moves = self._move_files_recursive(self.current_structure)
            self.moves_history = moves
            
            return json.dumps({
                "status": "success",
                "moves_count": len(moves),
                "moves": [f"{src} -> {dst}" for dst, src in moves],
                "message": f"Successfully moved {len(moves)} files"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def undo_organization(self, dummy_input: str = "") -> str:
        """Tool to undo the file organization by moving files back."""
        try:
            if not self.moves_history:
                return json.dumps({
                    "status": "error",
                    "message": "No moves to undo"
                })
            
            undone = 0
            for dst, src in self.moves_history:
                if os.path.exists(dst):
                    os.rename(dst, src)
                    undone += 1
            
            self.moves_history = []
            
            return json.dumps({
                "status": "success",
                "undone_moves": undone,
                "message": f"Undid {undone} file moves"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _merge_structures(self, base: Dict, new: Dict) -> Dict:
        """Merge updated structure with base structure."""
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
                            # Merge lists, avoiding duplicates
                            existing_files = set(base[cat][subcat])
                            for file in subfiles:
                                if file not in existing_files:
                                    base[cat][subcat].append(file)
            elif isinstance(base[cat], list) and isinstance(content, list):
                # Merge lists, avoiding duplicates
                existing_files = set(base[cat])
                for file in content:
                    if file not in existing_files:
                        base[cat].append(file)
        return base

    def _move_files_recursive(self, structure: Dict, current_path: str = "") -> List:
        """Recursively move files according to structure."""
        moves = []
        base_path = os.path.join(self.folder_path, current_path) if current_path else self.folder_path
        
        for category, contents in structure.items():
            target_path = os.path.join(base_path, category)
            
            if isinstance(contents, list):
                os.makedirs(target_path, exist_ok=True)
                for file in contents:
                    if isinstance(file, str):
                        src = os.path.join(self.folder_path, file)
                        dst = os.path.join(target_path, file)
                        if os.path.exists(src) and src != dst:
                            shutil.move(src, dst)
                            moves.append((dst, src))
            elif isinstance(contents, dict):
                os.makedirs(target_path, exist_ok=True)
                submoves = self._move_files_recursive(
                    contents, 
                    os.path.join(current_path, category)
                )
                moves.extend(submoves)
        return moves

    def get_tools(self) -> List[Tool]:
        """Get all tools for the agent."""
        return [
            Tool(
                name="list_files",
                func=self.get_files_in_folder,
                description="Lists all files in the target folder. Input: empty string or any text."
            ),
            Tool(
                name="generate_structure",
                func=self.generate_folder_structure,
                description="Generates folder structure based on files. Input: JSON with files list from list_files."
            ),
            Tool(
                name="assign_files",
                func=self.assign_files_to_structure,
                description="Assigns files to existing structure. Input: JSON with files batch to assign."
            ),
            Tool(
                name="preview_structure",
                func=self.preview_organization,
                description="Shows current organization structure. Input: empty string or any text."
            ),
            Tool(
                name="edit_structure",
                func=self.save_and_edit_structure,
                description="Save structure to file and open editor for manual changes. Input: empty string or any text."
            ),
            Tool(
                name="move_files",
                func=self.move_files,
                description="Physically move files according to current structure. Input: empty string or any text."
            ),
            Tool(
                name="undo_moves",
                func=self.undo_organization,
                description="Undo file organization by moving files back. Input: empty string or any text."
            )
        ]

def run_file_organization_agent(folder_path: str, user_instructions: str):
    """Run the file organization agent."""
    print(f"🚀 Starting ReACT File Organization Agent")
    print(f"📂 Target folder: {folder_path}")
    print(f"📋 Instructions: {user_instructions}")
    
    # Create agent instance
    organizer = FileOrganizerAgent(folder_path, user_instructions)
    
    # Initialize LLM and agent
    llm = GoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key)
    
    system_prompt = SystemMessage(content=f"""
You are a **File Organization ReACT Agent**. Your goal is to organize files in a folder according to user instructions.

**Your workflow:**
1. First, call `list_files` to see all files in the folder
2. Call `generate_structure` with the files JSON to create folder structure
3. Process files in batches: call `assign_files` for each batch of files
4. Call `preview_structure` to show the user the proposed organization
5. Optionally call `edit_structure` to let user manually edit the structure
6. Call `move_files` to physically organize the files
7. Offer `undo_moves` if user wants to revert

**User Instructions:** {user_instructions}

**Important:**
- Always start with list_files
- Process files in batches of 10-15 for better accuracy
- Show preview before moving files
- Be thorough and explain each step
- Handle errors gracefully

**Available tools:**
- list_files: Get all files in folder
- generate_structure: Create folder structure based on files
- assign_files: Assign files to folders (use batches)
- preview_structure: Show current organization plan
- edit_structure: Allow manual editing of structure
- move_files: Execute the file organization
- undo_moves: Revert file organization

Start by listing the files to understand what we're working with.
""")

    tools = organizer.get_tools()
    
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=15,
        early_stopping_method="generate",
        handle_parsing_errors=True
    )

    try:
        result = agent.run(f"Organize the files in {folder_path} according to these instructions: {user_instructions}")
        print(f"\n✅ Agent completed successfully!")
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"\n❌ Agent encountered an error: {e}")
        
        # Fallback manual execution
        print(f"\n🔄 Attempting manual fallback execution...")
        try:
            # Manual workflow
            print("Step 1: Listing files...")
            files_result = organizer.get_files_in_folder("")
            files_data = json.loads(files_result)
            print(f"Found {files_data.get('count', 0)} files")
            
            if files_data.get('status') == 'success' and files_data.get('files'):
                print("\nStep 2: Generating structure...")
                struct_result = organizer.generate_folder_structure(files_result)
                struct_data = json.loads(struct_result)
                
                if struct_data.get('status') == 'success':
                    print("\nStep 3: Assigning files...")
                    files = files_data['files']
                    batch_size = 15
                    
                    for i in range(0, len(files), batch_size):
                        batch = files[i:i + batch_size]
                        batch_input = json.dumps({"files": batch})
                        assign_result = organizer.assign_files_to_structure(batch_input)
                        assign_data = json.loads(assign_result)
                        print(f"Processed batch {i//batch_size + 1}/{(len(files)+batch_size-1)//batch_size}")
                    
                    print("\nStep 4: Previewing organization...")
                    preview = organizer.preview_organization("")
                    preview_data = json.loads(preview)
                    print("Organization preview:")
                    print(json.dumps(preview_data.get('structure', {}), indent=2))
                    
                    # Ask user if they want to proceed
                    proceed = input("\n🤔 Proceed with file organization? (y/N): ").strip().lower()
                    if proceed == 'y':
                        print("\nStep 5: Moving files...")
                        move_result = organizer.move_files("")
                        move_data = json.loads(move_result)
                        print(f"✅ Moved {move_data.get('moves_count', 0)} files")
                        
                        # Offer undo
                        undo = input("\n↩️  Undo organization? (y/N): ").strip().lower()
                        if undo == 'y':
                            undo_result = organizer.undo_organization("")
                            undo_data = json.loads(undo_result)
                            print(f"🔄 Undid {undo_data.get('undone_moves', 0)} moves")
                    else:
                        print("📝 Organization cancelled by user")
                        
        except Exception as fallback_error:
            print(f"❌ Fallback execution also failed: {fallback_error}")

def main():
    parser = argparse.ArgumentParser(description="ReACT File Organization Agent")
    parser.add_argument("folder_path", help="Folder to organize")
    parser.add_argument("--instruction", type=str, 
                        default="Organize files intelligently by file type, topic, and purpose. Create logical folder structures.",
                        help="Custom instruction for organizing files")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.folder_path):
        print("❌ Invalid folder path.")
        sys.exit(1)
    
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables.")
        sys.exit(1)
    
    run_file_organization_agent(args.folder_path, args.instruction)

if __name__ == "__main__":
    main()