import os
import shutil
import json

# Load the JSON structure
with open('gen_json.json', 'r') as f:
    data = json.load(f)

# Define the root directory
root_dir = 'D:/Users/prabh/Downloads - Copy'

def create_folders_and_move_files(folder_structure, current_dir):
    """
    Recursively create folders and move files according to the folder structure
    """
    # Verify root directory exists
    if not os.path.exists(root_dir):
        print(f"Error: Root directory '{root_dir}' does not exist")
        return

    for item_name, contents in folder_structure.items():
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
                print(f"Error creating folder '{folder_path}': {e}")
                continue
        else:
            # Move files to current directory
            file_path = os.path.join(root_dir, item_name)
            new_location = os.path.join(current_dir, item_name)

            # Skip if source and destination are the same
            if os.path.abspath(file_path) == os.path.abspath(new_location):
                print(f"Skipping {item_name}: Source and destination are the same")
                continue

            try:
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    # Create parent directory if it doesn't exist
                    os.makedirs(os.path.dirname(new_location), exist_ok=True)
                    print(f"Moving file: {file_path} to {new_location}")
                    shutil.move(file_path, new_location)
                else:
                    print(f"Skipping: File not found or not accessible: {file_path}")
            except (OSError, shutil.Error) as e:
                print(f"Error moving file '{item_name}': {e}")

# Verify the JSON data is not empty
if not data:
    print("Error: No data found in JSON file")
else:
    # Process each top-level key in the data
    for key in data:
        print(f"\nProcessing category: {key}")
        try:
            create_folders_and_move_files(data[key], os.path.join(root_dir, key))
        except Exception as e:
            print(f"Error processing category '{key}': {e}")

print("\nOperation completed!")