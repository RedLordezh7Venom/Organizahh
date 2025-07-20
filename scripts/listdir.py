import os

def list_files_and_folders(directory):
    return os.listdir(directory)

# Example directory
if __name__ == '__main__':
    directory = "D:/Users/prabh/Downloads - Copy"

    files_and_folders = list_files_and_folders(directory)
    print(files_and_folders)
    sum = 0
    for files in files_and_folders:
        sum+=(len(files))

    print(sum)