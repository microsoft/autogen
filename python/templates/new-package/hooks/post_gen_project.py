import os
import shutil
from pathlib import Path
import tomli_w
import tomllib

source_dir = os.getcwd()
target_dir = "{{ cookiecutter.__final_destination }}"

shutil.move(source_dir, target_dir)

THIS_FILE_DIR = Path(__file__).parent

# Add the package to the workspace def

workspace_def_path = THIS_FILE_DIR / ".." / ".." / ".." / "pyproject.toml"

with workspace_def_path.open("rb") as f:
    config = tomllib.load(f)

config["tool"]["uv"]["sources"]["{{ cookiecutter.package_name }}"] = {"workspace": True}

with workspace_def_path.open("wb") as f:
    tomli_w.dump(config, f)
