import customtkinter as ctk
import tkinter as tk # Keep tkinter for filedialog
from tkinter import filedialog # Keep filedialog for the browse button (if you still want it)
from PIL import Image, ImageTk
import os
--- Configuration ---
WINDOW_WIDTH = 800 # Increased width for the file explorer
WINDOW_HEIGHT = 600
BG_IMAGE_PATH = "background.png" # Replace with your actual path
ICON_IMAGE_PATH = "folder_icon.png" # Replace with your actual path
TITLE_TEXT = "Smart File organizer"
SUBTITLE_TEXT = "Organize your folders effortlessly."
BUTTON_TEXT = "Browse Folder" # Removed for now, can add back if needed
--- Custom File Explorer Class ---
class CustomFileExplorer(ctk.CTkFrame):
def init(self, master=None):
super().init(master)
self.master = master
self.current_path = ctk.StringVar(value=os.path.expanduser("~")) # Start in user's home directory
self.history = []
self.history_index = -1
self.create_widgets()
self.load_directory(self.current_path.get())
def create_widgets(self):
    # Path Entry and Browse Button Frame
    path_frame = ctk.CTkFrame(self)
    path_frame.pack(fill="x", padx=5, pady=(5, 0))

    self.path_entry = ctk.CTkEntry(path_frame, textvariable=self.current_path)
    self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    self.path_entry.bind("<Return>", self.on_path_enter)

    browse_button = ctk.CTkButton(path_frame, text="Browse", width=80, command=self.browse_directory_dialog)
    browse_button.pack(side="left")

    # Navigation Buttons Frame
    nav_frame = ctk.CTkFrame(self)
    nav_frame.pack(fill="x", padx=5, pady=(0, 5))

    back_button = ctk.CTkButton(nav_frame, text="Back", width=80, command=self.go_back)
    back_button.pack(side="left", padx=(0, 5))

    up_button = ctk.CTkButton(nav_frame, text="Up", width=80, command=self.go_up)
    up_button.pack(side="left")

    # File/Folder Listing (Scrollable Frame with Labels/Buttons)
    # CustomTkinter doesn't have a direct Treeview equivalent, so we'll simulate it
    self.file_list_frame = ctk.CTkScrollableFrame(self)
    self.file_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

def load_directory(self, path):
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        print(f"Error: Not a valid directory: {path}")
        return

    self.current_path.set(path)
    self.history.append(path)
    self.history_index += 1

    # Clear the scrollable frame
    for widget in self.file_list_frame.winfo_children():
        widget.destroy()

    try:
        items = os.listdir(path)
        # Sort directories first, then files
        items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

        for item_name in items:
            item_path = os.path.join(path, item_name)
            if os.path.isfile(item_path):
                file_size = self.get_human_readable_size(os.path.getsize(item_path))
                item_text = f"{item_name} (File) - {file_size}"
                item_widget = ctk.CTkButton(self.file_list_frame, text=item_text, anchor="w", command=lambda p=item_path: self.on_file_click(p))
                item_widget.pack(fill="x", pady=1)
            elif os.path.isdir(item_path):
                item_text = f"{item_name} (Folder)"
                item_widget = ctk.CTkButton(self.file_list_frame, text=item_text, anchor="w", command=lambda p=item_path: self.load_directory(p))
                item_widget.pack(fill="x", pady=1)

    except PermissionError:
        print(f"Permission denied: {path}")
        self.current_path.set("Permission Denied")
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        error_label = ctk.CTkLabel(self.file_list_frame, text="Permission Denied", text_color="red")
        error_label.pack()
    except Exception as e:
        print(f"An error occurred while loading directory: {e}")
        self.current_path.set("Error Loading Directory")
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        error_label = ctk.CTkLabel(self.file_list_frame, text=f"Error: {e}", text_color="red")
        error_label.pack()


def on_file_click(self, file_path):
    """Action when a file is clicked."""
    print(f"File clicked: {file_path}")
    # You can add logic here to open the file, show details, etc.

def on_path_enter(self, event):
    path = self.path_entry.get()
    self.load_directory(path)

def browse_directory_dialog(self):
    """Opens a native file dialog to select a directory."""
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        self.load_directory(folder_selected)

def go_up(self):
    current_path = self.current_path.get()
    parent_path = os.path.dirname(current_path)
    if parent_path != current_path:  # Avoid going above the root
        self.load_directory(parent_path)

def go_back(self):
    # Simple back (doesn't remember forward)
    if self.history_index > 0:
         self.history_index -= 1
         # Remove the current path from history before loading the previous one
         if self.history:
             self.history.pop()
         if self.history:
             previous_path = self.history[-1]
             self.load_directory(previous_path)
         else: # If history is empty after pop, go to home
             self.load_directory(os.path.expanduser("~"))


def get_human_readable_size(self, size, precision=2):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1
        size /= 1024.0
    return "%.*f %s" % (precision, size, suffixes[suffixIndex])


class App(ctk.CTk):
def init(self, width, height):
super().init()
self.width = width
self.height = height
self.title(TITLE_TEXT)
    # Set CustomTkinter appearance mode and color theme
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "dark-blue", "green"

    # Center the window on the screen
    self.center_window(width, height)
    self.resizable(True, True) # Allow resizing

    # --- Load Assets ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(script_dir, BG_IMAGE_PATH)
    icon_path = os.path.join(script_dir, ICON_IMAGE_PATH)

    # Note: CustomTkinter doesn't have a simple background image on the window itself
    # We'll skip the background image for simplicity in this CustomTkinter example
    # If you need a background image, you might need to use a CTkCanvas or place
    # widgets on top of a background image label/frame.

    # Load icon image (for potential use elsewhere, not directly on the CustomFileExplorer)
    try:
        self.icon_image_pil = Image.open(icon_path)
        icon_width = 60 # Fixed size for the icon
        aspect_ratio = self.icon_image_pil.height / self.icon_image_pil.width
        icon_height = int(icon_width * aspect_ratio)
        self.icon_image_ctk = ctk.CTkImage(light_image=self.icon_image_pil,
                                            dark_image=self.icon_image_pil,
                                            size=(icon_width, icon_height))

    except FileNotFoundError as e:
        print(f"Error loading icon image: {e}")
        self.icon_image_ctk = None
    except Exception as e:
        print(f"An error occurred loading icon: {e}")
        self.icon_image_ctk = None


    # --- Create Widgets ---
    self.create_widgets()

def center_window(self, width, height):
    """Centers the CustomTkinter window on the screen."""
    screen_width = self.winfo_screenwidth()
    screen_height = self.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    self.geometry(f'{width}x{height}+{x}+{y}')

def create_widgets(self):
    # Use CustomTkinter fonts (optional, can use default)
    title_font = ctk.CTkFont(family="Segoe UI", size=36, weight="bold")
    subtitle_font = ctk.CTkFont(family="Segoe UI", size=16)

    # Title and Subtitle Labels
    title_label = ctk.CTkLabel(self, text=TITLE_TEXT, font=title_font)
    title_label.pack(pady=(20, 0))

    subtitle_label = ctk.CTkLabel(self, text=SUBTITLE_TEXT, font=subtitle_font)
    subtitle_label.pack(pady=(0, 10))

    # Optional: Display the icon
    if self.icon_image_ctk:
        icon_label = ctk.CTkLabel(self, image=self.icon_image_ctk, text="")
        icon_label.pack(pady=(0, 10))


    # --- Embed CustomFileExplorer ---
    self.file_explorer = CustomFileExplorer(self)
    self.file_explorer.pack(fill="both", expand=True, padx=10, pady=10)


if name == "main":
# --- Create Placeholder Images (if they don't exist) ---
# This part is just for demonstration if you don't have the images ready.
def create_placeholder_images():
script_dir = os.path.dirname(os.path.abspath(file))
bg_path = os.path.join(script_dir, BG_IMAGE_PATH)
icon_path = os.path.join(script_dir, ICON_IMAGE_PATH)
if not os.path.exists(bg_path):
        try:
            print(f"Creating placeholder gradient: {BG_IMAGE_PATH}")
            img = Image.new('RGB', (WINDOW_WIDTH, WINDOW_HEIGHT), color = '#AA00AA') # Purple fallback
            for y in range(WINDOW_HEIGHT):
                for x in range(WINDOW_WIDTH):
                     r = int(50 + 150 * (x + y) / (WINDOW_WIDTH + WINDOW_HEIGHT))
                     g = int(50 + 50 * x / WINDOW_WIDTH)
                     b = int(150 - 100 * y / WINDOW_HEIGHT)
                     img.putpixel((x, y), (r,g,b))
            img.save(bg_path)
        except Exception as e:
            print(f"Could not create placeholder background: {e}")

    if not os.path.exists(icon_path):
         try:
            print(f"Creating placeholder icon: {ICON_IMAGE_PATH}")
            img = Image.new('RGBA', (200, 150), color = (0,0,0,0)) # Transparent
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 20), (200, 150)], fill='#3B82F6', outline='#1E3A8A', width=5)
            draw.rectangle([(0, 0), (80, 40)], fill='#3B82F6', outline='#1E3A8A', width=5)
            img.save(icon_path)
         except Exception as e:
             print(f"Could not create placeholder icon: {e}")

create_placeholder_images()

# --- Start the App ---
app = App(WINDOW_WIDTH, WINDOW_HEIGHT)
app.mainloop()
