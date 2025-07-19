import os
import shutil
import json
import re
from dotenv import load_dotenv 
import os
import shutil
import json
import sys
import subprocess
import re
import time # For potential delays if needed
import gc

from dotenv import load_dotenv
from pathlib import Path

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QStackedWidget,
    QFrame, QCheckBox,
)
from PyQt5.QtCore import  pyqtSignal, QObject
from PyQt5.QtGui import QFont,  QIcon


# --- Theme Management ---
from pyQT.ThemeManager import ThemeManager

# --- Page Widgets ---
from pyQT.PageWidgets import (
    StartPage,AnalyzePage,EditStructurePage,
    ConfirmPage,CompletePage
)


# --- Helper Functions ---
from pyQT.Helpers import show_error_message
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


load_dotenv()

from constants.app_constants import APP_NAME
# --- PyQt5 Imports ---
 
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

from constants.app_constants import APP_NAME

load_dotenv()
 

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

            # Use backbone if available
            if norm_path in self.controller.backbone:
                update_status("Using saved organization structure (backbone.json)...")
                analysis_result = self.controller._analyze_with_backbone(norm_path)
            else:
                # Analyze by extension first
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

                            # Define the expected output structure using Pydantic
                            # Using RootModel to directly represent the structure without a wrapper
                            class FileOrganization(RootModel):
                                """File organization structure with topics and subtopics."""
                                root: Dict[str, Any]

                            # Initialize the JSON output parser
                            parser = JsonOutputParser(pydantic_object=FileOrganization)

                            TEXT_SPLITTER_AVAILABLE = True
                        except ImportError:
                            update_status("Text splitter or JSON parser not available. Falling back to batch processing.")
                            TEXT_SPLITTER_AVAILABLE = False

                        # Initialize the LLM
                        llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
                        # llm = OllamaLLM(model = "gemma3n:e2b")
                        # Get all files from the directory
                        all_files = [item for item in os.listdir(self.controller.folder_path)
                                     if os.path.isfile(os.path.join(self.controller.folder_path, item))]

                        temp_generated_structure = {}

                        if TEXT_SPLITTER_AVAILABLE:
                            # Use text splitter approach
                            update_status("Using text splitter for efficient processing...")

                            # Create a text splitter for handling large file lists
                            text_splitter = RecursiveJsonSplitter(
                                max_chunk_size=4000  # Adjust based on model's context window
                            )

                            # Convert file list to a dictionary for the splitter
                            files_dict = {"files": all_files}
                            chunks = text_splitter.split_json(files_dict, convert_lists=True)

                            update_status(f"Processing {len(all_files)} files in {len(chunks)} chunks...")

                            # Create the prompt template with format instructions from the parser
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

                            # Process each chunk and merge the results
                            for i, chunk in enumerate(chunks):
                                percentage_done = int((i+1)/len(chunks)*100)
                                update_status(f"Processing files ({percentage_done}% complete)...")

                                # Create the chain for this chunk
                                chain = prompt | llm | parser

                                # Process the chunk
                                try:
                                    result = chain.invoke({"files_chunk": json.dumps(chunk, indent=2)})

                                    # Merge the result into the overall structure
                                    if not temp_generated_structure:
                                        # Check if result is a RootModel or a dict
                                        temp_generated_structure = result.root if hasattr(result, 'root') else result
                                    else:
                                        # Get the structure from the result
                                        result_struct = result.root if hasattr(result, 'root') else result
                                        # Merge the new structure with the existing one
                                        for topic, content in result_struct.items():
                                            if topic in temp_generated_structure:
                                                # If topic already exists, merge subtopics
                                                if isinstance(content, dict) and isinstance(temp_generated_structure[topic], dict):
                                                    for subtopic, files in content.items():
                                                        if subtopic in temp_generated_structure[topic]:
                                                            # Merge files in existing subtopic
                                                            if isinstance(files, list) and isinstance(temp_generated_structure[topic][subtopic], list):
                                                                temp_generated_structure[topic][subtopic].extend(files)
                                                            elif isinstance(files, dict) and isinstance(temp_generated_structure[topic][subtopic], dict):
                                                                temp_generated_structure[topic][subtopic].update(files)
                                                            else:
                                                                # Handle mixed types
                                                                print(f"Warning: Mixed types in subtopic {subtopic}")
                                                        else:
                                                            # Add new subtopic
                                                            temp_generated_structure[topic][subtopic] = files
                                                elif isinstance(content, list) and isinstance(temp_generated_structure[topic], list):
                                                    # If both are lists, extend
                                                    temp_generated_structure[topic].extend(content)
                                                else:
                                                    # Handle mixed types
                                                    print(f"Warning: Mixed types in topic {topic}")
                                            else:
                                                # Add new topic
                                                temp_generated_structure[topic] = content

                                    print(f"Successfully processed chunk {i+1}")
                                except Exception as e:
                                    print(f"Error processing chunk {i+1}: {e}")
                                    # Continue with other chunks even if one fails

                        else:
                            # Fall back to batch processing if text splitter not available
                            batch_size = int(len(all_files)/2)
                            batch_size = min(max(batch_size,200),500) #more than 200 but less than 500
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
                                files_batch_str = "\n".join(files_batch) # Pass as a string list

                                response = chain.invoke({"files_batch": files_batch_str}) # Use invoke for newer LangChain
                                llm_output = response # Extract text response

                                # Clean up potential markdown fences
                                if "```json" in llm_output:
                                    llm_output = llm_output.split("```json")[1].split("```")[0].strip()
                                elif "```" in llm_output:
                                     llm_output = llm_output.split("```")[1].split("```")[0].strip()
                                else:
                                    # Assume the whole output is JSON if no fences
                                    llm_output = llm_output.strip()

                                if not llm_output.startswith('{') or not llm_output.endswith('}'):
                                    print(f"Warning: LLM output for batch {batch_index+1} doesn't look like JSON: {llm_output[:100]}...")
                                    # Attempt to find JSON within the output
                                    match = re.search(r'\{.*\}', llm_output, re.DOTALL)
                                    if match:
                                        llm_output = match.group(0)
                                    else:
                                        print(f"Failed to extract JSON from batch {batch_index+1}, skipping.")
                                        continue # Skip this batch if JSON extraction fails

                                batch_structure = self.controller._parse_json_safely(llm_output)

                                if batch_structure:
                                    self.controller._merge_structures(temp_generated_structure, batch_structure)
                                    print(f"Successfully processed batch {batch_index+1}")
                                else:
                                    print(f"Failed to parse JSON for batch {batch_index+1}, skipping")

                        if not temp_generated_structure:
                            update_status("LLM analysis did not produce a valid structure. Using extension-based analysis only.")
                        else:
                            generated_structure = temp_generated_structure # Assign if successful
                            update_status(f"Successfully generated organization structure with {len(generated_structure)} categories.")

                    except Exception as e:
                        self.error.emit(f"Error during LLM analysis: {e}")
                        print(f"LLM Error: {e}")
                        # Fallback: generated_structure remains empty
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


class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set default window icon
        self.setWindowIcon(QIcon("assets/logo.ico"))
        # Optionally, you can store the icons for later use
        self.icon_default = QIcon("assets/logo.ico")
        self.icon_blue = QIcon("assets/logo_blue.ico")
        self.icon_green = QIcon("assets/logo_green.ico")

        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 850, 650) # x, y, width, height
        self.setMinimumSize(700, 500)

        # --- Initialize Theme Manager ---
        self.theme_manager = ThemeManager()

        # --- Application State ---
        self.folder_path = ""
        self.analysis_result = {}
        self.generated_structure = {}
        self.current_analysis_summary = ""
        self.organization_summary = ""
        self.use_llm_analysis = LANGCHAIN_AVAILABLE # Enable LLM by default if available

        # --- Load Backbone ---
        self.backbone = self._load_backbone()

        # --- Central Widget and Layout ---
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0) # No margins for main layout
        self.setCentralWidget(self.central_widget)

        # --- Settings Bar ---
        self.create_settings_bar() # Add settings bar to main_layout

        # --- Page Container ---
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget, 1) # Give stretch factor

        # --- Create and Add Pages ---
        self.pages = {}
        for PageClass in (StartPage, AnalyzePage, EditStructurePage, ConfirmPage, CompletePage):
            page_name = PageClass.__name__
            page_widget = PageClass(controller=self)
            self.pages[page_name] = page_widget
            self.stacked_widget.addWidget(page_widget)

        # --- Apply Initial Theme ---
        self.apply_theme()

        # --- Show Initial Page ---
        self.show_page("StartPage")

    def create_settings_bar(self):
        """Adds controls for appearance and LLM toggle."""
        settings_widget = QWidget()
        settings_layout = QHBoxLayout(settings_widget)
        settings_layout.setContentsMargins(10, 5, 10, 5)

        # App title label
        app_title = QLabel(APP_NAME)
        app_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        settings_layout.addWidget(app_title)

        settings_layout.addStretch(1)  # Push remaining widgets to the right

        # LLM toggle if available
        if LANGCHAIN_AVAILABLE:
            llm_check = QCheckBox("Use AI Analysis")
            llm_check.setChecked(self.use_llm_analysis)
            llm_check.stateChanged.connect(self.toggle_llm)
            settings_layout.addWidget(llm_check)
            settings_layout.addSpacing(20)

        # Theme selector
        theme_label = QLabel("Theme:")
        theme_label.setFont(QFont("Segoe UI", 9))
        settings_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.theme_manager.current_theme.capitalize())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        settings_layout.addWidget(self.theme_combo)

        # Add settings widget to main layout
        self.main_layout.addWidget(settings_widget)

        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line)

    def toggle_llm(self, checked):
        """Toggle LLM analysis on/off"""
        self.use_llm_analysis = checked
        print(f"LLM Analysis {'Enabled' if checked else 'Disabled'}")

    def on_theme_changed(self, theme_name):
        """Handle theme change from combo box"""
        self.theme_manager.set_theme(theme_name.lower())
        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme to the application"""
        # Apply stylesheet to the application
        self.setStyleSheet(self.theme_manager.get_stylesheet())


    def _load_backbone(self):
        """Loads the backbone JSON file."""
        backbone_path = Path(__file__).parent / "backbone.json"
        try:
            if (backbone_path.exists()):
                with open(backbone_path, 'r', encoding='utf-8') as f: # Specify encoding
                    return json.load(f)
            else:
                print(f"Info: backbone.json not found at {backbone_path}. Using default analysis.")
                return {}
        except json.JSONDecodeError:
             # Use QMessageBox here
             show_error_message("Backbone Error", f"Could not parse backbone.json. Please check its format.")
             return {}
        except Exception as e:
            show_error_message("Backbone Error", f"Failed to load backbone.json: {e}")
            return {}

    def show_page(self, page_name):
        """Switches to the specified page."""
        if page_name in self.pages:
            widget_to_show = self.pages[page_name]
            self.stacked_widget.setCurrentWidget(widget_to_show)
            # Trigger update/refresh if needed
            if hasattr(widget_to_show, 'on_show'):
                widget_to_show.on_show()

            # Update window title
            page_titles = {
                "StartPage": f"{APP_NAME}",
                "AnalyzePage": f"Analysis Preview - {APP_NAME}",
                "EditStructurePage": f"Edit Structure - {APP_NAME}",
                "ConfirmPage": f"Confirm Organization - {APP_NAME}",
                "CompletePage": f"Organization Complete - {APP_NAME}"
            }
            self.setWindowTitle(page_titles.get(page_name, APP_NAME))
        else:
            print(f"Error: Page '{page_name}' not found.")

    def reset_state(self):
        """Resets application state for a new folder."""
        self.folder_path = ""
        self.analysis_result = {}
        self.generated_structure = {}
        self.current_analysis_summary = ""
        self.organization_summary = ""

        # Reset StartPage widgets
        start_page = self.pages.get("StartPage")
        if start_page:
            start_page.path_display_label.setText("No folder selected")
            # start_page.path_display_label.setStyleSheet("color: gray;")
            start_page.analyze_btn.setEnabled(False)

        # Optional: Clear other pages like AnalyzePage results?
        analyze_page = self.pages.get("AnalyzePage")
        if analyze_page:
             analyze_page.clear_layout(analyze_page.results_layout)
             analyze_page.summary_label.setText("")
             analyze_page.subtitle_label.setText("Folder: ")
        edit_page = self.pages.get("EditStructurePage")
        if edit_page:
             edit_page.structure_tree.clear()

        gc.collect() # Suggest garbage collection

    # --- Backend Logic Methods (Copied/Adapted from original) ---
    # These methods are called by the workers or pages

    def _analyze_with_backbone(self, norm_path):
        # (Keep the logic from the original, ensure it uses self.folder_path)
        result = {}
        structure = self.backbone[norm_path]
        try:
            files_in_folder = {f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))}
        except Exception as e:
            # Error should be handled by the caller (worker)
            raise RuntimeError(f"Could not list files in folder:\n{e}") from e

        processed_files = set()

        def process_level(struct, current_category_path):
            for name, content in struct.items():
                # Ensure category_key uses OS-specific separator if needed, though consistency is good
                category_key = os.path.join(current_category_path, name) if current_category_path else name

                if isinstance(content, dict):
                    # If category_key represents a folder path, ensure it exists in result
                    # This original logic seems to assume lists at leaves, let's adapt slightly
                    # result.setdefault(category_key, []) # Original might be wrong if sub-dicts exist
                    process_level(content, category_key)
                elif isinstance(content, list):
                    result.setdefault(category_key, [])
                    for file_pattern in content: # Assuming file names, not patterns here
                        if file_pattern in files_in_folder:
                            result[category_key].append(file_pattern)
                            processed_files.add(file_pattern)
                elif isinstance(content, str): # Assumed to be a single file
                     result.setdefault(category_key, []) # Store single file in a list for consistency
                     if content in files_in_folder:
                         result[category_key].append(content)
                         processed_files.add(content)

        process_level(structure, "")
        other_files = files_in_folder - processed_files
        if other_files: result.setdefault("Others", []).extend(list(other_files))
        return {k: v for k, v in result.items() if v} # Remove empty categories

    def _analyze_by_extension(self):
        """Analyze files by extension."""
        result = {}
        try:
            all_files = [item for item in os.listdir(self.folder_path)
                         if os.path.isfile(os.path.join(self.folder_path, item))]

            for item in all_files:
                ext = os.path.splitext(item)[1].lower()
                category = self._get_category(ext) if ext else 'No Extension'
                result.setdefault(category, []).append(item)
        except Exception as e:
             raise RuntimeError(f"Could not read folder contents for extension analysis:\n{e}") from e
        return result

    def _get_category(self, ext):
        # (Keep the category definitions - same as original)
        categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.heic', '.heif', '.ico'],
            'Documents': ['.pdf', '.docx', '.doc', '.txt', '.rtf', '.odt', '.wpd', '.md'],
            'Spreadsheets': ['.xlsx', '.xls', '.csv', '.ods'],
            'Presentations': ['.pptx', '.ppt', '.odp'],
            'Videos': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.json', '.xml', '.yaml', '.sh', '.bat'],
            'Executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.jar'],
            'Fonts': ['.ttf', '.otf', '.woff', '.woff2'],
            'Databases': ['.sqlite', '.db', '.sql', '.mdb', '.accdb'],
        }
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return 'Others'

    def _parse_json_safely(self, json_str):
        """Safely parse JSON, potentially fixing common issues."""
        try:
            # First try direct parsing
            return json.loads(json_str)
        except json.JSONDecodeError as json_err:
            print(f"Initial JSON parsing failed: {json_err}. Raw string (start): {json_str[:200]}")
            # Attempting basic fixes
            try:
                # Remove potential leading/trailing non-JSON chars more aggressively
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    fixed_json = json_match.group(0)
                    print("Attempting parse after extracting {...}")
                    return json.loads(fixed_json)
                else:
                    print("Could not extract a top-level JSON object.")
                    return {} # Give up if no object found
            except json.JSONDecodeError as e2:
                 print(f"JSON parsing failed even after basic extraction: {e2}")
                 return {} # Give up if basic fixes fail
            except Exception as e:
                print(f"Unexpected error during JSON fixing: {e}")
                return {}

    def _merge_structures(self, target, source):
        """Merge source structure into target structure (recursive)."""
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    self._merge_structures(target[key], value)
                elif isinstance(target[key], list) and isinstance(value, list):
                    # Combine lists, avoid duplicates if desired (simple extend here)
                    target[key].extend(v for v in value if v not in target[key])
                else:
                    # Conflict: Overwrite or handle differently? Overwriting for simplicity.
                    print(f"Warning: Merging conflict for key '{key}'. Overwriting target.")
                    target[key] = value
            else:
                target[key] = value
