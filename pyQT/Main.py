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

        # --- Backbone loading removed ---

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


    # Backbone loading removed

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

    # Backbone analysis removed

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
