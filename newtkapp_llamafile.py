import os
import shutil
import customtkinter as ctk # Import customtkinter
from tkinter import filedialog, messagebox # Keep standard messagebox/filedialog
# from tkinter.font import Font # We'll define fonts differently
import json
from PIL import Image # Keep PIL for potential image use
import sys
import platform
import subprocess
from dotenv import load_dotenv
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()

# --- Theme Configuration (Optional: Customize CTk's themes) ---
# customtkinter themes handle most colors. Define specifics if needed.
APP_NAME = "Smart File Organizer"

class FileOrganizerApp(ctk.CTk): # Inherit from ctk.CTk
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("850x650")
        self.minsize(700, 500)

        # --- Appearance Settings (Light/Dark Mode) ---
        ctk.set_appearance_mode("System") # Default to system theme
        ctk.set_default_color_theme("blue") # Default theme color

        # --- Font Setup ---
        self.setup_fonts()

        # --- Load Backbone ---
        self.backbone = self._load_backbone()

        self.folder_path = ""
        self.analysis_result = {}
        self.generated_structure = {} # Store the LLM-generated structure
        self.current_analysis_summary = "" # Store summary for CompletePage

        # Callback for status updates during analysis
        self.update_status_callback = None

        # --- Configure Main Grid ---
        self.grid_rowconfigure(0, weight=0) # Row 0 for potential settings bar
        self.grid_rowconfigure(1, weight=1) # Row 1 for the main content pages
        self.grid_columnconfigure(0, weight=1)

        # --- Settings Bar (Optional Example) ---
        self.settings_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.settings_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.create_settings_bar() # Add theme/scaling controls

        # --- Page Container ---
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # --- Create Frames ---
        self.frames = {}
        for F in (StartPage, AnalyzePage, EditStructurePage, ConfirmPage, CompletePage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def setup_fonts(self):
        """Define standard fonts for the application."""
        base_family = "Segoe UI" if platform.system() == "Windows" else "Helvetica Neue"
        # Adjust sizes as needed for CTk's scaling
        self.FONT_TITLE = (base_family, 26, "bold")
        self.FONT_SUBTITLE = (base_family, 18)
        self.FONT_BODY = (base_family, 13)
        self.FONT_BODY_BOLD = (base_family, 13, "bold")
        self.FONT_BUTTON = (base_family, 14, "bold")
        self.FONT_LABEL = (base_family, 12)
        self.FONT_SMALL = (base_family, 10)

    def create_settings_bar(self):
        """Adds controls for appearance and scaling."""
        appearance_label = ctk.CTkLabel(self.settings_frame, text="Theme:", font=self.FONT_SMALL)
        appearance_label.pack(side="left", padx=(20, 5), pady=10)
        appearance_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["Light", "Dark", "System"],
            command=ctk.set_appearance_mode,
            width=100,
            font=self.FONT_SMALL,
            dropdown_font=self.FONT_SMALL
        )
        appearance_menu.pack(side="left", padx=5, pady=10)
        appearance_menu.set("System") # Default value

        # Add more settings like scaling if desired
        # scaling_label = ctk.CTkLabel(self.settings_frame, text="UI Scaling:", font=self.FONT_SMALL)
        # ... create scaling OptionMenu ...

    def _load_backbone(self):
        """Loads the backbone JSON file."""
        backbone_path = Path(__file__).parent / "backbone.json"
        try:
            if backbone_path.exists():
                with open(backbone_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"Info: backbone.json not found at {backbone_path}. Using default analysis.")
                return {}
        except json.JSONDecodeError:
             messagebox.showerror("Error", f"Could not parse backbone.json. Please check its format.")
             return {}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load backbone.json: {e}")
            return {}

    def show_frame(self, page_name):
        """Raises the specified frame to the top."""
        frame = self.frames[page_name]
        frame.tkraise()
        # Trigger update/refresh if needed when a frame is shown
        if hasattr(frame, 'on_show'):
            frame.on_show()

        # Update window title
        page_titles = {
            "StartPage": f"{APP_NAME}",
            "AnalyzePage": f"Analysis Preview - {APP_NAME}",
            "EditStructurePage": f"Edit Structure - {APP_NAME}",
            "ConfirmPage": f"Confirm Organization - {APP_NAME}",
            "CompletePage": f"Organization Complete - {APP_NAME}"
        }
        self.title(page_titles.get(page_name, APP_NAME))

    def rebuild_edit_structure_page(self):
        """Rebuilds only the EditStructurePage frame"""
        import gc

        print("Starting rebuild process...")
        print("Current structure:", list(self.generated_structure.keys()))
        print("Current analysis result:", list(self.analysis_result.keys()))

        # Only destroy the EditStructurePage frame
        if "EditStructurePage" in self.frames:
            self.frames["EditStructurePage"].destroy()
            del self.frames["EditStructurePage"]

        # Force update to ensure destruction is complete
        self.update_idletasks()

        # Run garbage collection to clean up lingering references
        gc.collect()

        # Create only a new EditStructurePage
        new_frame = EditStructurePage(parent=self.container, controller=self)
        self.frames["EditStructurePage"] = new_frame
        new_frame.grid(row=0, column=0, sticky="nsew")

        # Load the structure into the new frame
        new_frame.load_structure()

        # Raise the new frame to the top
        new_frame.tkraise()

        # Force update
        self.update_idletasks()

        print("Rebuild complete.")
        print("After rebuild - Structure:", list(self.generated_structure.keys()))
        print("After rebuild - Analysis:", list(self.analysis_result.keys()))

    # --- Analysis Logic (Keep mostly the same, adjust error reporting) ---

    def analyze_folder(self):
        """Analyze the selected folder structure"""
        if not self.folder_path or not os.path.isdir(self.folder_path):
             messagebox.showerror("Error", "Invalid folder path selected.")
             return False

        norm_path = os.path.normpath(self.folder_path)

        # Update status if callback is available
        def update_status(message):
            if self.update_status_callback:
                self.update_status_callback(message)
            print(message)  # Also print to console for logging

        update_status("Scanning folder contents...")

        # First, get the list of files and folders
        try:
            files_and_folders = os.listdir(self.folder_path)
            if not files_and_folders:
                messagebox.showinfo("Empty Folder", "The selected folder is empty.")
                return False
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not list files in folder:\n{e}")
            return False

        # Use backbone if available, otherwise use LLM-based structure generation
        if norm_path in self.backbone:
            update_status("Using saved organization structure...")
            self.analysis_result = self._analyze_with_backbone(norm_path)
        else:
            # First analyze by extension for display
            update_status("Analyzing files by type...")
            self.analysis_result = self._analyze_by_extension()

            # Then generate structure using LLM in batches
            update_status("Generating intelligent organization structure...")
            try:
                # Initialize Google GenAI model
                api_key = os.getenv("GOOGLE_API_KEY")
                llm = GoogleGenerativeAI(model="gemini-2.0-flash", api_key=api_key)

                # Get all files in the directory
                all_files = []
                for item in os.listdir(self.folder_path):
                    item_path = os.path.join(self.folder_path, item)
                    if os.path.isfile(item_path):
                        all_files.append(item)

                # Process files in batches of 200
                batch_size = 200
                batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
                update_status(f"Processing {len(all_files)} files in {len(batches)} batches...")

                # Initialize the final structure
                self.generated_structure = {}

                # Create prompt template for structure generation
                prompt_template = r"""
                You are given a list of files from a directory:
                {files_batch}

                Your task is to generate a JSON structure that organizes these files into topics and subtopics.
                Give the output as valid JSON only, with no other text.
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

                # Process each batch
                for batch_index, files_batch in enumerate(batches):
                    update_status(f"Processing batch {batch_index+1}/{len(batches)}...")

                    # Use LangChain to interact with Google GenAI
                    chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(prompt_template))

                    # Pass the current batch as input to the chain
                    response = chain.run({"files_batch": files_batch})

                    # Clean up the response
                    if "```json" in response:
                        response = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        response = response.split("```")[1].split("```")[0].strip()

                    # Try to parse the JSON
                    batch_structure = self._parse_json_safely(response)

                    # Merge this batch's structure with the main structure
                    if batch_structure:
                        self._merge_structures(self.generated_structure, batch_structure)
                        print(f"Successfully processed batch {batch_index+1}")
                    else:
                        print(f"Failed to process batch {batch_index+1}, skipping")

                # If we couldn't generate any structure, fall back to extension-based analysis
                if not self.generated_structure:
                    update_status("No valid structure was generated. Using extension-based analysis.")
                else:
                    update_status(f"Successfully generated organization structure with {len(self.generated_structure)} categories.")

            except Exception as e:
                messagebox.showerror("LLM Error", f"Error generating structure with LLM: {e}")
                print(f"LLM Error: {e}")
                # Continue with extension-based analysis if LLM fails
                self.generated_structure = {}

        # Store summary for later use
        files_count = sum(len(files) for files in self.analysis_result.values())
        cats_count = len(self.analysis_result)
        self.current_analysis_summary = f"Found {files_count} file(s) across {cats_count} categories."

        return True

    def _analyze_with_backbone(self, norm_path):
        # (Keep the logic from the previous version, potentially refine error handling)
        result = {}
        structure = self.backbone[norm_path]
        try:
            files_in_folder = {f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))}
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not list files in folder:\n{e}")
            return {}

        processed_files = set()

        def process_level(struct, current_category_path):
            # ... (rest of the backbone processing logic) ...
            for name, content in struct.items():
                category_key = os.path.join(current_category_path, name) if current_category_path else name

                if isinstance(content, dict):
                    if category_key not in result: result[category_key] = []
                    process_level(content, category_key)
                elif isinstance(content, list):
                    if category_key not in result: result[category_key] = []
                    for file_pattern in content:
                        if file_pattern in files_in_folder:
                            result[category_key].append(file_pattern)
                            processed_files.add(file_pattern)
                elif isinstance(content, str):
                     if category_key not in result: result[category_key] = []
                     if content in files_in_folder:
                         result[category_key].append(content)
                         processed_files.add(content)

        process_level(structure, "")
        other_files = files_in_folder - processed_files
        if other_files: result.setdefault("Others", []).extend(list(other_files))
        return {k: v for k, v in result.items() if v} # Remove empty categories

    def _analyze_by_extension(self):
        """Analyze files by extension, handling all files regardless of type"""
        result = {}
        try:
            # Get all files in the directory
            all_files = []
            for item in os.listdir(self.folder_path):
                item_path = os.path.join(self.folder_path, item)
                if os.path.isfile(item_path):
                    all_files.append(item)

            # Process all files regardless of extension
            for item in all_files:
                ext = os.path.splitext(item)[1].lower()
                category = self._get_category(ext) if ext else 'No Extension'
                result.setdefault(category, []).append(item)

        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not read folder contents:\n{e}")
            return {}
        return result

    def _parse_json_safely(self, json_str):
        """Safely parse JSON with multiple fallback strategies"""
        try:
            # First try direct parsing
            return json.loads(json_str)
        except json.JSONDecodeError as json_err:
            print(f"JSON parsing error: {json_err}")
            print(f"Attempting to fix malformed JSON...")

            try:
                # 1. Replace single quotes with double quotes
                fixed_json = json_str.replace("'", "\"")

                # 2. Try to add missing closing quotes/braces
                if fixed_json.count('{') > fixed_json.count('}'):
                    fixed_json += '}' * (fixed_json.count('{') - fixed_json.count('}'))

                # 3. Try to fix missing colons
                import re
                fixed_json = re.sub(r'\"([^\"]+)\"\s+\"', r'"\1": "', fixed_json)

                # 4. Fix trailing commas before closing braces
                fixed_json = fixed_json.replace(',}', '}').replace(',]', ']')

                # 5. Add missing quotes around keys
                fixed_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', fixed_json)

                # Try parsing the fixed JSON
                return json.loads(fixed_json)
            except Exception as e:
                print(f"First-level fixes failed: {e}")

                try:
                    # Try more aggressive approaches
                    # 1. Try to extract what looks like valid JSON
                    json_pattern = r'\{.*\}'
                    match = re.search(json_pattern, fixed_json, re.DOTALL)
                    if match:
                        potential_json = match.group(0)
                        return json.loads(potential_json)

                    # 2. If that fails, try to build a minimal valid structure
                    print("Attempting to build minimal valid structure")
                    return {}
                except Exception as final_err:
                    print(f"All JSON repair attempts failed: {final_err}")
                    return {}

    def _merge_structures(self, target, source):
        """Merge source structure into target structure"""
        if not source:
            return  # Nothing to merge

        for category, content in source.items():
            if category not in target:
                # New category, just add it
                target[category] = content
            elif isinstance(target[category], dict) and isinstance(content, dict):
                # Both are dictionaries, merge recursively
                self._merge_structures(target[category], content)
            elif isinstance(target[category], dict):
                # Target is dict but source is not, add files to appropriate subcategories
                # For simplicity, we'll add to a "Misc" subcategory
                if "Misc" not in target[category]:
                    target[category]["Misc"] = {}

                if isinstance(content, dict):
                    for file, file_type in content.items():
                        target[category]["Misc"][file] = file_type
                else:
                    # Handle unexpected content type
                    pass
            else:
                # Handle other cases (target not a dict)
                # Just overwrite with source for simplicity
                target[category] = content

    def _get_category(self, ext):
        # (Keep the category definitions)
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

    def organize_files(self):
        """Organize files according to the analysis or generated structure"""
        # Check if we have data to work with
        if not self.analysis_result and not self.generated_structure:
            messagebox.showwarning("Warning", "No analysis data found.")
            return False

        moved_count = 0
        error_count = 0
        error_messages = []

        # If we have a generated structure from LLM, use that
        if self.generated_structure:
            print("Organizing using LLM-generated structure...")

            # Create a function to recursively process the structure
            def create_folders_and_move_files(structure, current_dir):
                nonlocal moved_count, error_count, error_messages

                for item_name, contents in structure.items():
                    if isinstance(contents, dict):
                        # Create folder path
                        folder_path = os.path.join(current_dir, item_name)

                        try:
                            # Create the folder if it doesn't exist
                            if not os.path.exists(folder_path):
                                os.makedirs(folder_path)
                                print(f"Created folder: {folder_path}")

                            # Recursively process subfolders and their contents
                            create_folders_and_move_files(contents, folder_path)
                        except OSError as e:
                            error_count += 1
                            error_messages.append(f"Dir Error '{item_name}': {e}")
                            continue
                    else:
                        # Handle both string values and dictionary values with file types
                        file_name = item_name

                        # Move file to current directory
                        file_path = os.path.join(self.folder_path, file_name)
                        new_location = os.path.join(current_dir, file_name)

                        # Skip if source and destination are the same
                        if os.path.abspath(file_path) == os.path.abspath(new_location):
                            print(f"Skipping {file_name}: Source and destination are the same")
                            continue

                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            try:
                                print(f"Moving file: {file_path} to {new_location}")
                                shutil.move(file_path, new_location)
                                moved_count += 1
                            except Exception as e:
                                error_count += 1
                                error_messages.append(f"Move Error '{file_name}': {e}")
                        else:
                            print(f"File not found: {file_path}")

            # Process the structure
            print(f"Organizing files using structure with {len(self.generated_structure)} top-level categories")
            for category, contents in self.generated_structure.items():
                category_path = os.path.join(self.folder_path, category)
                try:
                    if not os.path.exists(category_path):
                        os.makedirs(category_path)
                        print(f"Created top-level category folder: {category_path}")

                    # Process this category
                    create_folders_and_move_files({category: contents}, self.folder_path)
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Error processing category '{category}': {e}")

        # Otherwise use the simple analysis result
        else:
            print("Organizing using extension-based analysis...")

            for category, files in self.analysis_result.items():
                category_path = os.path.join(self.folder_path, category)
                try:
                    os.makedirs(category_path, exist_ok=True)
                except OSError as e:
                    error_count += 1
                    error_messages.append(f"Dir Error '{category}': {e}")
                    continue

                for file in files:
                    src = os.path.join(self.folder_path, file)
                    dst = os.path.join(category_path, file)
                    if os.path.abspath(src) == os.path.abspath(dst): continue

                    if os.path.exists(src) and os.path.isfile(src):
                        try:
                            shutil.move(src, dst)
                            moved_count += 1
                        except Exception as e:
                            error_count += 1
                            error_messages.append(f"Move Error '{file}': {e}")
                    # else: skip missing/non-file source

        print(f"Organization finished. Moved: {moved_count}, Errors: {error_count}")

        # Store organization summary for completion page
        self.organization_summary = f"Moved {moved_count} files."
        if error_count > 0:
            self.organization_summary += f"\n\nErrors ({error_count}):\n" + "\n".join(error_messages[:5])
            if len(error_messages) > 5:
                self.organization_summary += f"\n...and {len(error_messages) - 5} more errors."

        # Handle errors
        if error_count > 0:
            messagebox.showerror("Organization Errors",
                                 f"{error_count} error(s) occurred. Check console/logs.\n" +
                                 f"First few errors:\n- " + "\n- ".join(error_messages[:3]))
            return True  # Still return True to show completion page with error details
        elif moved_count == 0:
             messagebox.showwarning("Organization Issue", "No files were moved. Check source folder permissions or file existence.")
             return False # Treat as non-successful if no files were moved
        return True

    def open_folder(self):
        # (Keep the open folder logic)
        path = self.controller.folder_path # Assuming called from page context
        if not path or not os.path.isdir(path):
             messagebox.showwarning("Open Folder", "Cannot open folder. Path is invalid or not set.")
             return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")


# --- Page Classes (Refactored for CustomTkinter) ---

class BasePage(ctk.CTkFrame):
    """Base class for pages to avoid repeating parent/controller."""
    def __init__(self, parent, controller):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.controller = controller
        # Define fonts using controller's definitions
        self.FONT_TITLE = controller.FONT_TITLE
        self.FONT_SUBTITLE = controller.FONT_SUBTITLE
        self.FONT_BODY = controller.FONT_BODY
        self.FONT_BODY_BOLD = controller.FONT_BODY_BOLD
        self.FONT_BUTTON = controller.FONT_BUTTON
        self.FONT_LABEL = controller.FONT_LABEL
        self.FONT_SMALL = controller.FONT_SMALL

class StartPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        # Central content frame with padding
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=40, pady=40)

        # --- Header ---
        title = ctk.CTkLabel(self.main_frame, text=APP_NAME, font=self.FONT_TITLE, text_color=("gray10", "gray90"))
        title.pack(pady=(0, 10))

        subtitle = ctk.CTkLabel(self.main_frame, text="Clean up your folders effortlessly", font=self.FONT_SUBTITLE, text_color="gray50")
        subtitle.pack(pady=(0, 40))

        # --- Folder Selection Card ---
        card = ctk.CTkFrame(self.main_frame, corner_radius=10) # Use CTkFrame as card
        card.pack(fill="x", pady=20, ipady=20) # Internal padding with ipady

        # --- Folder Selection Row ---
        folder_select_frame = ctk.CTkFrame(card, fg_color="transparent")
        folder_select_frame.pack(fill="x", padx=20, pady=(0, 15))

        folder_label = ctk.CTkLabel(folder_select_frame, text="Select Folder:", font=self.FONT_BODY_BOLD)
        folder_label.pack(side="left", padx=(0, 10))

        browse_button = ctk.CTkButton(
            folder_select_frame,
            text="Browse...",
            font=self.FONT_BUTTON,
            command=self.browse_folder,
            width=120
        )
        browse_button.pack(side="left")

        # --- Path Display ---
        self.path_var = ctk.StringVar(value="No folder selected")
        path_display_label = ctk.CTkLabel(
            card,
            textvariable=self.path_var,
            font=self.FONT_LABEL,
            text_color="gray50",
            wraplength=550, # Adjust as needed
            anchor="w",
            justify="left",
        )
        path_display_label.pack(fill="x", padx=20, pady=(0, 25))
        self.path_display_widget = path_display_label # Store reference to change color

        # --- Analyze Button ---
        self.analyze_btn = ctk.CTkButton(
            card,
            text="Analyze Folder",
            font=self.FONT_BUTTON,
            state="disabled",
            command=self.go_to_analysis,
            height=40 # Make button taller
        )
        self.analyze_btn.pack(pady=(10, 10))

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.controller.folder_path = path
            # Truncate long paths for display
            max_len = 60
            display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
            self.path_var.set(f"Selected: {display_path}")
            # Use CTk's text color tuple for light/dark modes
            self.path_display_widget.configure(text_color=("gray30", "gray70"))
            self.analyze_btn.configure(state="normal")
        else:
            # Optionally reset if selection cancelled, or keep current
            pass

    def go_to_analysis(self):
        if not self.controller.folder_path:
             messagebox.showwarning("No Folder", "Please select a folder first.")
             return

        # Create a progress dialog
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Analyzing Files")
        progress_window.geometry("400x150")
        progress_window.transient(self.controller)  # Set as transient to main window
        progress_window.grab_set()  # Make it modal

        # Center the progress window
        progress_window.update_idletasks()
        width = progress_window.winfo_width()
        height = progress_window.winfo_height()
        x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
        y = (progress_window.winfo_screenheight() // 2) - (height // 2)
        progress_window.geometry(f"{width}x{height}+{x}+{y}")

        # Add progress message
        message_label = ctk.CTkLabel(
            progress_window,
            text="Analyzing folder contents...\nThis may take a moment for large folders.",
            font=self.FONT_BODY
        )
        message_label.pack(pady=(20, 15))

        # Add progress indicator
        progress = ctk.CTkProgressBar(progress_window, mode="indeterminate", width=300)
        progress.pack(pady=10)
        progress.start()

        # Update status message function
        def update_status(message):
            message_label.configure(text=message)
            progress_window.update_idletasks()

        # Configure the controller to use our status update function
        self.controller.update_status_callback = update_status

        # Disable the analyze button
        original_text = self.analyze_btn.cget("text")
        self.analyze_btn.configure(text="Analyzing...", state="disabled")

        # Use after to allow the UI to update before starting analysis
        def run_analysis():
            try:
                analysis_ok = self.controller.analyze_folder()

                # Close progress window
                progress_window.destroy()

                # Reset button
                self.analyze_btn.configure(text=original_text, state="normal" if self.controller.folder_path else "disabled")

                if analysis_ok and self.controller.analysis_result:
                    # Populate *before* showing
                    self.controller.frames["AnalyzePage"].populate_analysis()
                    self.controller.show_frame("AnalyzePage")
                elif analysis_ok and not self.controller.analysis_result:
                    messagebox.showinfo("Empty Folder", "The selected folder is empty or has no files matching the criteria.")
                # else: error message handled in analyze_folder
            except Exception as e:
                progress_window.destroy()
                self.analyze_btn.configure(text=original_text, state="normal" if self.controller.folder_path else "disabled")
                messagebox.showerror("Analysis Error", f"An error occurred during analysis: {e}")

        # Schedule the analysis to run after the UI updates
        self.after(100, run_analysis)


class AnalyzePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))

        title = ctk.CTkLabel(header_frame, text="Analysis Preview", font=self.FONT_TITLE)
        title.pack(anchor="w")

        self.subtitle_var = ctk.StringVar()
        subtitle = ctk.CTkLabel(header_frame, textvariable=self.subtitle_var, font=self.FONT_LABEL, text_color="gray50")
        subtitle.pack(anchor="w", pady=(4, 0))

        # --- Results Area (Scrollable Frame instead of Treeview) ---
        self.results_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.results_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 15))

        # --- Summary Label ---
        self.summary_label_var = ctk.StringVar(value="Analyzing...")
        summary_label = ctk.CTkLabel(self, textvariable=self.summary_label_var, font=self.FONT_LABEL, text_color="gray50")
        summary_label.grid(row=2, column=0, sticky="w", padx=30, pady=(0, 10))

        # --- Button Bar ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", padx=30, pady=(5, 20))
        # Configure columns for button layout
        btn_frame.grid_columnconfigure(0, weight=1)  # Left button
        btn_frame.grid_columnconfigure(1, weight=0)  # Middle button
        btn_frame.grid_columnconfigure(2, weight=1)  # Right button

        # Back button (left-aligned)
        back_btn = ctk.CTkButton(
            btn_frame, text="← Back", font=self.FONT_BUTTON, width=120,
            fg_color="gray60", hover_color="gray50", # Secondary style
            command=lambda: controller.show_frame("StartPage")
        )
        back_btn.grid(row=0, column=0, sticky='w')

        # Edit Structure button (center-right)
        self.edit_btn = ctk.CTkButton(
            btn_frame, text="Edit Structure", font=self.FONT_BUTTON, width=160, height=40,
            command=self.edit_structure
        )
        self.edit_btn.grid(row=0, column=1, padx=(0, 10), sticky='e')

        # Organize Now button (right-aligned)
        self.organize_btn = ctk.CTkButton(
            btn_frame, text="Organize Now →", font=self.FONT_BUTTON, width=160, height=40,
            command=self.organize_now,
            fg_color="#FF9F0A", hover_color="#E08E00"  # Orange to highlight primary action
        )
        self.organize_btn.grid(row=0, column=2, sticky='e')


    def populate_analysis(self):
        """Populate the scrollable frame with analysis results."""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        # Update path subtitle
        path = self.controller.folder_path
        max_len = 70
        display_path = path if len(path) <= max_len else "..." + path[-(max_len-3):]
        self.subtitle_var.set(f"Folder: {display_path}")

        # Check if analysis results exist
        if not self.controller.analysis_result:
            no_files_label = ctk.CTkLabel(self.results_frame, text="No files found or analysis failed.", font=self.FONT_BODY, text_color="gray50")
            no_files_label.pack(pady=20)
            self.summary_label_var.set("No files to organize.")
            self.edit_btn.configure(state="disabled")
            self.organize_btn.configure(state="disabled")
            return

        # Enable buttons if we have results
        self.edit_btn.configure(state="normal")
        self.organize_btn.configure(state="normal")

        # If we have a generated structure, display it
        if self.controller.generated_structure:
            # Add a header for the generated structure
            structure_header = ctk.CTkFrame(self.results_frame, fg_color="transparent")
            structure_header.pack(fill="x", pady=(10, 5))

            structure_label = ctk.CTkLabel(
                structure_header,
                text="AI-Generated Organization Structure",
                font=self.FONT_SUBTITLE,
                anchor="w"
            )
            structure_label.pack(side="left")

            # Display the structure in a tree-like format
            def display_structure(structure, level=0):
                for item, content in structure.items():
                    indent = "    " * level

                    # Determine if this is a folder or file
                    is_folder = isinstance(content, dict)
                    prefix = "📁 " if is_folder else "📄 "

                    # Create a frame for this item
                    item_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
                    item_frame.pack(fill="x", pady=2)

                    # Create the label with appropriate indentation
                    item_label = ctk.CTkLabel(
                        item_frame,
                        text=f"{indent}{prefix}{item}",
                        font=self.FONT_BODY,
                        anchor="w"
                    )
                    item_label.pack(anchor="w", padx=(20 * level, 0))

                    # Add file type indicator if available
                    if not is_folder and not isinstance(content, list) and isinstance(content, str):
                        type_label = ctk.CTkLabel(
                            item_frame,
                            text=f"({content})",
                            font=self.FONT_SMALL,
                            text_color="gray50",
                            anchor="w"
                        )
                        type_label.pack(side="right", padx=10)

                    if isinstance(content, dict):
                        display_structure(content, level + 1)

            # Display the structure
            display_structure(self.controller.generated_structure)

            # Add a separator
            separator = ctk.CTkFrame(self.results_frame, height=2, fg_color="gray70")
            separator.pack(fill="x", pady=15)

            # Add a header for the current files
            current_header = ctk.CTkFrame(self.results_frame, fg_color="transparent")
            current_header.pack(fill="x", pady=(10, 5))

            current_label = ctk.CTkLabel(
                current_header,
                text="Current Files by Type",
                font=self.FONT_SUBTITLE,
                anchor="w"
            )
            current_label.pack(side="left")

        # Sort categories
        sorted_categories = sorted(self.controller.analysis_result.keys())

        for category in sorted_categories:
            files = self.controller.analysis_result[category]
            if not files: continue # Skip empty

            # Category Header
            cat_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
            cat_frame.pack(fill="x", pady=(10, 2))

            cat_label = ctk.CTkLabel(cat_frame, text=f"{category} ({len(files)})", font=self.FONT_BODY_BOLD, anchor="w")
            cat_label.pack(side="left")

            # File List (Indented)
            for file in sorted(files):
                 # Use fg_color="transparent" if you don't want a background for file labels
                file_label = ctk.CTkLabel(self.results_frame, text=file, font=self.FONT_BODY, anchor="w")
                file_label.pack(fill="x", padx=(20, 0), pady=1) # Indent with padx

        # Update summary text (using stored summary)
        self.summary_label_var.set(self.controller.current_analysis_summary)

    def edit_structure(self):
        """Go to the structure editing page"""
        if not self.controller.analysis_result:
             messagebox.showwarning("Nothing to Organize", "The analysis did not find any files to organize.")
             return

        # Prepare the EditStructurePage before showing it
        self.controller.frames["EditStructurePage"].load_structure()
        self.controller.show_frame("EditStructurePage")

    def organize_now(self):
        """Skip structure editing and go directly to confirmation"""
        if not self.controller.analysis_result:
             messagebox.showwarning("Nothing to Organize", "The analysis did not find any files to organize.")
             return

        # Go directly to the confirmation page
        self.controller.show_frame("ConfirmPage")


class EditStructurePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        # Configure grid layout
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=0)  # Button bar
        self.grid_columnconfigure(0, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))

        title = ctk.CTkLabel(header_frame, text="Edit Organization Structure", font=self.FONT_TITLE)
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Customize the organization structure before organizing files",
            font=self.FONT_LABEL,
            text_color="gray50"
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        # --- Main Content Area ---
        content_frame = ctk.CTkFrame(self, corner_radius=10)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 15))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=0)  # Header
        content_frame.grid_rowconfigure(1, weight=1)  # Tree views

        # Left side - Structure Tree
        left_header = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Header with title and add button
        left_title = ctk.CTkLabel(left_header, text="Organization Structure", font=self.FONT_BODY_BOLD)
        left_title.pack(side="left", anchor="w")

        # Add a hint about editing
        edit_hint = ctk.CTkLabel(
            left_header,
            text="(Use ✏️ to rename, 🗑️ to delete)",
            font=self.FONT_SMALL,
            text_color="gray60"
        )
        edit_hint.pack(side="left", padx=10)

        # Add a button to create new categories
        add_category_btn = ctk.CTkButton(
            left_header,
            text="+ New Category",
            font=self.FONT_SMALL,
            width=120,
            height=25,
            command=self._add_new_category
        )
        add_category_btn.pack(side="right", padx=5)

        # Create a frame for the structure tree
        self.structure_frame = ctk.CTkScrollableFrame(content_frame)
        self.structure_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Right side - Files
        right_header = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_header.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        # Header with title and hint
        right_title = ctk.CTkLabel(right_header, text="Files", font=self.FONT_BODY_BOLD)
        right_title.pack(side="left", anchor="w")

        # Add a hint about file organization
        file_hint = ctk.CTkLabel(
            right_header,
            text="(Files will be organized by category)",
            font=self.FONT_SMALL,
            text_color="gray60"
        )
        file_hint.pack(side="left", padx=10)

        # Create a frame for the files list
        self.files_frame = ctk.CTkScrollableFrame(content_frame)
        self.files_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10))

        # --- Button Bar ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=30, pady=(5, 20))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(
            btn_frame, text="← Back", font=self.FONT_BUTTON, width=120,
            fg_color="gray60", hover_color="gray50",
            command=lambda: controller.show_frame("AnalyzePage")
        )
        back_btn.grid(row=0, column=0, sticky='w')

        self.confirm_btn = ctk.CTkButton(
            btn_frame, text="Continue to Organize →", font=self.FONT_BUTTON, width=200, height=40,
            command=self.confirm
        )
        self.confirm_btn.grid(row=0, column=1, sticky='e')

        # Store references to structure widgets
        self.structure_widgets = {}

    def load_structure(self):
        """Load and display the structure"""
        print("DEBUG: Loading structure from scratch")
        
        # Clear any existing widgets
        for widget in self.structure_frame.winfo_children():
            widget.destroy()
        
        # Reset the structure_widgets dictionary
        self.structure_widgets = {}
        
        # Check if we have a generated structure
        if self.controller.generated_structure:
            print("DEBUG: Using generated structure")
            self._display_structure(self.controller.generated_structure)
        else:
            # Fall back to analysis_result if no generated structure
            print("DEBUG: Using analysis_result")
            self._display_files(self.controller.analysis_result)
        
        # Force update
        self.update_idletasks()    
    def _display_structure(self, structure, parent_frame=None, level=0, parent_path=""):
        """Recursively display the structure"""
        if parent_frame is None:
            parent_frame = self.structure_frame

        # Use consistent path separator
        if parent_path and not parent_path.endswith(os.path.sep):
            parent_path = parent_path + os.path.sep

        # Debug: Print all categories that will be displayed
        print(f"DISPLAY: Categories at level {level} with parent '{parent_path}': {list(structure.keys())}")

        # Sort categories for consistent display order
        sorted_categories = sorted(structure.keys())

        for category in sorted_categories:
            contents = structure[category]
            
            # Create the full path for this category (using consistent separator)
            full_path = parent_path + category if parent_path else category
            print(f"DISPLAY: Processing category: '{full_path}'")

            # Create a frame for this category
            category_frame = ctk.CTkFrame(parent_frame, fg_color=("gray90", "gray20"))
            category_frame.pack(fill="x", pady=2, padx=(level*20, 0))

            # Store reference to this category frame with the FULL PATH as the key
            self.structure_widgets[full_path] = category_frame
            print(f"DISPLAY: Added widget for '{full_path}' to structure_widgets")

            # Create header with category name
            header_frame = ctk.CTkFrame(category_frame, fg_color="transparent")
            header_frame.pack(fill="x", pady=2)

            # Add expand/collapse icon
            if isinstance(contents, dict) and contents:
                expand_btn = ctk.CTkButton(
                    header_frame,
                    text="▼",
                    width=20,
                    height=20,
                    font=self.FONT_SMALL,
                    fg_color="transparent",
                    hover_color=("gray80", "gray30"),
                    command=lambda path=full_path: self._toggle_category(path)
                )
                expand_btn.pack(side="left", padx=5)
            else:
                # Placeholder for alignment
                spacer = ctk.CTkFrame(header_frame, width=20, height=20, fg_color="transparent")
                spacer.pack(side="left", padx=5)

            # Category label
            category_label = ctk.CTkLabel(
                header_frame,
                text=category,  # Just show the category name, not the full path
                font=self.FONT_BODY_BOLD,
                anchor="w"
            )
            category_label.pack(side="left", fill="x", expand=True)

            # Add edit button with explicit FULL PATH capture
            # Use a separate function to avoid lambda capture issues
            edit_btn = ctk.CTkButton(
                header_frame,
                text="✏️",
                width=30,
                height=20,
                font=self.FONT_SMALL,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                command=lambda path=full_path: self._edit_category(path)
            )
            edit_btn.pack(side="right", padx=2)

            # Add delete button with explicit FULL PATH capture
            delete_btn = ctk.CTkButton(
                header_frame,
                text="🗑️",
                width=30,
                height=20,
                font=self.FONT_SMALL,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                command=lambda path=full_path: self._delete_category(path)
            )
            delete_btn.pack(side="right", padx=2)

            # Create content frame for subcategories/files
            content_frame = ctk.CTkFrame(category_frame, fg_color="transparent")
            content_frame.pack(fill="x", pady=(0, 5))

            # Store reference to the content frame with the FULL PATH as the key
            self.structure_widgets[f"{full_path}_content"] = content_frame

            # Recursively add subcategories, passing the FULL PATH as parent_path
            if isinstance(contents, dict):
                self._display_structure(contents, content_frame, level + 1, full_path)
            else:
                # Display files if this is a leaf node
                files_list_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                files_list_frame.pack(fill="x", pady=5)
                
                # Display files
                if isinstance(contents, list):
                    files = contents
                elif isinstance(contents, str):
                    files = [contents]
                else:
                    files = []
                    
                for file in sorted(files):
                    file_label = ctk.CTkLabel(
                        files_list_frame,
                        text=file,
                        font=self.FONT_BODY,
                        anchor="w"
                    )
                    file_label.pack(fill="x", padx=5, pady=2)

    def _display_files(self, analysis_result):
        """Display files by category"""
        for category, files in analysis_result.items():
            # Create a category frame
            category_frame = ctk.CTkFrame(self.files_frame)
            category_frame.pack(fill="x", pady=5)

            # Category header
            category_label = ctk.CTkLabel(
                category_frame,
                text=f"{category} ({len(files)})",
                font=self.FONT_BODY_BOLD,
                anchor="w"
            )
            category_label.pack(fill="x", padx=10, pady=5)

            # Files list
            files_list_frame = ctk.CTkFrame(category_frame, fg_color="transparent")
            files_list_frame.pack(fill="x", padx=10, pady=(0, 5))

            # If no files, show a message
            if not files:
                no_files_label = ctk.CTkLabel(
                    files_list_frame,
                    text="No files in this category",
                    font=self.FONT_BODY,
                    text_color="gray50"
                )
                no_files_label.pack(pady=5)

            # Display files
            for file in sorted(files):
                file_label = ctk.CTkLabel(
                    files_list_frame,
                    text=file,
                    font=self.FONT_BODY,
                    anchor="w"
                )
                file_label.pack(fill="x", padx=5, pady=2)



    def _toggle_category(self, category):
        """Expand or collapse a category"""
        content_frame = self.structure_widgets.get(f"{category}_content")
        if content_frame:
            # Toggle visibility
            if content_frame.winfo_viewable():
                content_frame.pack_forget()
            else:
                content_frame.pack(fill="x", pady=(0, 5))

    def _edit_category(self, category):
        """Edit a category name"""
        print(f"EDIT: Starting edit for category: '{category}'")
        
        # Normalize path separators for consistency
        category = category.replace('\\', os.path.sep).replace('/', os.path.sep)
        
        # Get the basename for display
        basename = os.path.basename(category)
        
        new_name = ctk.CTkInputDialog(
            title="Edit Category",
            text=f"Enter new name for '{basename}':"
        ).get_input()

        if new_name and new_name != basename and new_name.strip():
            # Normalize the new name
            new_name = new_name.strip()
            
            print(f"EDIT: Renaming '{category}' to have basename '{new_name}'")
            
            # Split the path into parts
            path_parts = category.split(os.path.sep)
            path_parts = [p for p in path_parts if p]  # Remove empty parts
            
            print(f"EDIT: Path parts: {path_parts}")
            
            # Determine if this is a top-level category or a nested one
            if len(path_parts) == 1:
                # Top-level category
                print(f"EDIT: This is a top-level category")
                
                # Update analysis_result
                if category in self.controller.analysis_result:
                    files = self.controller.analysis_result.pop(category)
                    self.controller.analysis_result[new_name] = files
                    print(f"EDIT: Updated analysis_result for top-level category")
                
                # Update subcategories in analysis_result
                old_prefix = category + os.path.sep
                new_prefix = new_name + os.path.sep
                
                keys_to_update = [k for k in self.controller.analysis_result.keys() 
                                 if k.startswith(old_prefix)]
                
                for old_key in keys_to_update:
                    new_key = new_prefix + old_key[len(old_prefix):]
                    files = self.controller.analysis_result.pop(old_key)
                    self.controller.analysis_result[new_key] = files
                    print(f"EDIT: Updated subcategory: '{old_key}' -> '{new_key}'")
                
                # Update generated_structure
                if self.controller.generated_structure and category in self.controller.generated_structure:
                    content = self.controller.generated_structure.pop(category)
                    self.controller.generated_structure[new_name] = content
                    print(f"EDIT: Updated generated_structure for top-level category")
            else:
                # Nested category
                print(f"EDIT: This is a nested category with {len(path_parts)} parts")
                
                # Get parent path and current basename
                current_basename = path_parts[-1]
                parent_parts = path_parts[:-1]
                parent_path = os.path.sep.join(parent_parts)
                
                # Create the new full path
                new_full_path = os.path.join(parent_path, new_name)
                
                print(f"EDIT: Parent path: '{parent_path}'")
                print(f"EDIT: Current basename: '{current_basename}'")
                print(f"EDIT: New full path will be: '{new_full_path}'")
                
                # Update analysis_result if needed
                if category in self.controller.analysis_result:
                    files = self.controller.analysis_result.pop(category)
                    self.controller.analysis_result[new_full_path] = files
                    print(f"EDIT: Updated analysis_result for nested category")
                
                # Update generated_structure by navigating to the parent
                if self.controller.generated_structure:
                    # Start at the root
                    current = self.controller.generated_structure
                    
                    # Navigate through the parent path
                    for part in parent_parts:
                        print(f"EDIT: Looking for '{part}' in {list(current.keys())}")
                        if part in current:
                            current = current[part]
                            print(f"EDIT: Navigated to '{part}' in structure")
                        else:
                            print(f"EDIT: Failed to find '{part}' in structure")
                            break
                    
                    # Check if we found the target to rename
                    print(f"EDIT: Looking for '{current_basename}' in {list(current.keys())}")
                    if current_basename in current:
                        # Store the content
                        content = current[current_basename]
                        # Remove old key
                        del current[current_basename]
                        # Add with new key
                        current[new_name] = content
                        print(f"EDIT: Successfully renamed '{current_basename}' to '{new_name}' in structure")
                    else:
                        print(f"EDIT: Could not find '{current_basename}' in parent")
                        print(f"EDIT: Available keys: {list(current.keys())}")
        
        # Print the structure after changes for debugging
        print("EDIT: Structure after rename:", self.controller.generated_structure)
        
        # Force complete UI rebuild
        print("EDIT: Forcing complete UI rebuild")
        
        # Clear all widgets
        for widget in self.structure_frame.winfo_children():
            widget.destroy()
        
        # Reset tracking dictionaries
        self.structure_widgets = {}
        
        # Rebuild from scratch
        if self.controller.generated_structure:
            print("EDIT: Rebuilding UI from generated_structure")
            self._display_structure(self.controller.generated_structure)
        else:
            print("EDIT: Rebuilding UI from analysis_result")
            self._display_files(self.controller.analysis_result)
        
        # Force update
        self.update_idletasks()
        
        # Show confirmation
        messagebox.showinfo("Category Renamed", 
                           f"Renamed '{basename}' to '{new_name}'")
    def _update_generated_structure(self, file, target_category):
        """Update the generated structure when a file is moved"""
        # This is a simplified implementation that works with flat structures
        # For nested structures, a more complex recursive approach would be needed

        # First, find and remove the file from its current location in the structure
        file_found = False
        file_type = "file"  # Default file type if not found

        for _, contents in list(self.controller.generated_structure.items()):
            if isinstance(contents, dict):
                # Check subcategories
                for _, files in list(contents.items()):
                    if isinstance(files, dict) and file in files:
                        # Found in a sub-subcategory, remove it
                        file_type = files.pop(file)
                        file_found = True
                        break
                    elif file in files:
                        # Found in a subcategory, remove it
                        file_type = files.pop(file)
                        file_found = True
                        break

                if file_found:
                    break
            elif file in contents:
                # Found directly in a category, remove it
                file_type = contents.pop(file)
                file_found = True
                break

        # Now add the file to the target category
        if file_found:
            # Ensure target category exists
            if target_category not in self.controller.generated_structure:
                self.controller.generated_structure[target_category] = {}

            # If target is a dict, add to a "Files" subcategory
            if isinstance(self.controller.generated_structure[target_category], dict):
                if "Files" not in self.controller.generated_structure[target_category]:
                    self.controller.generated_structure[target_category]["Files"] = {}

                # Add the file with its type
                self.controller.generated_structure[target_category]["Files"][file] = file_type
            else:
                # Target is not a dict, convert it to one
                current_contents = self.controller.generated_structure[target_category]
                self.controller.generated_structure[target_category] = {
                    "Files": current_contents
                }
                # Add the file
                self.controller.generated_structure[target_category]["Files"][file] = file_type
        else:
            print(f"Could not find file '{file}' in generated structure")

    def _add_new_category(self):
        """Add a new category to the structure"""
        new_category = ctk.CTkInputDialog(
            title="New Category",
            text="Enter name for the new category:"
        ).get_input()

        if new_category and new_category.strip():
            # Normalize the category name (trim whitespace)
            new_category = new_category.strip()

            # Check if category already exists
            if new_category in self.controller.analysis_result:
                messagebox.showwarning(
                    "Category Exists",
                    f"A category named '{new_category}' already exists."
                )
                return

            print(f"Adding new category: '{new_category}'")
            print("Before adding - Structure:", list(self.controller.generated_structure.keys()))
            print("Before adding - Analysis:", list(self.controller.analysis_result.keys()))

            # Add the new category to analysis_result
            self.controller.analysis_result[new_category] = []

            # Add to generated structure if it exists
            if self.controller.generated_structure:
                self.controller.generated_structure[new_category] = {}

            print("After adding - Structure:", list(self.controller.generated_structure.keys()))
            print("After adding - Analysis:", list(self.controller.analysis_result.keys()))

            # Force garbage collection to clean up any lingering references
            import gc
            gc.collect()

            # Show the message before rebuilding to avoid UI freezing
            messagebox.showinfo("Category Added", f"Added new category '{new_category}'.")

            # Use the controller's method to completely rebuild the page
            self.controller.rebuild_edit_structure_page()

            # Force update to ensure UI is refreshed
            self.controller.update_idletasks()

            print(f"Created new category: '{new_category}'")

            # Force another update after a short delay
            self.after(100, self.controller.update_idletasks)

    def _delete_category(self, category):
        """Delete a category and move its files to 'Others'"""
        # Debug: Print the exact category being deleted
        print(f"DELETE: Attempting to delete category: '{category}'")
        
        # Normalize path separators for consistency
        category = category.replace('\\', os.path.sep).replace('/', os.path.sep)
        
        # Get the basename for display
        basename = os.path.basename(category)
        
        # Ask for confirmation
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the category '{basename}'?\n\n"
            "Files in this category will be moved to 'Others'."
        ):
            print("DELETE: User cancelled deletion")
            return

        print(f"DELETE: User confirmed deletion of '{category}'")
        print("DELETE: Before deletion - Structure keys:", list(self.controller.generated_structure.keys()))
        print("DELETE: Before deletion - Analysis keys:", list(self.controller.analysis_result.keys()))

        # Split the path into parts
        path_parts = category.split(os.path.sep)
        path_parts = [p for p in path_parts if p]  # Remove empty parts
        
        print(f"DELETE: Path parts: {path_parts}")
        
        # Determine if this is a top-level category or a nested one
        if len(path_parts) == 1:
            # Top-level category
            print(f"DELETE: This is a top-level category")
            
            # Remove from analysis_result
            if category in self.controller.analysis_result:
                files = self.controller.analysis_result.pop(category, [])
                print(f"DELETE: Removed '{category}' from analysis_result with {len(files)} files")

                # Create 'Others' category if it doesn't exist
                if "Others" not in self.controller.analysis_result:
                    self.controller.analysis_result["Others"] = []

                # Move files to 'Others'
                if files:
                    self.controller.analysis_result["Others"].extend(files)
                    print(f"DELETE: Moved {len(files)} files to 'Others' category")
            else:
                print(f"DELETE: Category '{category}' not found in analysis_result")

            # Remove from generated_structure
            if category in self.controller.generated_structure:
                # Ensure 'Others' exists in generated structure
                if "Others" not in self.controller.generated_structure:
                    self.controller.generated_structure["Others"] = {}

                # Move files from the category to 'Others'
                self._move_files_to_others(category)

                # Remove the category
                del self.controller.generated_structure[category]
                print(f"DELETE: Removed '{category}' from generated_structure")
            else:
                print(f"DELETE: Category '{category}' not found in generated_structure")
        else:
            # Nested category
            print(f"DELETE: This is a nested category with {len(path_parts)} parts")
            
            # Get parent path and current basename
            current_basename = path_parts[-1]
            parent_parts = path_parts[:-1]
            parent_path = os.path.sep.join(parent_parts)
            
            print(f"DELETE: Parent path: '{parent_path}'")
            print(f"DELETE: Current basename: '{current_basename}'")
            
            # Remove from analysis_result if needed
            if category in self.controller.analysis_result:
                files = self.controller.analysis_result.pop(category, [])
                print(f"DELETE: Removed '{category}' from analysis_result with {len(files)} files")

                # Create 'Others' category if it doesn't exist
                if "Others" not in self.controller.analysis_result:
                    self.controller.analysis_result["Others"] = []

                # Move files to 'Others'
                if files:
                    self.controller.analysis_result["Others"].extend(files)
                    print(f"DELETE: Moved {len(files)} files to 'Others' category")
            
            # Remove from generated_structure by navigating to the parent
            if self.controller.generated_structure:
                # Start at the root
                current = self.controller.generated_structure
                
                # Navigate through the parent path
                for part in parent_parts:
                    print(f"DELETE: Looking for '{part}' in {list(current.keys())}")
                    if part in current:
                        current = current[part]
                        print(f"DELETE: Navigated to '{part}' in structure")
                    else:
                        print(f"DELETE: Failed to find '{part}' in structure")
                        break
                
                # Check if we found the target to delete
                print(f"DELETE: Looking for '{current_basename}' in {list(current.keys())}")
                if current_basename in current:
                    # Get the content before deleting
                    content = current[current_basename]
                    
                    # If the content is a dict, move its files to 'Others'
                    if isinstance(content, dict):
                        print(f"DELETE: Moving files from subcategory to 'Others'")
                        self._move_subcategory_files_to_others(content)
                    
                    # Remove the category
                    del current[current_basename]
                    print(f"DELETE: Successfully deleted '{current_basename}' from structure")
                else:
                    print(f"DELETE: Could not find '{current_basename}' in parent")
                    print(f"DELETE: Available keys: {list(current.keys())}")

        # Debug: Check if category was actually removed
        print("DELETE: After deletion - Structure keys:", list(self.controller.generated_structure.keys()))
        print("DELETE: After deletion - Analysis keys:", list(self.controller.analysis_result.keys()))
        
        # Clean up any UI widgets for this category
        if category in self.structure_widgets:
            if self.structure_widgets[category].winfo_exists():
                self.structure_widgets[category].destroy()
            self.structure_widgets.pop(category, None)
            print(f"DELETE: Removed widget for '{category}'")

        # Clean up content frame
        content_key = f"{category}_content"
        if content_key in self.structure_widgets:
            if self.structure_widgets[content_key].winfo_exists():
                self.structure_widgets[content_key].destroy()
            self.structure_widgets.pop(content_key, None)
            print(f"DELETE: Removed content widget for '{category}'")

        # Force complete UI rebuild
        print("DELETE: Forcing complete UI rebuild")
        
        # Clear all widgets
        for widget in self.structure_frame.winfo_children():
            widget.destroy()
        
        # Reset tracking dictionaries
        self.structure_widgets = {}
        
        # Rebuild from scratch
        if self.controller.generated_structure:
            print("DELETE: Rebuilding UI from generated_structure")
            self._display_structure(self.controller.generated_structure)
        else:
            print("DELETE: Rebuilding UI from analysis_result")
            self._display_files(self.controller.analysis_result)
        
        # Force update
        self.update_idletasks()
        
        # Show confirmation message
        messagebox.showinfo("Category Deleted", f"Deleted category '{basename}'. Files moved to 'Others'.")
        
        print(f"DELETE: Completed deletion of '{category}'")

    def _move_files_to_others(self, source_category):
        """Move files from a category to 'Others' in the generated structure"""
        if source_category not in self.controller.generated_structure:
            return

        source = self.controller.generated_structure[source_category]

        # Ensure 'Others' exists
        if "Others" not in self.controller.generated_structure:
            self.controller.generated_structure["Others"] = {}

        # Ensure 'Files' exists in 'Others'
        if "Files" not in self.controller.generated_structure["Others"]:
            self.controller.generated_structure["Others"]["Files"] = {}

        others_files = self.controller.generated_structure["Others"]["Files"]

        # Process the source recursively
        def process_structure(struct, path_prefix=""):
            for name, content in struct.items():
                current_path = os.path.join(path_prefix, name) if path_prefix else name
                
                if isinstance(content, dict):
                    # Recursively process subdirectories
                    process_structure(content, current_path)
                else:
                    # Move file to Others/Files
                    if isinstance(content, str):
                        # Single file
                        others_files[name] = content
                        print(f"DELETE: Moved file '{name}' to Others/Files")
                    elif isinstance(content, list):
                        # List of files
                        for file in content:
                            others_files[file] = "file"
                            print(f"DELETE: Moved file '{file}' to Others/Files")

        # Start processing
        process_structure(source)

    def _move_subcategory_files_to_others(self, structure, path_prefix=""):
        """Recursively move files from a subcategory structure to 'Others'"""
        # Ensure 'Others' exists in generated structure
        if "Others" not in self.controller.generated_structure:
            self.controller.generated_structure["Others"] = {}
        
        # Ensure 'Files' exists in 'Others'
        if "Files" not in self.controller.generated_structure["Others"]:
            self.controller.generated_structure["Others"]["Files"] = {}
        
        # Target for files
        others_files = self.controller.generated_structure["Others"]["Files"]
        
        # Process the structure recursively
        for name, content in structure.items():
            current_path = os.path.join(path_prefix, name) if path_prefix else name
            
            if isinstance(content, dict):
                # Recursively process subdirectories
                self._move_subcategory_files_to_others(content, current_path)
            else:
                # Move file to Others/Files
                if isinstance(content, str):
                    # Single file
                    others_files[name] = content
                    print(f"DELETE: Moved file '{name}' to Others/Files")
                elif isinstance(content, list):
                    # List of files
                    for file in content:
                        others_files[file] = "file"
                        print(f"DELETE: Moved file '{file}' to Others/Files")

    def confirm(self):
        """Proceed to the confirmation page"""
        self.controller.show_frame("ConfirmPage")


class ConfirmPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        # Center content vertically and horizontally
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, corner_radius=10, width=400) # Fixed width for the card
        card.grid(row=0, column=0) # Centered by grid config

        # --- Icon and Title ---
        # Consider using a CTkImage here if you have an icon file
        icon_label = ctk.CTkLabel(card, text="⚠️", font=(self.FONT_TITLE[0], 60)) # Large Emoji
        icon_label.pack(pady=(25, 10))

        title = ctk.CTkLabel(card, text="Confirm Organization", font=self.FONT_SUBTITLE, wraplength=350)
        title.pack(pady=(0, 10))

        # --- Warning Text ---
        warning_text = ("This will move files into new subfolders within the selected directory.\n\nThis action cannot be automatically undone.")
        warning_details = ctk.CTkLabel(card, text=warning_text, font=self.FONT_BODY, text_color="gray50", justify="center", wraplength=350)
        warning_details.pack(pady=(0, 25))

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=(10, 25))

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Back", font=self.FONT_BUTTON, width=120,
            fg_color="gray60", hover_color="gray50",
            command=lambda: controller.show_frame("EditStructurePage")
        )
        cancel_btn.pack(side="left", padx=10)

        self.confirm_btn = ctk.CTkButton(
            btn_frame, text="Yes, Organize Now", font=self.FONT_BUTTON, width=160, height=40,
            command=self.organize,
            # Use theme colors for warning/danger state
            fg_color="#FF9F0A", hover_color="#E08E00" # Custom Orange/Darker Orange
            # Or use CTk's default red: fg_color="red", hover_color="#darkred" # Requires custom theme? Check CTk docs.
        )
        self.confirm_btn.pack(side="left", padx=10)

    def organize(self):
        original_text = self.confirm_btn.cget("text")
        self.confirm_btn.configure(text="Organizing...", state="disabled")
        self.update_idletasks()

        success = self.controller.organize_files()

        self.confirm_btn.configure(text=original_text, state="normal")

        if success:
            # Optional: Update CompletePage message before showing
            self.controller.frames["CompletePage"].update_completion_message()
            self.controller.show_frame("CompletePage")
        # else: Error message shown in organize_files, stay here


class CompletePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        # Center content
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, corner_radius=10, width=400)
        card.grid(row=0, column=0)

        # --- Icon and Title ---
        icon_label = ctk.CTkLabel(card, text="✅", font=(self.FONT_TITLE[0], 60))
        icon_label.pack(pady=(25, 10))

        title = ctk.CTkLabel(card, text="Organization Complete!", font=self.FONT_SUBTITLE)
        title.pack(pady=(0, 10))

        # --- Details Text ---
        self.details_var = ctk.StringVar(value="Files have been successfully organized.")
        details_label = ctk.CTkLabel(card, textvariable=self.details_var, font=self.FONT_BODY, text_color="gray50", wraplength=350)
        details_label.pack(pady=(0, 30))

        # --- Buttons (Vertical Layout) ---
        btn_width = 220 # Make buttons wider

        open_btn = ctk.CTkButton(
            card, text="📂 Open Folder", font=self.FONT_BUTTON, width=btn_width, height=40,
            command=self.open_folder  # Changed from self.controller.open_folder to self.open_folder
        )
        open_btn.pack(pady=8)

        again_btn = ctk.CTkButton(
            card, text="Organize Another Folder", font=self.FONT_BUTTON, width=btn_width, height=40,
            command=self.go_to_start
        )
        again_btn.pack(pady=8)

        exit_btn = ctk.CTkButton(
            card, text="Exit Application", font=self.FONT_BUTTON, width=btn_width,
            fg_color="gray60", hover_color="gray50", command=self.controller.quit
        )
        exit_btn.pack(pady=(8, 25))

    def open_folder(self):
        """Open the organized folder in file explorer"""
        path = self.controller.folder_path
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Open Folder", "Cannot open folder. Path is invalid or not set.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def update_completion_message(self):
        """Updates the message shown on the completion screen."""
        folder_name = os.path.basename(self.controller.folder_path) if self.controller.folder_path else "Selected folder"

        # If we have an organization summary, use it
        if hasattr(self.controller, 'organization_summary'):
            self.details_var.set(f"Organized '{folder_name}'.\n\n{self.controller.organization_summary}")
        else:
            # Fallback to the analysis summary
            summary = self.controller.current_analysis_summary
            self.details_var.set(f"Organized '{folder_name}'.\n({summary})")


    def go_to_start(self):
        """Resets state and returns to the StartPage."""
        self.controller.folder_path = ""
        self.controller.analysis_result = {}
        self.controller.generated_structure = {}  # Reset the generated structure
        self.controller.current_analysis_summary = ""
        # Remove organization summary if it exists
        if hasattr(self.controller, 'organization_summary'):
            delattr(self.controller, 'organization_summary')

        start_page = self.controller.frames["StartPage"]
        # Reset StartPage widgets
        start_page.path_var.set("No folder selected")
        start_page.path_display_widget.configure(text_color="gray50")
        start_page.analyze_btn.configure(state="disabled")
        self.controller.show_frame("StartPage")


# --- Main Execution ---
if __name__ == "__main__":
    # Dependency check
    try:
        # Check for required packages
        import customtkinter
        from PIL import Image
        from langchain_google_genai import GoogleGenerativeAI
    except ImportError as e:
        # Use standard tkinter for the error message box
        import tkinter as tk
        from tkinter import messagebox

        root_err = tk.Tk()
        root_err.withdraw()

        missing_package = str(e).split("'")[1] if "'" in str(e) else str(e)

        if messagebox.askyesno("Missing Dependency",
                              f"This application requires the {missing_package} package. Would you like to install it now?"):
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", missing_package])
                messagebox.showinfo("Installation Complete", f"{missing_package} has been installed. Please restart the application.")
            except Exception as install_error:
                messagebox.showerror("Installation Error", f"Failed to install {missing_package}: {install_error}")
        else:
            messagebox.showerror("Error", f"{missing_package} is required to run this application.")

        root_err.destroy()
        sys.exit(1)

    app = FileOrganizerApp()
    app.mainloop()
