import os

def install_requirements(root_dir):
    for subdir, dirs, files in os.walk(root_dir):
        if "requirements.txt" in files:
            os.chdir(subdir)  # Change to the directory with the file
            os.system("pip install -r requirements.txt")

root_dir = "/path/to/your/project/root"  # Replace with your project's root directory
install_requirements(root_dir)
