import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.font import Font
import json
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import sys
from pathlib import Path

class ThemeColors:
    """Modern color palette for the application"""
    PRIMARY = "#4361EE"
    PRIMARY_DARK = "#3A56D4"
    PRIMARY_LIGHT = "#4895EF"
    SECONDARY = "#4CC9F0"
    BACKGROUND = "#F8F9FA"
    CARD_BG = "#FFFFFF"
    TEXT_PRIMARY = "#212529"
    TEXT_SECONDARY = "#6C757D"
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    GRAY_LIGHT = "#E9ECEF"

class ModernButton(tk.Button):
    """Enhanced button with hover effects and modern styling"""
    def __init__(self, master, **kwargs):
        self.bg_color = kwargs.pop('bg_color', ThemeColors.PRIMARY)
        self.hover_color = kwargs.pop('hover_color', ThemeColors.PRIMARY_DARK)
        self.fg_color = kwargs.pop('fg_color', "#FFFFFF")
        
        super().__init__(master, **kwargs)
        self.configure(
            bg=self.bg_color,
            fg=self.fg_color,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            activebackground=self.hover_color,
            activeforeground=self.fg_color,
            borderwidth=0,
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = self.hover_color

    def on_leave(self, e):
        self['background'] = self.bg_color

class SecondaryButton(ModernButton):
    """Secondary style button"""
    def __init__(self, master, **kwargs):
        kwargs['bg_color'] = ThemeColors.GRAY_LIGHT
        kwargs['hover_color'] = "#D0D4D9"
        kwargs['fg_color'] = ThemeColors.TEXT_PRIMARY
        super().__init__(master, **kwargs)

class CardFrame(tk.Frame):
    """Frame with card-like appearance and shadow effect"""
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg', ThemeColors.CARD_BG)
        super().__init__(parent, **kwargs)
        self.configure(
            bg=bg_color,
            highlightbackground="#E0E0E0",
            highlightthickness=1,
            padx=15,
            pady=15,
        )

def create_rounded_rectangle(width, height, radius, color):
    """Create a rounded rectangle image for UI elements"""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([(0, 0), (width-1, height-1)], radius, fill=color)
    return image

class FileOrganizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart File Organizer")
        self.geometry("900x650")
        self.minsize(800, 600)
        self.configure(bg=ThemeColors.BACKGROUND)
        
        # Set app icon if available
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        
        # Load backbone.json
        try:
            with open('backbone.json', 'r') as f:
                self.backbone = json.load(f)
        except:
            self.backbone = {}

        self.folder_path = ""
        self.analysis_result = {}

        # Configure grid weight for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create container
        container = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Create header with app name
        header = tk.Frame(self, bg=ThemeColors.PRIMARY, height=60)
        header.place(x=0, y=0, relwidth=1)
        
        header_title = tk.Label(
            header, 
            text="Smart File Organizer", 
            font=("Segoe UI", 16, "bold"),
            bg=ThemeColors.PRIMARY,
            fg="white"
        )
        header_title.place(relx=0.5, rely=0.5, anchor="center")

        # Create frames for each page
        self.frames = {}
        for F in (StartPage, AnalyzePage, ConfirmPage, CompletePage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            frame.configure(bg=ThemeColors.BACKGROUND)

        # Show the start page
        self.show_frame("StartPage")

    def show_frame(self, page_name):
        """Show a frame for the given page name"""
        for frame in self.frames.values():
            frame.grid_remove()
            
        frame = self.frames[page_name]
        frame.grid()
        frame.tkraise()
        frame.event_generate("<<ShowFrame>>")
        
        # Update window title based on current page
        page_titles = {
            "StartPage": "Smart File Organizer - Home",
            "AnalyzePage": "Smart File Organizer - Analysis",
            "ConfirmPage": "Smart File Organizer - Confirm",
            "CompletePage": "Smart File Organizer - Complete"
        }
        self.title(page_titles.get(page_name, "Smart File Organizer"))

    def analyze_folder(self):
        """Analyze the selected folder structure"""
        if self.folder_path in self.backbone:
            self.analysis_result = self.analyze_with_backbone()
        else:
            self.analysis_result = self.analyze_by_extension()

    def analyze_with_backbone(self):
        """Analyze folder using backbone.json structure"""
        result = {}
        structure = self.backbone[self.folder_path]
        
        def process_structure(struct, prefix=""):
            for name, content in struct.items():
                if isinstance(content, dict):
                    category = f"{prefix}/{name}" if prefix else name
                    result[category] = []
                    process_structure(content, category)
                else:
                    category = prefix if prefix else "Uncategorized"
                    if category not in result:
                        result[category] = []
                    result[category].append(name)
        
        process_structure(structure)
        return result

    def analyze_by_extension(self):
        """Analyze folder by file extensions"""
        result = {}
        for root, _, files in os.walk(self.folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                category = self.get_category(ext)
                result.setdefault(category, []).append(file)
        return result

    def get_category(self, ext):
        """Get category based on file extension"""
        categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            'Documents': ['.pdf', '.docx', '.txt', '.doc', '.xlsx', '.pptx', '.odt', '.rtf', '.md'],
            'Videos': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb'],
            'Executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm']
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return 'Others'

    def organize_files(self):
        """Organize files according to analysis results"""
        try:
            for category, files in self.analysis_result.items():
                category_path = os.path.join(self.folder_path, category)
                os.makedirs(category_path, exist_ok=True)
                for file in files:
                    src = os.path.join(self.folder_path, file)
                    dst = os.path.join(category_path, file)
                    if os.path.exists(src) and os.path.isfile(src):
                        shutil.move(src, dst)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            return False

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Configure for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main content frame
        main_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header section
        header_frame = tk.Frame(main_frame, bg=ThemeColors.BACKGROUND)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(30, 0))
        
        # Title with custom font
        title_font = Font(family="Segoe UI", size=28, weight="bold")
        label = tk.Label(
            header_frame,
            text="Organize Your Files",
            font=title_font,
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.PRIMARY
        )
        label.pack(pady=(0, 10))

        # Subtitle
        subtitle = tk.Label(
            header_frame,
            text="Smart organization for your digital workspace",
            font=("Segoe UI", 14),
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.TEXT_SECONDARY
        )
        subtitle.pack(pady=(0, 30))
        
        # Card content
        content_card = CardFrame(main_frame, bg=ThemeColors.CARD_BG)
        content_card.grid(row=1, column=0, sticky="nsew", padx=50, pady=30)
        content_card.grid_columnconfigure(0, weight=1)
        
        # Folder selection section
        folder_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        folder_frame.pack(pady=20, fill="x", expand=True)
        
        folder_label = tk.Label(
            folder_frame,
            text="Select a folder to organize:",
            font=("Segoe UI", 12),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_PRIMARY
        )
        folder_label.pack(anchor="w", padx=10, pady=(0, 15))
        
        # Browse button with icon
        browse_frame = tk.Frame(folder_frame, bg=ThemeColors.CARD_BG)
        browse_frame.pack(fill="x", padx=10)
        
        browse_button = ModernButton(
            browse_frame,
            text="Browse Folders",
            command=self.browse_folder
        )
        browse_button.pack(side="left")
        
        # Path display with better styling
        self.path_frame = tk.Frame(folder_frame, bg=ThemeColors.CARD_BG)
        self.path_frame.pack(pady=(20, 10), fill="x", padx=10)
        
        self.path_var = tk.StringVar()
        self.path_var.set("")
        
        self.path_label = tk.Label(
            self.path_frame,
            textvariable=self.path_var,
            font=("Segoe UI", 10),
            bg=ThemeColors.GRAY_LIGHT,
            fg=ThemeColors.TEXT_PRIMARY,
            wraplength=600,
            anchor="w",
            justify="left",
            padx=15,
            pady=12,
            relief="flat"
        )
        
        # Action buttons
        button_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        button_frame.pack(pady=30, fill="x")
        
        self.analyze_btn = ModernButton(
            button_frame,
            text="Analyze Folder",
            state="disabled",
            command=self.go_to_analysis
        )
        self.analyze_btn.pack(pady=10)
        
        # Features section
        features_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        features_frame.pack(fill="x", pady=(20, 10), padx=10)
        
        features_title = tk.Label(
            features_frame,
            text="Features",
            font=("Segoe UI", 14, "bold"),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_PRIMARY
        )
        features_title.pack(anchor="w", pady=(0, 10))
        
        features = [
            "✓ Smart categorization by file type",
            "✓ Custom organization structures",
            "✓ Preview before organizing",
            "✓ Fast and efficient processing"
        ]
        
        for feature in features:
            feature_label = tk.Label(
                features_frame,
                text=feature,
                font=("Segoe UI", 11),
                bg=ThemeColors.CARD_BG,
                fg=ThemeColors.TEXT_SECONDARY,
                anchor="w",
                pady=5
            )
            feature_label.pack(fill="x")

    def browse_folder(self):
        """Open folder browser dialog"""
        path = filedialog.askdirectory()
        if path:
            self.controller.folder_path = path
            self.path_var.set(path)
            self.path_label.pack(fill="x")
            self.analyze_btn.config(state="normal")

    def go_to_analysis(self):
        """Process folder and go to analysis page"""
        # Show loading indicator
        self.analyze_btn.config(text="Analyzing...", state="disabled")
        self.update()
        
        # Perform analysis
        self.controller.analyze_folder()
        
        # Update UI and proceed
        self.controller.frames["AnalyzePage"].populate_analysis()
        self.controller.show_frame("AnalyzePage")
        
        # Reset button state
        self.analyze_btn.config(text="Analyze Folder", state="normal")

class AnalyzePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Configure for responsiveness
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header section
        header_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(20, 10))
        
        # Title
        title_font = Font(family="Segoe UI", size=22, weight="bold")
        label = tk.Label(
            header_frame,
            text="Analysis Results",
            font=title_font,
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.PRIMARY
        )
        label.pack(pady=(0, 5))
        
        # Subtitle with folder path
        self.subtitle = tk.Label(
            header_frame,
            text="",
            font=("Segoe UI", 11),
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.TEXT_SECONDARY,
            wraplength=700
        )
        self.subtitle.pack(pady=(0, 10))

        # Create a card frame for the treeview
        tree_card = CardFrame(self, bg=ThemeColors.CARD_BG)
        tree_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(0, weight=1)

        # Create Treeview with modern styling
        tree_frame = tk.Frame(tree_card, bg=ThemeColors.CARD_BG)
        tree_frame.pack(fill="both", expand=True)

        # Configure style for treeview
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background=ThemeColors.CARD_BG,
            foreground=ThemeColors.TEXT_PRIMARY,
            rowheight=30,
            fieldbackground=ThemeColors.CARD_BG,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=ThemeColors.PRIMARY_LIGHT,
            foreground="white",
            font=("Segoe UI", 11, "bold"),
            borderwidth=0
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", ThemeColors.PRIMARY_LIGHT)],
            foreground=[("selected", "white")]
        )

        # Create Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            style="Custom.Treeview",
            selectmode="none"
        )
        self.tree.pack(side="left", fill="both", expand=True)

        # Add scrollbar with modern styling
        scrollbar_style = ttk.Style()
        scrollbar_style.configure("Custom.Vertical.TScrollbar", 
                                  background=ThemeColors.PRIMARY_LIGHT,
                                  troughcolor=ThemeColors.GRAY_LIGHT,
                                  borderwidth=0,
                                  arrowsize=14)
        
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview,
            style="Custom.Vertical.TScrollbar"
        )
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Configure Treeview
        self.tree["columns"] = ("count",)
        self.tree.column("#0", width=400, minwidth=200)
        self.tree.column("count", width=100, anchor="center", minwidth=80)
        self.tree.heading("#0", text="Category/File")
        self.tree.heading("count", text="Count")

        # Summary section
        self.summary_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        self.summary_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        self.summary_label = tk.Label(
            self.summary_frame,
            text="",
            font=("Segoe UI", 11),
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.TEXT_SECONDARY
        )
        self.summary_label.pack(pady=5)

        # Button frame
        btn_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))

        back_btn = SecondaryButton(
            btn_frame,
            text="← Back",
            command=lambda: controller.show_frame("StartPage")
        )
        back_btn.pack(side="left", padx=20)

        confirm_btn = ModernButton(
            btn_frame,
            text="Organize Files →",
            command=self.confirm
        )
        confirm_btn.pack(side="right", padx=20)

    def populate_analysis(self):
        """Populate treeview with analysis results"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Update subtitle with folder path
        self.subtitle.config(text=f"Folder: {self.controller.folder_path}")

        # Add new items
        total_files = 0
        total_categories = 0
        
        for category, files in self.controller.analysis_result.items():
            total_categories += 1
            total_files += len(files)
            
            category_id = self.tree.insert(
                "",
                "end",
                text=category,
                values=(len(files),),
                tags=("category",)
            )
            for file in files:
                self.tree.insert(
                    category_id,
                    "end",
                    text=file,
                    tags=("file",)
                )

        # Configure tags
        self.tree.tag_configure("category", font=("Segoe UI", 11, "bold"))
        self.tree.tag_configure("file", font=("Segoe UI", 10))
        
        # Update summary
        self.summary_label.config(
            text=f"Summary: {total_files} files will be organized into {total_categories} categories"
        )

    def confirm(self):
        """Go to confirmation page"""
        self.controller.show_frame("ConfirmPage")

class ConfirmPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Configure for responsiveness
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(30, 20))
        
        # Title
        title_font = Font(family="Segoe UI", size=22, weight="bold")
        label = tk.Label(
            header_frame,
            text="Confirm Organization",
            font=title_font,
            bg=ThemeColors.BACKGROUND,
            fg=ThemeColors.PRIMARY
        )
        label.pack(pady=(0, 10))

        # Main content card
        content_card = CardFrame(self, bg=ThemeColors.CARD_BG)
        content_card.grid(row=1, column=0, sticky="nsew", padx=50, pady=(0, 30))
        
        # Warning icon
        warning_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        warning_frame.pack(pady=(20, 10))
        
        warning_icon = tk.Label(
            warning_frame,
            text="⚠️",
            font=("Segoe UI", 48),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.WARNING
        )
        warning_icon.pack()

        # Warning message
        warning = tk.Label(
            content_card,
            text="You are about to organize all files according to the analysis.",
            font=("Segoe UI", 12, "bold"),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_PRIMARY
        )
        warning.pack(pady=(10, 5))
        
        warning_details = tk.Label(
            content_card,
            text="This will move files into category folders. The process cannot be automatically undone.",
            font=("Segoe UI", 11),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_SECONDARY,
            wraplength=500
        )
        warning_details.pack(pady=(0, 20))
        
        # Confirmation question
        confirm_question = tk.Label(
            content_card,
            text="Are you sure you want to proceed?",
            font=("Segoe UI", 12),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_PRIMARY
        )
        confirm_question.pack(pady=(10, 20))

        # Buttons
        btn_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        btn_frame.pack(pady=20)

        cancel_btn = SecondaryButton(
            btn_frame,
            text="Cancel",
            command=lambda: controller.show_frame("AnalyzePage")
        )
        cancel_btn.grid(row=0, column=0, padx=10)

        self.confirm_btn = ModernButton(
            btn_frame,
            text="Yes, Organize Files",
            command=self.organize
        )
        self.confirm_btn.grid(row=0, column=1, padx=10)

    def organize(self):
        """Organize files and go to completion page"""
        self.confirm_btn.config(text="Organizing...", state="disabled")
        self.update()
        
        success = self.controller.organize_files()
        if success:
            self.controller.show_frame("CompletePage")
        
        self.confirm_btn.config(text="Yes, Organize Files", state="normal")

class CompletePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Configure for responsiveness
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = tk.Frame(self, bg=ThemeColors.BACKGROUND)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(30, 20))
        
        # Main content card
        content_card = CardFrame(self, bg=ThemeColors.CARD_BG)
        content_card.grid(row=1, column=0, sticky="nsew", padx=50, pady=(0, 30))

        # Success icon
        success_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        success_frame.pack(pady=(30, 10))
        
        success_icon = tk.Label(
            success_frame,
            text="✅",
            font=("Segoe UI", 48),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.SUCCESS
        )
        success_icon.pack()

        # Success message
        title_font = Font(family="Segoe UI", size=22, weight="bold")
        label = tk.Label(
            content_card,
            text="Organization Complete!",
            font=title_font,
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.PRIMARY
        )
        label.pack(pady=(10, 5))
        
        success_details = tk.Label(
            content_card,
            text="Your files have been successfully organized into categories.",
            font=("Segoe UI", 11),
            bg=ThemeColors.CARD_BG,
            fg=ThemeColors.TEXT_SECONDARY
        )
        success_details.pack(pady=(0, 30))

        # Buttons in a vertical layout
        button_frame = tk.Frame(content_card, bg=ThemeColors.CARD_BG)
        button_frame.pack(pady=(0, 30))
        
        open_btn = ModernButton(
            button_frame,
            text="Open Folder",
            command=self.open_folder
        )
        open_btn.pack(pady=10, fill="x", ipady=5)

        again_btn = ModernButton(
            button_frame,
            text="Organize Another Folder",
            command=lambda: controller.show_frame("StartPage")
        )
        again_btn.pack(pady=10, fill="x", ipady=5)

        exit_btn = SecondaryButton(
            button_frame,
            text="Exit Application",
            command=controller.quit
        )
        exit_btn.pack(pady=10, fill="x", ipady=5)

    def open_folder(self):
        """Open the organized folder in file explorer"""
        path = self.controller.folder_path
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':  # macOS
                import subprocess
                subprocess.Popen(['open', path])
            else:  # Linux
                import subprocess
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")

if __name__ == "__main__":
    # Check for required packages
    try:
        from PIL import Image, ImageTk, ImageDraw, ImageFilter
    except ImportError:
        if messagebox.askyesno("Missing Dependency", 
                              "This application requires the Pillow library. Would you like to install it now?"):
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            messagebox.showinfo("Installation Complete", "Pillow has been installed. Please restart the application.")
            sys.exit(0)
        else:
            messagebox.showerror("Error", "Pillow is required to run this application.")
            sys.exit(1)
    
    app = FileOrganizerApp()
    
    # Configure style
    style = ttk.Style()
    style.configure("Treeview", font=("Segoe UI", 10))
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    
    app.mainloop()