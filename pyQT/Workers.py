import os
import shutil
import json
import re
from dotenv import load_dotenv 
import os
import shutil
import json
import re
  
from PyQt5.QtCore import  pyqtSignal, QObject 
 
# --- Langchain Imports ---
try:
    from langchain_ollama import OllamaLLM
    from langchain_google_genai import GoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: Langchain or Google GenAI not installed. LLM features will be disabled.")
    # Define dummy classes if needed for the code structure to run without LLM
    class GoogleGenerativeAI: pass
    class PromptTemplate: pass
    class LLMChain: pass

class AnalysisWorker(QObject):
    """Worker for running folder analysis in a separate thread."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, dict, dict, str) # success, analysis_result, generated_structure, summary
    error = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        try:
            # --- Analysis Logic (Adapted from original) ---
            if not self.controller.folder_path or not os.path.isdir(self.controller.folder_path):
                self.error.emit("Invalid folder path selected.")
                self.finished.emit(False, {}, {}, "")
                return

            norm_path = os.path.normpath(self.controller.folder_path)

            def update_status(message):
                self.progress.emit(message)
                print(message) # Also print to console

            update_status("Scanning folder contents...")

            try:
                files_and_folders = os.listdir(self.controller.folder_path)
                if not files_and_folders:
                    self.error.emit("The selected folder is empty.")
                    self.finished.emit(False, {}, {}, "") # Treat empty as not successful for proceeding
                    return
            except Exception as e:
                self.error.emit(f"Could not list files in folder:\n{e}")
                self.finished.emit(False, {}, {}, "")
                return

            analysis_result = {}
            generated_structure = {}

            # Only use extension-based analysis and LLM if enabled
            update_status("Analyzing files by type...")
            analysis_result = self.controller._analyze_by_extension()

            # Generate structure using LLM if available and enabled
            if LANGCHAIN_AVAILABLE and self.controller.use_llm_analysis:
                update_status("Generating intelligent organization structure (LLM)...")
                try:
                    api_key = os.getenv("GOOGLE_API_KEY")
                    if not api_key:
                        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

                    # Import necessary components for text splitting and JSON parsing
                    try:
                        from langchain_text_splitters import RecursiveJsonSplitter
                        from langchain_core.output_parsers import JsonOutputParser
                        from pydantic import RootModel
                        from typing import Dict, Any

                        class FileOrganization(RootModel):
                            root: Dict[str, Any]

                        parser = JsonOutputParser(pydantic_object=FileOrganization)
                        TEXT_SPLITTER_AVAILABLE = True
                    except ImportError:
                        update_status("Text splitter or JSON parser not available. Falling back to batch processing.")
                        TEXT_SPLITTER_AVAILABLE = False

                    llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
                    all_files = [item for item in os.listdir(self.controller.folder_path)
                                 if os.path.isfile(os.path.join(self.controller.folder_path, item))]

                    temp_generated_structure = {}

                    if TEXT_SPLITTER_AVAILABLE:
                        update_status("Using text splitter for efficient processing...")
                        text_splitter = RecursiveJsonSplitter(max_chunk_size=4000)
                        files_dict = {"files": all_files}
                        chunks = text_splitter.split_json(files_dict, convert_lists=True)
                        update_status(f"Processing {len(all_files)} files in {len(chunks)} chunks...")
                        prompt_template_str = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        {format_instructions}
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:

                        {{
                          "Topic_1": {{
                            "Subtopic_1": [ "file1.txt", "file2.pdf" ],
                            "Subtopic_2": [ "imageA.jpg" ]
                          }},
                          "Topic_2": [ "archive.zip", "installer.exe" ]
                        }}

                        Here is the list of files to organize:
                        {files_chunk}
                        """
                        prompt = PromptTemplate(
                            template=prompt_template_str,
                            input_variables=["files_chunk"],
                            partial_variables={"format_instructions": parser.get_format_instructions()}
                        )
                        for i, chunk in enumerate(chunks):
                            percentage_done = int((i+1)/len(chunks)*100)
                            update_status(f"Processing files ({percentage_done}% complete)...")
                            chain = prompt | llm | parser
                            try:
                                result = chain.invoke({"files_chunk": json.dumps(chunk, indent=2)})
                                if not temp_generated_structure:
                                    temp_generated_structure = result.root if hasattr(result, 'root') else result
                                else:
                                    result_struct = result.root if hasattr(result, 'root') else result
                                    for topic, content in result_struct.items():
                                        if topic in temp_generated_structure:
                                            if isinstance(content, dict) and isinstance(temp_generated_structure[topic], dict):
                                                for subtopic, files in content.items():
                                                    if subtopic in temp_generated_structure[topic]:
                                                        if isinstance(files, list) and isinstance(temp_generated_structure[topic][subtopic], list):
                                                            temp_generated_structure[topic][subtopic].extend(files)
                                                        elif isinstance(files, dict) and isinstance(temp_generated_structure[topic][subtopic], dict):
                                                            temp_generated_structure[topic][subtopic].update(files)
                                                        else:
                                                            print(f"Warning: Mixed types in subtopic {subtopic}")
                                                    else:
                                                        temp_generated_structure[topic][subtopic] = files
                                            elif isinstance(content, list) and isinstance(temp_generated_structure[topic], list):
                                                temp_generated_structure[topic].extend(content)
                                            else:
                                                print(f"Warning: Mixed types in topic {topic}")
                                        else:
                                            temp_generated_structure[topic] = content
                                print(f"Successfully processed chunk {i+1}")
                            except Exception as e:
                                print(f"Error processing chunk {i+1}: {e}")
                    else:
                        batch_size = int(len(all_files)/2)
                        batch_size = min(max(batch_size,200),500)
                        batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
                        update_status(f"Processing {len(all_files)} files in {len(batches)} batches...")
                        prompt_template_str = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into folders and subfolders, intelligently and intuitively based.
                        The output MUST be ONLY a valid JSON object, starting with {{ and ending with }}. Do not include any explanations, markdown formatting (like ```json), or other text outside the JSON structure.
                        Group similar files together. Use descriptive names for topics and subtopics. The structure should resemble this example:

                        {{
                          "Topic_1": {{
                            "Subtopic_1": [ "file1.txt", "file2.pdf" ],
                            "Subtopic_2": [ "imageA.jpg" ]
                          }},
                          "Topic_2": [ "archive.zip", "installer.exe" ]
                        }}

                        Here is the list of files for this batch:
                        {files_batch}
                        """
                        prompt = PromptTemplate.from_template(prompt_template_str)
                        chain = prompt | llm
                        for batch_index, files_batch in enumerate(batches):
                            update_status(f"Processing batch {batch_index+1}/{len(batches)}...")
                            files_batch_str = "\n".join(files_batch)
                            response = chain.invoke({"files_batch": files_batch_str})
                            llm_output = response
                            if "```json" in llm_output:
                                llm_output = llm_output.split("```json")[1].split("```")[0].strip()
                            elif "```" in llm_output:
                                 llm_output = llm_output.split("```")[1].split("```")[0].strip()
                            else:
                                llm_output = llm_output.strip()
                            if not llm_output.startswith('{') or not llm_output.endswith('}'):
                                print(f"Warning: LLM output for batch {batch_index+1} doesn't look like JSON: {llm_output[:100]}...")
                                match = re.search(r'\{.*\}', llm_output, re.DOTALL)
                                if match:
                                    llm_output = match.group(0)
                                else:
                                    print(f"Failed to extract JSON from batch {batch_index+1}, skipping.")
                                    continue
                            batch_structure = self.controller._parse_json_safely(llm_output)
                            if batch_structure:
                                self.controller._merge_structures(temp_generated_structure, batch_structure)
                                print(f"Successfully processed batch {batch_index+1}")
                            else:
                                print(f"Failed to parse JSON for batch {batch_index+1}, skipping")
                    if not temp_generated_structure:
                        update_status("LLM analysis did not produce a valid structure. Using extension-based analysis only.")
                    else:
                        generated_structure = temp_generated_structure
                        update_status(f"Successfully generated organization structure with {len(generated_structure)} categories.")
                except Exception as e:
                    self.error.emit(f"Error during LLM analysis: {e}")
                    print(f"LLM Error: {e}")
                    generated_structure = {}
            else:
                if not LANGCHAIN_AVAILABLE:
                    update_status("Langchain not available. Skipping LLM analysis.")
                else:
                     update_status("LLM analysis disabled. Using extension-based analysis only.")


            # --- Final Summary ---
            # Use generated structure if available, otherwise analysis_result for counts
            summary_source = generated_structure if generated_structure else analysis_result
            files_count = 0
            cats_count = 0
            if summary_source:
                 # Need a way to count files in the potentially nested generated_structure
                 def count_files_recursive(struct):
                     count = 0
                     if isinstance(struct, dict):
                         for key, value in struct.items():
                             count += count_files_recursive(value)
                     elif isinstance(struct, list):
                          count += len(struct) # Assume list contains filenames
                     elif isinstance(struct, str): # Handle case where value is a single file string
                          count += 1
                     return count

                 files_count = count_files_recursive(summary_source)
                 cats_count = len(summary_source) # Top-level categories

            summary = f"Found {files_count} file(s) across {cats_count} categories."
            if generated_structure:
                summary += " (AI Structure Generated)"
            elif analysis_result:
                 summary += " (Analyzed by Extension)"
            else:
                 summary = "No files found or analysis failed."


            self.finished.emit(True, analysis_result, generated_structure, summary)

        except Exception as e:
            self.error.emit(f"An unexpected error occurred during analysis: {e}")
            self.finished.emit(False, {}, {}, "")


class OrganizeWorker(QObject):
    """Worker for running file organization in a separate thread."""
    finished = pyqtSignal(bool, str) # success, summary_message
    error = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        try:
            # --- Organization Logic (Adapted from original) ---
            if not self.controller.analysis_result and not self.controller.generated_structure:
                self.error.emit("No analysis data found to organize.")
                self.finished.emit(False, "No analysis data found.")
                return

            moved_count = 0
            error_count = 0
            error_messages = []
            target_structure = self.controller.generated_structure if self.controller.generated_structure else self.controller.analysis_result
            use_llm_structure = bool(self.controller.generated_structure)

            print(f"Organizing using {'LLM structure' if use_llm_structure else 'extension analysis'}...")

            # --- Recursive function for LLM structure ---
            def create_folders_and_move_llm(structure, current_rel_path=""):
                nonlocal moved_count, error_count, error_messages
                base_target_dir = self.controller.folder_path

                for item_name, contents in structure.items():
                    # Special handling for _files_ key - don't create a _files_ folder
                    if item_name == "_files_":
                        # Move files directly to the current folder instead of creating a _files_ subfolder
                        if isinstance(contents, list):
                            current_folder_path = os.path.join(base_target_dir, current_rel_path)
                            try:
                                # Ensure the current folder exists
                                if not os.path.exists(current_folder_path):
                                    os.makedirs(current_folder_path)
                                    print(f"Created folder: {current_folder_path}")

                                # Move each file to the current folder
                                for file_name in contents:
                                    src_path = os.path.join(base_target_dir, file_name)
                                    dst_path = os.path.join(current_folder_path, file_name)

                                    if os.path.abspath(src_path) == os.path.abspath(dst_path):
                                        print(f"Skipping {file_name}: Source and destination are the same")
                                        continue

                                    if os.path.exists(src_path) and os.path.isfile(src_path):
                                        try:
                                            print(f"Moving: {src_path} -> {dst_path}")
                                            shutil.move(src_path, dst_path)
                                            moved_count += 1
                                        except Exception as e:
                                            error_count += 1
                                            error_messages.append(f"Move Error '{file_name}' to '{current_rel_path}': {e}")
                                    else:
                                        print(f"Warning: Source file not found or is not a file: {src_path}")
                            except OSError as e:
                                error_count += 1
                                error_messages.append(f"Dir Error '{current_rel_path}': {e}")
                        continue  # Skip the rest of the processing for _files_ key

                    new_rel_path = os.path.join(current_rel_path, item_name)
                    target_path = os.path.join(base_target_dir, new_rel_path)

                    if isinstance(contents, dict):
                        # It's a subfolder definition
                        try:
                            if not os.path.exists(target_path):
                                os.makedirs(target_path)
                                print(f"Created folder: {target_path}")
                            # Recurse into the subfolder structure
                            create_folders_and_move_llm(contents, new_rel_path)
                        except OSError as e:
                            error_count += 1
                            error_messages.append(f"Dir Create Error '{new_rel_path}': {e}")
                            # Decide whether to continue into this branch or skip
                            continue # Skip this branch on directory creation error
                    elif isinstance(contents, list):
                         # It's a list of files for the current folder (item_name is the folder)
                        folder_path = os.path.join(base_target_dir, current_rel_path, item_name)
                        try:
                            if not os.path.exists(folder_path):
                                os.makedirs(folder_path)
                                print(f"Created folder: {folder_path}")

                            for file_name in contents:
                                src_path = os.path.join(base_target_dir, file_name) # Files are initially in the root
                                dst_path = os.path.join(folder_path, file_name)

                                if os.path.abspath(src_path) == os.path.abspath(dst_path):
                                    print(f"Skipping {file_name}: Source and destination are the same")
                                    continue

                                if os.path.exists(src_path) and os.path.isfile(src_path):
                                    try:
                                        print(f"Moving: {src_path} -> {dst_path}")
                                        shutil.move(src_path, dst_path)
                                        moved_count += 1
                                    except Exception as e:
                                        error_count += 1
                                        error_messages.append(f"Move Error '{file_name}' to '{new_rel_path}': {e}")
                                else:
                                     print(f"Warning: Source file not found or is not a file: {src_path}")
                                     # Optionally count as an error or just log
                                     # error_count += 1
                                     # error_messages.append(f"Source Not Found '{file_name}'")

                        except OSError as e:
                            error_count += 1
                            error_messages.append(f"Dir Error '{item_name}': {e}")
                            continue # Skip this category if folder creation fails
                    elif isinstance(contents, str): # Handle case where value is a single file string
                        # Assume the item_name is the folder, contents is the file
                        folder_path = os.path.join(base_target_dir, current_rel_path, item_name)
                        file_name = contents
                        try:
                            if not os.path.exists(folder_path):
                                os.makedirs(folder_path)
                                print(f"Created folder: {folder_path}")

                            src_path = os.path.join(base_target_dir, file_name) # Files are initially in the root
                            dst_path = os.path.join(folder_path, file_name)

                            if os.path.abspath(src_path) == os.path.abspath(dst_path):
                                print(f"Skipping {file_name}: Source and destination are the same")
                                continue

                            if os.path.exists(src_path) and os.path.isfile(src_path):
                                try:
                                    print(f"Moving: {src_path} -> {dst_path}")
                                    shutil.move(src_path, dst_path)
                                    moved_count += 1
                                except Exception as e:
                                    error_count += 1
                                    error_messages.append(f"Move Error '{file_name}' to '{new_rel_path}': {e}")
                            else:
                                    print(f"Warning: Source file not found or is not a file: {src_path}")

                        except OSError as e:
                            error_count += 1
                            error_messages.append(f"Dir Error '{item_name}': {e}")
                            continue # Skip this category if folder creation fails
                    else:
                        print(f"Warning: Unexpected content type in structure for '{item_name}': {type(contents)}")


            # --- Process based on structure type ---
            if use_llm_structure:
                 create_folders_and_move_llm(target_structure)
            else:
                # --- Simple extension-based organization ---
                for category, files in target_structure.items():
                    category_path = os.path.join(self.controller.folder_path, category)
                    try:
                        os.makedirs(category_path, exist_ok=True)
                    except OSError as e:
                        error_count += 1
                        error_messages.append(f"Dir Create Error '{category}': {e}")
                        continue # Skip this category

                    for file in files:
                        src = os.path.join(self.controller.folder_path, file)
                        dst = os.path.join(category_path, file)

                        if os.path.abspath(src) == os.path.abspath(dst):
                            continue # Skip if already in place

                        if os.path.exists(src) and os.path.isfile(src):
                            try:
                                print(f"Moving: {src} -> {dst}")
                                shutil.move(src, dst)
                                moved_count += 1
                            except Exception as e:
                                error_count += 1
                                error_messages.append(f"Move Error '{file}' to '{category}': {e}")
                        else:
                             print(f"Warning: Source file not found or is not a file: {src}")
                             # Optionally count as an error
                             # error_count += 1
                             # error_messages.append(f"Source Not Found '{file}'")


            # --- Final Summary ---
            print(f"Organization finished. Moved: {moved_count}, Errors: {error_count}")
            summary = f"Moved {moved_count} files."
            if error_count > 0:
                summary += f"\n\nEncountered {error_count} error(s):\n" + "\n".join(error_messages[:10]) # Show first 10 errors
                if len(error_messages) > 10:
                     summary += f"\n...and {len(error_messages) - 10} more errors."
                self.finished.emit(True, summary) # Still emit success=True to show summary page
            elif moved_count == 0 and not error_count:
                 # Check if there were files to move initially
                 initial_files_exist = False
                 if use_llm_structure:
                     def check_files_llm(struct):
                         if isinstance(struct, dict):
                             return any(check_files_llm(v) for v in struct.values())
                         elif isinstance(struct, list):
                             return bool(struct)
                         elif isinstance(struct, str):
                             return True
                         return False
                     initial_files_exist = check_files_llm(target_structure)
                 else:
                     initial_files_exist = any(target_structure.values())

                 if initial_files_exist:
                     summary = "No files were moved. Check permissions or if files already match the target structure."
                     self.error.emit("No files were moved. Check permissions or if files already match the target structure.")
                     self.finished.emit(False, summary) # Emit False as nothing happened
                 else:
                     summary = "No files found in the analysis to organize."
                     self.finished.emit(True, summary) # Emit True as the process completed without error on an empty set

            else: # moved_count > 0 and error_count == 0
                self.finished.emit(True, summary)

        except Exception as e:
            self.error.emit(f"An unexpected error occurred during organization: {e}")
            self.finished.emit(False, "An unexpected error occurred.")
