# filename: check_files.py

import os

# Get the current working directory
cwd = os.getcwd()

# Get the list of all files in the current working directory
files = os.listdir(cwd)

# Print the current working directory and the list of files
print("Current working directory:", cwd)
print("Files in the current working directory:", files)
