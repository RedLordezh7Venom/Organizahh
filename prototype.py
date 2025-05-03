import os
import shutil
import json

# Load the backbone.json structure
with open('back2.json', 'r') as f:
    data = json.load(f)

# Define the root directory
root_dir = f'D:/Users/prabh/Downloadscopy'

def create_folders_and_move_files(folder_structure, current_dir):
    for item_name, contents in folder_structure.items():
        if isinstance(contents, dict):
            # Create folder path
            folder_path = os.path.join(current_dir, item_name)
            
            # Create the folder if it doesn't exist
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Created folder: {folder_path}")
            
            # Recursively process subfolders and their contents
            create_folders_and_move_files(contents, folder_path)
        else:
            # Move files to current directory
            file_path = os.path.join(root_dir, item_name)
            if os.path.exists(file_path):
                new_location = os.path.join(current_dir, item_name)
                print(f"Moving file: {file_path} to {new_location}")
                shutil.move(file_path, new_location)
            else:
                print(f"File not found: {file_path}")

# Call the function to create folders and move files
create_folders_and_move_files(data[root_dir], root_dir)

print("Folders created and files moved successfully!")



