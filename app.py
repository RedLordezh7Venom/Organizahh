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
    QApplication 
)

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

# --- Main Application Window ---
from pyQT.Main import FileOrganizerApp


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