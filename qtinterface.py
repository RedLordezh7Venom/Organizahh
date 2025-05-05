import os
import shutil
import json
import sys
import platform
import subprocess
import re
import time # For potential delays if needed
import gc

from dotenv import load_dotenv
from pathlib import Path

# --- PyQt5 Imports ---
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QScrollArea, QStackedWidget,
    QFileDialog, QMessageBox, QInputDialog, QProgressDialog, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QFrame, QSpacerItem, QStyle, QStyleFactory, QSlider, QCheckBox,
    QMenu
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QDesktopServices, QColor, QPalette, QIcon

# --- Langchain Imports ---
try:
    from langchain_google_genai import GoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: Langchain or Google GenAI not installed. LLM features will be disabled.")
    # Define dummy classes if needed for the code structure to run without LLM
    class GoogleGenerativeAI: pass
    class PromptTemplate: pass
    class LLMChain: pass


load_dotenv()

APP_NAME = "Smart File Organizer"

# --- Theme Management ---
class ThemeManager:
    """Manages application themes (light/dark mode)"""

    # Light Theme Colors
    LIGHT = {
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "accent": "#2196F3",
        "accent_hover": "#1976D2",
        "border": "#e0e0e0",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "card_bg": "#ffffff",
        "disabled": "#bdbdbd",
        "highlight": "#e3f2fd"
    }

    # Dark Theme Colors
    DARK = {
        "bg_primary": "#121212",
        "bg_secondary": "#1e1e1e",
        "text_primary": "#ffffff",
        "text_secondary": "#b0b0b0",
        "accent": "#2196F3",
        "accent_hover": "#64B5F6",
        "border": "#333333",
        "success": "#81C784",
        "warning": "#FFB74D",
        "error": "#E57373",
        "card_bg": "#2d2d2d",
        "disabled": "#616161",
        "highlight": "#1e3a5f"
    }

    def __init__(self):
        self.current_theme = "light"  # Default theme
        self.colors = self.LIGHT.copy()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.colors = self.DARK.copy()
        else:
            self.current_theme = "light"
            self.colors = self.LIGHT.copy()
        return self.current_theme

    def set_theme(self, theme_name):
        """Set theme by name"""
        if theme_name.lower() == "dark":
            self.current_theme = "dark"
            self.colors = self.DARK.copy()
        else:
            self.current_theme = "light"
            self.colors = self.LIGHT.copy()
        return self.current_theme

    def get_stylesheet(self):
        """Generate QSS stylesheet based on current theme"""
        c = self.colors
        return f"""
        QWidget {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
        }}

        QMainWindow, QDialog {{
            background-color: {c['bg_primary']};
        }}

        QLabel {{
            color: {c['text_primary']};
            background-color: transparent;
        }}

        QPushButton {{
            background-color: {c['accent']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {c['accent_hover']};
        }}

        QPushButton:disabled {{
            background-color: {c['disabled']};
            color: {c['text_secondary']};
        }}

        QFrame {{
            border: 1px solid {c['border']};
            border-radius: 4px;
            background-color: {c['bg_secondary']};
        }}

        QScrollArea, QTreeWidget {{
            border: 1px solid {c['border']};
            background-color: {c['bg_secondary']};
        }}

        QTreeWidget::item {{
            padding: 4px;
        }}

        QTreeWidget::item:selected {{
            background-color: {c['highlight']};
        }}

        QComboBox {{
            border: 1px solid {c['border']};
            border-radius: 4px;
            padding: 4px;
            background-color: {c['bg_secondary']};
        }}

        QComboBox::drop-down {{
            border: none;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c['bg_secondary']};
            border: 1px solid {c['border']};
        }}

        QProgressDialog, QMessageBox {{
            background-color: {c['bg_secondary']};
        }}

        QCheckBox {{
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        """

# --- Helper Functions ---

def show_error_message(title, message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec_()

def show_warning_message(title, message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec_()

def show_info_message(title, message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec_()

def ask_yes_no(title, question):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setWindowTitle(title)
    msg.setText(question)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)
    return msg.exec_() == QMessageBox.Yes

# --- Worker Objects for Threading ---

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

                        llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key) # Corrected parameter name

                        all_files = [item for item in os.listdir(self.controller.folder_path)
                                     if os.path.isfile(os.path.join(self.controller.folder_path, item))]

                        batch_size = 200 # Keep batching
                        batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
                        update_status(f"Processing {len(all_files)} files in {len(batches)} batches...")

                        temp_generated_structure = {}

                        prompt_template_str = r"""
                        You are an expert file organizer. Given a list of filenames from a directory, generate a JSON structure proposing a logical organization into topical folders and subfolders.
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
                        chain = LLMChain(llm=llm, prompt=prompt)

                        for batch_index, files_batch in enumerate(batches):
                            update_status(f"Processing batch {batch_index+1}/{len(batches)}...")
                            files_batch_str = "\n".join(files_batch) # Pass as a string list

                            response = chain.invoke({"files_batch": files_batch_str}) # Use invoke for newer LangChain
                            llm_output = response.get('text', '') # Extract text response

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


# --- Page Widgets ---

class BasePage(QWidget):
    """Base class for pages."""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setup_fonts()
        self.setup_ui()

    def setup_fonts(self):
        """Define standard fonts for the application."""
        base_family = "Segoe UI" if platform.system() == "Windows" else "Sans-Serif" # More generic fallback
        self.FONT_TITLE = QFont(base_family, 20, QFont.Bold)
        self.FONT_SUBTITLE = QFont(base_family, 14)
        self.FONT_BODY = QFont(base_family, 10)
        self.FONT_BODY_BOLD = QFont(base_family, 10, QFont.Bold)
        self.FONT_BUTTON = QFont(base_family, 10, QFont.Bold)
        self.FONT_LABEL = QFont(base_family, 9)
        self.FONT_SMALL = QFont(base_family, 8)
        self.FONT_ICON_LARGE = QFont(base_family, 40) # For emoji icons

    def setup_ui(self):
        """Placeholder for UI setup in subclasses."""
        pass

    def on_show(self):
        """Called when the page is shown. Subclasses can override."""
        pass

class StartPage(BasePage):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter) # Center content vertically

        # --- Header ---
        title = QLabel(APP_NAME)
        title.setFont(self.FONT_TITLE)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Clean up your folders effortlessly")
        subtitle.setFont(self.FONT_SUBTITLE)
        subtitle.setAlignment(Qt.AlignCenter)
        # Add some styling for subtitle color if desired via QSS
        # subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Folder Selection Card ---
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel) # Give it a panel look
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; }") # Example QSS
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card.setMaximumWidth(600) # Limit card width

        # --- Folder Selection Row ---
        folder_select_layout = QHBoxLayout()
        folder_label = QLabel("Select Folder:")
        folder_label.setFont(self.FONT_BODY_BOLD)
        browse_button = QPushButton("Browse...")
        browse_button.setFont(self.FONT_BUTTON)
        browse_button.setFixedWidth(120)
        browse_button.clicked.connect(self.browse_folder)

        folder_select_layout.addWidget(folder_label)
        folder_select_layout.addWidget(browse_button)
        folder_select_layout.addStretch()
        card_layout.addLayout(folder_select_layout)

        # --- Path Display ---
        self.path_display_label = QLabel("No folder selected")
        self.path_display_label.setFont(self.FONT_LABEL)
        self.path_display_label.setWordWrap(True)
        # self.path_display_label.setStyleSheet("color: gray;")
        card_layout.addWidget(self.path_display_label)

        # --- Analyze Button ---
        self.analyze_btn = QPushButton("Analyze Folder")
        self.analyze_btn.setFont(self.FONT_BUTTON)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setFixedHeight(40)
        self.analyze_btn.clicked.connect(self.go_to_analysis)
        # self.analyze_btn.setStyleSheet("padding: 5px;") # Add padding
        card_layout.addWidget(self.analyze_btn, alignment=Qt.AlignCenter)

        layout.addWidget(card, alignment=Qt.AlignCenter) # Center the card horizontally
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(layout)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.controller.folder_path = path
            max_len = 60
            display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
            self.path_display_label.setText(f"Selected: {display_path}")
            # self.path_display_label.setStyleSheet("color: black;") # Reset color
            self.analyze_btn.setEnabled(True)
        # else: No change if cancelled

    def go_to_analysis(self):
        if not self.controller.folder_path:
            show_warning_message("No Folder", "Please select a folder first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")

        # Setup Progress Dialog
        self.progress_dialog = QProgressDialog("Analyzing folder...", "Cancel", 0, 0, self) # Indeterminate
        self.progress_dialog.setWindowTitle("Analysis in Progress")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False) # We'll close it manually
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

        # Setup Worker Thread
        self.analysis_thread = QThread()
        self.analysis_worker = AnalysisWorker(self.controller)
        self.analysis_worker.moveToThread(self.analysis_thread)

        # Connect signals
        self.analysis_worker.progress.connect(self.update_progress_status)
        self.analysis_worker.finished.connect(self.analysis_complete)
        self.analysis_worker.error.connect(self.analysis_error)
        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater) # Clean up thread
        self.progress_dialog.canceled.connect(self.cancel_analysis) # Allow cancellation

        # Start the thread
        self.analysis_thread.start()

    def update_progress_status(self, message):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents() # Keep dialog responsive

    def analysis_complete(self, success, analysis_result, generated_structure, summary):
        self.progress_dialog.close()
        self.analysis_thread.quit()
        self.analysis_thread.wait()

        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path)) # Re-enable if path still valid

        if success:
            self.controller.analysis_result = analysis_result
            self.controller.generated_structure = generated_structure
            self.controller.current_analysis_summary = summary

            if not analysis_result and not generated_structure:
                 show_info_message("Analysis Complete", "The folder is empty or no relevant files were found.")
            else:
                # Populate AnalyzePage *before* showing
                analyze_page = self.controller.pages["AnalyzePage"]
                analyze_page.populate_analysis()
                self.controller.show_page("AnalyzePage")
        # Error messages handled by analysis_error or specific checks in worker

    def analysis_error(self, error_message):
         # This catches errors emitted by the worker specifically
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.close()
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.quit()
            self.analysis_thread.wait()

        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path))
        show_error_message("Analysis Error", error_message)


    def cancel_analysis(self):
        print("Analysis cancelled by user.")
        if self.analysis_thread and self.analysis_thread.isRunning():
            # Note: Forcefully terminating threads is generally discouraged.
            # A better approach would involve the worker checking a flag.
            # For simplicity here, we just quit the thread. The worker might finish.
            self.analysis_thread.quit()
            self.analysis_thread.wait()
        if self.progress_dialog:
             self.progress_dialog.close()
        self.analyze_btn.setText("Analyze Folder")
        self.analyze_btn.setEnabled(bool(self.controller.folder_path))


class AnalyzePage(BasePage):
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("Analysis Preview")
        title.setFont(self.FONT_TITLE)
        self.subtitle_label = QLabel("Folder: ")
        self.subtitle_label.setFont(self.FONT_LABEL)
        # self.subtitle_label.setStyleSheet("color: gray;")

        header_layout.addWidget(title)
        header_layout.addWidget(self.subtitle_label)
        main_layout.addLayout(header_layout)

        # --- Results Area ---
        self.results_scroll_area = QScrollArea()
        self.results_scroll_area.setWidgetResizable(True)
        self.results_scroll_area.setFrameShape(QFrame.StyledPanel)
        self.results_widget = QWidget() # Content widget for scroll area
        self.results_layout = QVBoxLayout(self.results_widget) # Layout for content
        self.results_layout.setAlignment(Qt.AlignTop) # Add items to the top
        self.results_scroll_area.setWidget(self.results_widget)
        main_layout.addWidget(self.results_scroll_area, 1) # Give scroll area stretch factor

        # --- Summary Label ---
        self.summary_label = QLabel("Analyzing...")
        self.summary_label.setFont(self.FONT_LABEL)
        # self.summary_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.summary_label)

        # --- Button Bar ---
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFont(self.FONT_BUTTON)
        back_btn.setFixedWidth(120)
        back_btn.clicked.connect(lambda: self.controller.show_page("StartPage"))

        self.edit_btn = QPushButton("Edit Structure")
        self.edit_btn.setFont(self.FONT_BUTTON)
        self.edit_btn.setFixedWidth(160)
        self.edit_btn.setFixedHeight(40)
        self.edit_btn.clicked.connect(self.edit_structure)

        self.continue_btn = QPushButton("Continue to Organize")
        self.continue_btn.setFont(self.FONT_BUTTON)
        self.continue_btn.setFixedWidth(180)
        self.continue_btn.setFixedHeight(40)
        self.continue_btn.clicked.connect(self.organize_now)

        self.organize_btn = QPushButton("Organize Now →")
        self.organize_btn.setFont(self.FONT_BUTTON)
        self.organize_btn.setFixedWidth(160)
        self.organize_btn.setFixedHeight(40)
        self.organize_btn.clicked.connect(self.organize_now)

        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.continue_btn)
        btn_layout.addWidget(self.organize_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def clear_layout(self, layout):
        """Removes all widgets from a layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self.clear_layout(sub_layout)

    def populate_analysis(self):
        """Populate the scrollable area with analysis results."""
        # Clear previous results
        self.clear_layout(self.results_layout)

        # Update path subtitle
        path = self.controller.folder_path
        max_len = 70
        display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
        self.subtitle_label.setText(f"Folder: {display_path}")

        # Check if results exist
        has_results = bool(self.controller.analysis_result or self.controller.generated_structure)

        if not has_results:
            no_files_label = QLabel("No files found or analysis failed.")
            no_files_label.setFont(self.FONT_BODY)
            # no_files_label.setStyleSheet("color: gray;")
            self.results_layout.addWidget(no_files_label, alignment=Qt.AlignCenter)
            self.summary_label.setText("No files to organize.")
            self.edit_btn.setEnabled(False)
            self.continue_btn.setEnabled(False)
            self.organize_btn.setEnabled(False)
            return

        # Enable buttons
        self.edit_btn.setEnabled(True)
        self.continue_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)

        # --- Display Generated Structure (if available) ---
        if self.controller.generated_structure:
            structure_label = QLabel("AI-Generated Organization Structure")
            structure_label.setFont(self.FONT_SUBTITLE)
            self.results_layout.addWidget(structure_label)

            def display_structure_recursive(layout, structure, level=0):
                indent = "    " * level
                for item, content in sorted(structure.items()):
                    is_folder = isinstance(content, dict)
                    prefix = "📁 " if is_folder else "📄 "

                    item_label_text = f"{indent}{prefix}{item}"
                    item_label = QLabel(item_label_text)
                    item_label.setFont(self.FONT_BODY)
                    layout.addWidget(item_label)

                    if isinstance(content, dict):
                        display_structure_recursive(layout, content, level + 1)
                    elif isinstance(content, list): # List of files
                         for file_item in sorted(content):
                              file_label = QLabel(f"{indent}    📄 {file_item}")
                              file_label.setFont(self.FONT_BODY)
                              layout.addWidget(file_label)
                    elif isinstance(content, str): # Single file
                         file_label = QLabel(f"{indent}    📄 {content}")
                         file_label.setFont(self.FONT_BODY)
                         layout.addWidget(file_label)


            display_structure_recursive(self.results_layout, self.controller.generated_structure)

            # Add a separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self.results_layout.addWidget(separator)

            current_label = QLabel("Current Files by Type (For Reference)")
            current_label.setFont(self.FONT_SUBTITLE)
            self.results_layout.addWidget(current_label)

        # --- Display Analysis by Extension (Always show for reference or if no LLM) ---
        if self.controller.analysis_result:
            sorted_categories = sorted(self.controller.analysis_result.keys())
            for category in sorted_categories:
                files = self.controller.analysis_result[category]
                if not files: continue

                cat_label = QLabel(f"{category} ({len(files)})")
                cat_label.setFont(self.FONT_BODY_BOLD)
                self.results_layout.addWidget(cat_label)

                for file in sorted(files):
                    file_label = QLabel(f"    {file}") # Indent files
                    file_label.setFont(self.FONT_BODY)
                    self.results_layout.addWidget(file_label)
                self.results_layout.addSpacing(5) # Add space between categories
        elif not self.controller.generated_structure:
             # Only show this if there's no generated structure AND no analysis result (should be caught earlier)
             no_files_label = QLabel("No analysis results available.")
             no_files_label.setFont(self.FONT_BODY)
             self.results_layout.addWidget(no_files_label)


        # Update summary text
        self.summary_label.setText(self.controller.current_analysis_summary)
        self.results_widget.adjustSize() # Adjust content widget size

    def edit_structure(self):
        if not (self.controller.analysis_result or self.controller.generated_structure):
            show_warning_message("Nothing to Organize", "The analysis did not find any files to organize.")
            return
        # Prepare EditStructurePage before showing
        edit_page = self.controller.pages["EditStructurePage"]
        edit_page.load_structure()
        self.controller.show_page("EditStructurePage")

    def organize_now(self):
        if not (self.controller.analysis_result or self.controller.generated_structure):
            show_warning_message("Nothing to Organize", "The analysis did not find any files to organize.")
            return
        # Go directly to confirmation
        self.controller.show_page("ConfirmPage")


class EditStructurePage(BasePage):
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("Edit Organization Structure")
        title.setFont(self.FONT_TITLE)
        subtitle = QLabel("Customize the structure using the tree view below.")
        subtitle.setFont(self.FONT_LABEL)
        # subtitle.setStyleSheet("color: gray;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # --- Main Content Area (Tree View Only) ---
        # Using QTreeWidget simplifies editing significantly
        content_layout = QVBoxLayout()

        # Header for Tree
        tree_header_layout = QHBoxLayout()
        tree_title = QLabel("Organization Structure")
        tree_title.setFont(self.FONT_BODY_BOLD)
        add_category_btn = QPushButton("+ New Top-Level Category")
        add_category_btn.setFont(self.FONT_SMALL)
        add_category_btn.setFixedHeight(25)
        add_category_btn.clicked.connect(self._add_new_category)

        tree_header_layout.addWidget(tree_title)
        tree_header_layout.addStretch()
        tree_header_layout.addWidget(add_category_btn)
        content_layout.addLayout(tree_header_layout)

        # Add drag and drop hint
        drag_hint = QLabel("Tip: Drag and drop files between folders to reorganize")
        drag_hint.setFont(self.FONT_SMALL)
        content_layout.addWidget(drag_hint)

        # Status message for operations
        self.status_label = QLabel("")
        self.status_label.setFont(self.FONT_SMALL)
        content_layout.addWidget(self.status_label)

        # Tree Widget
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabels(["Category / File"])
        self.structure_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.structure_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.structure_tree.itemChanged.connect(self.handle_item_rename) # Handle renaming via editing

        # Enable drag and drop
        self.structure_tree.setDragEnabled(True)
        self.structure_tree.setAcceptDrops(True)
        self.structure_tree.setDropIndicatorShown(True)
        self.structure_tree.setDragDropMode(QTreeWidget.InternalMove)  # Allow moving items within the tree
        self.structure_tree.setSelectionMode(QTreeWidget.ExtendedSelection)  # Allow selecting multiple items

        # Connect drag and drop signal
        self.structure_tree.model().rowsInserted.connect(self.handle_item_moved)

        content_layout.addWidget(self.structure_tree)

        main_layout.addLayout(content_layout, 1) # Tree gets stretch factor

        # --- Button Bar ---
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFont(self.FONT_BUTTON)
        back_btn.setFixedWidth(120)
        back_btn.clicked.connect(lambda: self.controller.show_page("AnalyzePage"))

        self.confirm_btn = QPushButton("Continue to Organize →")
        self.confirm_btn.setFont(self.FONT_BUTTON)
        self.confirm_btn.setFixedHeight(40)
        self.confirm_btn.clicked.connect(self.confirm)

        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.confirm_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # Flag to prevent recursive renaming signal
        self._is_renaming = False


    def load_structure(self):
        """Load the structure into the QTreeWidget."""
        self.structure_tree.clear()
        source_structure = self.controller.generated_structure if self.controller.generated_structure else self.controller.analysis_result
        use_llm_structure = bool(self.controller.generated_structure)

        if not source_structure:
             # Should not happen if called correctly, but handle defensively
             self.structure_tree.addTopLevelItem(QTreeWidgetItem(["No structure to display"]))
             return

        def add_items_recursive(parent_item, structure):
            if isinstance(structure, dict):
                for key, value in sorted(structure.items()):
                    # Create folder item
                    folder_item = QTreeWidgetItem([key])
                    folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": key}) # Store type and name
                    # Allow renaming, dragging, and dropping
                    folder_item.setFlags(folder_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                    folder_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon)) # Use folder icon
                    parent_item.addChild(folder_item)
                    # Recursively add children
                    add_items_recursive(folder_item, value)
            elif isinstance(structure, list):
                 # Add files under the current parent folder
                 for filename in sorted(structure):
                      file_item = QTreeWidgetItem([filename])
                      file_item.setData(0, Qt.UserRole, {"type": "file", "name": filename}) # Store type and name
                      # Enable dragging but disable editing for files
                      file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                      file_item.setIcon(0, self.style().standardIcon(getattr(QStyle, "SP_FileIcon", QStyle.SP_CustomBase)))
                      parent_item.addChild(file_item)
            elif isinstance(structure, str): # Handle single file string as value
                 file_item = QTreeWidgetItem([structure])
                 file_item.setData(0, Qt.UserRole, {"type": "file", "name": structure})
                 # Enable dragging but disable editing for files
                 file_item.setFlags(file_item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                 file_item.setIcon(0, self.style().standardIcon(getattr(QStyle, "SP_FileIcon", QStyle.SP_CustomBase)))
                 parent_item.addChild(file_item)


        # If using analysis_result (flat structure), create top-level items for categories
        if not use_llm_structure:
             for category, files in sorted(source_structure.items()):
                  category_item = QTreeWidgetItem([category])
                  category_item.setData(0, Qt.UserRole, {"type": "folder", "path": category})
                  # Allow renaming, dragging, and dropping
                  category_item.setFlags(category_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                  category_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                  self.structure_tree.addTopLevelItem(category_item)
                  add_items_recursive(category_item, files) # Add files under category
        else:
             # If using LLM structure, add items starting from the root
             add_items_recursive(self.structure_tree.invisibleRootItem(), source_structure)

        self.structure_tree.expandAll() # Expand tree initially

    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.structure_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        item_data = item.data(0, Qt.UserRole)
        item_type = item_data.get("type") if item_data else None

        if item_type == "folder":
            rename_action = menu.addAction("Rename Category")
            rename_action.triggered.connect(lambda: self.rename_item(item))
            delete_action = menu.addAction("Delete Category")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            add_subfolder_action = menu.addAction("Add Subfolder")
            add_subfolder_action.triggered.connect(lambda: self.add_subfolder(item))
        # Add actions for files if needed (e.g., move to different category)

        menu.exec_(self.structure_tree.viewport().mapToGlobal(position))

    def rename_item(self, item):
        """Initiate renaming of the selected item."""
        self.structure_tree.editItem(item, 0) # Start editing the item text

    def handle_item_rename(self, item, column):
        """Handle the actual renaming after editing is finished."""
        if self._is_renaming: # Prevent recursion from setData
             return
        if column != 0:
             return

        item_data = item.data(0, Qt.UserRole)
        if not item_data or item_data.get("type") != "folder":
             return # Only handle folder renames here

        old_name = item_data.get("path") # Get the original name/path stored
        new_name = item.text(0).strip()

        if not new_name or new_name == old_name:
            # If name is empty or unchanged, revert
            self._is_renaming = True
            item.setText(0, old_name)
            self._is_renaming = False
            return

        print(f"Attempting rename: '{old_name}' -> '{new_name}'")

        # --- Update the underlying data structure ---
        # This is complex because we need to find the item in the nested dict/list
        # and update the key or value. This is a limitation of directly mapping
        # a mutable dict to a tree view without a proper model.
        # For simplicity, we'll rebuild the structure from the tree after rename.
        # A more robust solution uses QAbstractItemModel.

        # Rebuild the internal structure from the tree (Simplified approach)
        self.update_structure_from_tree()

        # Refresh the tree to ensure consistency (might be redundant but safer)
        self.load_structure()

        show_info_message("Renamed", f"Category '{old_name}' renamed to '{new_name}'.")


    def delete_item(self, item):
        """Delete the selected category item."""
        item_data = item.data(0, Qt.UserRole)
        if not item_data or item_data.get("type") != "folder":
            return

        category_name = item.text(0) # Get current display name

        if not ask_yes_no("Confirm Delete", f"Delete category '{category_name}'?\nFiles within will be lost in this view (but not deleted from disk yet)."):
             return

        # Remove item from tree
        parent = item.parent() or self.structure_tree.invisibleRootItem()
        parent.removeChild(item)

        # Update the internal structure based on the modified tree
        self.update_structure_from_tree()

        show_info_message("Deleted", f"Category '{category_name}' removed from structure.")
        # Note: Files are not moved to "Others" in this simplified tree approach.
        # The organization step will handle files based on the *final* structure.

    def add_subfolder(self, parent_item):
         """Adds a new subfolder under the selected item."""
         item_data = parent_item.data(0, Qt.UserRole)
         if not item_data or item_data.get("type") != "folder":
             return # Can only add subfolders to folders

         new_name, ok = QInputDialog.getText(self, "Add Subfolder", f"Enter name for new subfolder under '{parent_item.text(0)}':")
         if ok and new_name.strip():
             new_name = new_name.strip()

             # Check if subfolder with this name already exists
             for i in range(parent_item.childCount()):
                 if parent_item.child(i).text(0) == new_name:
                     show_warning_message("Exists", f"A subfolder named '{new_name}' already exists here.")
                     return

             # Create new tree item
             new_folder_item = QTreeWidgetItem([new_name])
             new_folder_item.setData(0, Qt.UserRole, {"type": "folder", "path": new_name}) # Path relative to parent for now
             # Allow renaming, dragging, and dropping
             new_folder_item.setFlags(new_folder_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
             new_folder_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
             parent_item.addChild(new_folder_item)
             parent_item.setExpanded(True)

             # Update the internal structure
             self.update_structure_from_tree()
             print(f"Added subfolder: {new_name}")
         else:
             print("Subfolder addition cancelled or empty name.")


    def _add_new_category(self):
        """Add a new top-level category."""
        new_name, ok = QInputDialog.getText(self, "New Category", "Enter name for the new top-level category:")
        if ok and new_name.strip():
            new_name = new_name.strip()

            # Check if top-level category exists
            for i in range(self.structure_tree.topLevelItemCount()):
                 if self.structure_tree.topLevelItem(i).text(0) == new_name:
                      show_warning_message("Exists", f"A top-level category named '{new_name}' already exists.")
                      return

            # Add item to tree
            new_item = QTreeWidgetItem([new_name])
            new_item.setData(0, Qt.UserRole, {"type": "folder", "path": new_name})
            # Allow renaming, dragging, and dropping
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            new_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
            self.structure_tree.addTopLevelItem(new_item)

            # Update internal structure
            self.update_structure_from_tree()
            show_info_message("Added", f"Category '{new_name}' added.")
        else:
             print("Category addition cancelled or empty name.")


    def update_structure_from_tree(self):
        """Rebuilds the controller's generated_structure from the QTreeWidget."""
        # We'll build the structure directly in the temp_root_dict variable

        def build_dict_recursive(parent_dict, tree_item):
            for i in range(tree_item.childCount()):
                child_item = tree_item.child(i)
                item_data = child_item.data(0, Qt.UserRole)
                item_name = child_item.text(0)
                item_type = item_data.get("type") if item_data else "unknown"

                if item_type == "folder":
                    # Create a new dict for the folder and recurse
                    sub_dict = {}
                    parent_dict[item_name] = sub_dict
                    build_dict_recursive(sub_dict, child_item)
                elif item_type == "file":
                    # Files need to be collected in lists under their parent folder key
                    # This requires adjusting the structure slightly if mixing dicts and lists
                    # For simplicity, let's assume folders contain dicts (subfolders) or lists (files)
                    # Find the list to add to, creating if necessary
                    if not isinstance(parent_dict, list):
                         # If the parent isn't a list, we might be adding the first file
                         # Or this structure is mixed. Let's default to adding to a list
                         # associated with the parent folder's name if possible.
                         # This logic gets complex quickly without a model.
                         # --- Simplified: Assume files are added to a list ---
                         # This won't perfectly rebuild the original nested structure if it mixed types.
                         if "_files_" not in parent_dict:
                              parent_dict["_files_"] = []
                         parent_dict["_files_"].append(item_name)

                    else: # Parent is already a list (e.g., under analysis_result structure)
                         parent_dict.append(item_name)


        # Build the structure starting from the invisible root
        root = self.structure_tree.invisibleRootItem()
        temp_root_dict = {}
        build_dict_recursive(temp_root_dict, root)

        # Clean up the temporary structure (e.g., remove "_files_" keys if needed)
        # This part depends heavily on the desired final structure format.
        # Let's assume the top level keys are the main categories.
        final_structure = temp_root_dict

        # --- Refinement needed here based on desired output format ---
        # The recursive function above needs adjustment to correctly create
        # the list-based or dict-based structure expected by organize_files.
        # For now, we'll update the controller with the potentially imperfect structure.

        print("Rebuilt structure from tree (may need refinement):", final_structure)
        self.controller.generated_structure = final_structure
        # If the original was analysis_result, update that instead/as well? Needs clarification.
        # For now, always update generated_structure, assuming user edits create the desired final form.
        self.controller.analysis_result = {} # Clear analysis result if structure was edited


    def confirm(self):
        """Update structure from tree and proceed to confirmation."""
        self.update_structure_from_tree() # Save changes from tree before confirming
        if not self.controller.generated_structure and not self.controller.analysis_result:
             show_warning_message("Empty Structure", "There is no organization structure defined.")
             return
        self.controller.show_page("ConfirmPage")

    def handle_item_moved(self, *_):
        """Handle when an item is moved via drag and drop

        Parameters are required by the signal but not used in this implementation.
        We use *_ to indicate unused variable-length arguments.
        """
        # Wait a moment for the UI to update before rebuilding the structure
        QTimer.singleShot(100, self.update_structure_from_tree)

        # Update status label
        self.status_label.setText("Item moved - structure updated")

        # Clear status after a delay
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

        # Log to console
        print("Item moved via drag and drop - structure will be updated")

    def on_show(self):
        """Reload structure when page is shown."""
        self.load_structure()


class ConfirmPage(BasePage):
     def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter) # Center everything

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; max-width: 400px; }")
        card.setMaximumWidth(450) # Limit width
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- Icon and Title ---
        icon_label = QLabel("⚠️") # Emoji icon
        icon_label.setFont(self.FONT_ICON_LARGE)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("Confirm Organization")
        title.setFont(self.FONT_SUBTITLE)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # --- Warning Text ---
        warning_text = ("This will move files into new subfolders within the selected directory.\n\n"
                        "This action cannot be automatically undone.")
        warning_details = QLabel(warning_text)
        warning_details.setFont(self.FONT_BODY)
        # warning_details.setStyleSheet("color: gray;")
        warning_details.setAlignment(Qt.AlignCenter)
        warning_details.setWordWrap(True)
        card_layout.addWidget(warning_details)
        card_layout.addSpacing(25)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        cancel_btn = QPushButton("Back")
        cancel_btn.setFont(self.FONT_BUTTON)
        cancel_btn.setFixedWidth(120)
        # cancel_btn.setStyleSheet("background-color: gray; color: white;")
        cancel_btn.clicked.connect(lambda: self.controller.show_page("EditStructurePage")) # Or AnalyzePage?

        self.confirm_btn = QPushButton("Yes, Organize Now")
        self.confirm_btn.setFont(self.FONT_BUTTON)
        self.confirm_btn.setFixedWidth(160)
        self.confirm_btn.setFixedHeight(40)
        # self.confirm_btn.setStyleSheet("background-color: #FF9F0A; color: black;") # Orange-like
        self.confirm_btn.clicked.connect(self.organize)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.confirm_btn)
        card_layout.addLayout(btn_layout)

        layout.addWidget(card) # Add card to the main centered layout

        self.setLayout(layout)

     def organize(self):
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setText("Organizing...")

        # Setup Worker Thread
        self.organize_thread = QThread()
        self.organize_worker = OrganizeWorker(self.controller)
        self.organize_worker.moveToThread(self.organize_thread)

        # Connect signals
        self.organize_worker.finished.connect(self.organize_complete)
        self.organize_worker.error.connect(self.organize_error)
        self.organize_thread.started.connect(self.organize_worker.run)
        self.organize_thread.finished.connect(self.organize_thread.deleteLater)

        # Start
        self.organize_thread.start()

     def organize_complete(self, success, summary_message):
        self.organize_thread.quit()
        self.organize_thread.wait()
        self.confirm_btn.setText("Yes, Organize Now")
        self.confirm_btn.setEnabled(True)

        self.controller.organization_summary = summary_message # Store summary

        if success:
            # Update CompletePage message before showing
            complete_page = self.controller.pages["CompletePage"]
            complete_page.update_completion_message()
            self.controller.show_page("CompletePage")
        # Error messages handled by organize_error or specific checks in worker

     def organize_error(self, error_message):
        if self.organize_thread and self.organize_thread.isRunning():
            self.organize_thread.quit()
            self.organize_thread.wait()
        self.confirm_btn.setText("Yes, Organize Now")
        self.confirm_btn.setEnabled(True)
        show_error_message("Organization Error", error_message)
        # Stay on ConfirmPage after error


class CompletePage(BasePage):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        # card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 10px; max-width: 400px; }")
        card.setMaximumWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- Icon and Title ---
        icon_label = QLabel("✅") # Emoji icon
        icon_label.setFont(self.FONT_ICON_LARGE)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("Organization Complete!")
        title.setFont(self.FONT_SUBTITLE)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # --- Details Text ---
        self.details_label = QLabel("Files have been successfully organized.")
        self.details_label.setFont(self.FONT_BODY)
        # self.details_label.setStyleSheet("color: gray;")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setWordWrap(True)
        card_layout.addWidget(self.details_label)
        card_layout.addSpacing(30)

        # --- Buttons (Vertical Layout) ---
        btn_width = 220

        open_btn = QPushButton("📂 Open Folder")
        open_btn.setFont(self.FONT_BUTTON)
        open_btn.setFixedWidth(btn_width)
        open_btn.setFixedHeight(40)
        open_btn.clicked.connect(self.open_folder)
        card_layout.addWidget(open_btn, alignment=Qt.AlignCenter)

        again_btn = QPushButton("Organize Another Folder")
        again_btn.setFont(self.FONT_BUTTON)
        again_btn.setFixedWidth(btn_width)
        again_btn.setFixedHeight(40)
        again_btn.clicked.connect(self.go_to_start)
        card_layout.addWidget(again_btn, alignment=Qt.AlignCenter)

        exit_btn = QPushButton("Exit Application")
        exit_btn.setFont(self.FONT_BUTTON)
        exit_btn.setFixedWidth(btn_width)
        # exit_btn.setStyleSheet("background-color: gray; color: white;")
        exit_btn.clicked.connect(self.controller.close) # Close main window
        card_layout.addWidget(exit_btn, alignment=Qt.AlignCenter)

        layout.addWidget(card)
        self.setLayout(layout)

    def open_folder(self):
        """Open the organized folder in file explorer."""
        path = self.controller.folder_path
        if not path or not os.path.isdir(path):
            show_warning_message("Open Folder", "Cannot open folder. Path is invalid or not set.")
            return
        try:
            # Use QDesktopServices for cross-platform opening
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            show_error_message("Error", f"Could not open folder: {e}")

    def update_completion_message(self):
        """Updates the message shown on the completion screen."""
        folder_name = os.path.basename(self.controller.folder_path) if self.controller.folder_path else "Selected folder"
        summary = getattr(self.controller, 'organization_summary', "Organization process finished.") # Get summary if exists
        self.details_label.setText(f"Organized '{folder_name}'.\n\n{summary}")

    def go_to_start(self):
        """Resets state and returns to the StartPage."""
        self.controller.reset_state()
        self.controller.show_page("StartPage")

    def on_show(self):
        """Ensure the message is updated when shown."""
        self.update_completion_message()


# --- Main Application Window ---

class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()

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
            if backbone_path.exists():
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


# --- Main Execution ---
if __name__ == "__main__":
    # Dependency check (using standard tkinter is okay here before PyQt app starts)
    try:
        # Check for required packages (PIL is optional now unless used elsewhere)
        # import PIL
        if not LANGCHAIN_AVAILABLE:
             print("Note: Langchain/Google GenAI not found. LLM features disabled.")
             # Optionally show a Tkinter messagebox here if critical
             # import tkinter as tk
             # from tkinter import messagebox
             # root_err = tk.Tk(); root_err.withdraw()
             # messagebox.showwarning("Missing Dependency", "Langchain/Google GenAI not found. AI organization features will be disabled.")
             # root_err.destroy()

    except ImportError as e:
        # This part is less likely needed now as PIL is optional
        import tkinter as tk
        from tkinter import messagebox
        root_err = tk.Tk()
        root_err.withdraw()
        missing_package = str(e).split("'")[1] if "'" in str(e) else str(e)
        messagebox.showerror("Error", f"Required package {missing_package} is missing.")
        root_err.destroy()
        sys.exit(1)

    # --- Run the PyQt Application ---
    app = QApplication(sys.argv)
    # You might want to apply a style for better consistency:
    # app.setStyle("Fusion")
    main_window = FileOrganizerApp()
    main_window.show()
    sys.exit(app.exec_())