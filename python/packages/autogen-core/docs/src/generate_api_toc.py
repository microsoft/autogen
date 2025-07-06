#!/usr/bin/env python3
"""
Script to automatically generate the API reference table of contents for AutoGen.

This script scans all packages and their modules to generate the toctree entries
for the API documentation index.md file.
"""

import os
from pathlib import Path
from typing import List, Dict, Set
import re


# Constants for package filtering and organization
DOCUMENTED_PACKAGES = ["autogen_core", "autogen_agentchat", "autogen_ext"]

PACKAGE_SECTIONS = {
    "autogen_agentchat": "AutoGen AgentChat",
    "autogen_core": "AutoGen Core", 
    "autogen_ext": "AutoGen Extensions"
}

# Exclusion patterns for submodules that are re-exported by parent modules
EXCLUSION_PATTERNS = [
    # task_centric_memory re-exports from memory_controller and utils
    (r'^autogen_ext\.experimental\.task_centric_memory\.memory_controller$', 
     'autogen_ext.experimental.task_centric_memory'),
    # utils package re-exports from utils.apprentice and other utils submodules
    (r'^autogen_ext\.experimental\.task_centric_memory\.utils\.apprentice$', 
     'autogen_ext.experimental.task_centric_memory.utils'),
    (r'^autogen_ext\.experimental\.task_centric_memory\.utils\.chat_completion_client_recorder$', 
     'autogen_ext.experimental.task_centric_memory.utils'),
    (r'^autogen_ext\.experimental\.task_centric_memory\.utils\.grader$', 
     'autogen_ext.experimental.task_centric_memory.utils'),
    (r'^autogen_ext\.experimental\.task_centric_memory\.utils\.page_logger$', 
     'autogen_ext.experimental.task_centric_memory.utils'),
    (r'^autogen_ext\.experimental\.task_centric_memory\.utils\.teachability$', 
     'autogen_ext.experimental.task_centric_memory.utils'),
]


def is_private_module(module_parts: List[str]) -> bool:
    """Check if any part of the module path indicates it's a private module."""
    return any(part.startswith('_') and part != '__init__' for part in module_parts)


def find_python_packages() -> List[Path]:
    """Find documented Python packages in the workspace."""
    packages_dir = Path(__file__).parent.parent.parent.parent.parent / "packages"
    python_packages = []
    
    for package_dir in packages_dir.iterdir():
        if package_dir.is_dir():
            # Check if this package is in our documented packages list
            package_name = package_dir.name.replace("-", "_")
            if package_name in DOCUMENTED_PACKAGES:
                src_dir = package_dir / "src"
                if src_dir.exists():
                    python_packages.append(src_dir)
    
    return python_packages


def get_module_hierarchy(package_root: Path) -> Dict[str, Set[str]]:
    """Get the module hierarchy for a package, filtering only documented packages."""
    modules: Dict[str, Set[str]] = {}
    
    for root, dirs, files in os.walk(package_root):
        # Skip __pycache__ and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('__pycache__') and not d.startswith('.')]
        
        root_path = Path(root)
        
        # Process Python files (excluding private modules)
        for file in files:
            if file.endswith('.py') and file != '__init__.py' and not file.startswith('_'):
                file_path = root_path / file
                module_path = file_path.relative_to(package_root)
                
                # Convert file path to module name
                module_parts = list(module_path.parts[:-1]) + [module_path.stem]
                
                if module_parts:
                    # Skip if any part of the module path is private
                    if is_private_module(module_parts):
                        continue
                        
                    module_name = '.'.join(module_parts)
                    package_name = module_parts[0]
                    
                    # Only include modules from documented packages
                    if package_name in DOCUMENTED_PACKAGES:
                        if package_name not in modules:
                            modules[package_name] = set()
                        
                        modules[package_name].add(module_name)
        
        # Also check for directories with __init__.py (packages, excluding private)
        for dir_name in dirs:
            if not dir_name.startswith('_'):  # Skip private directories
                dir_path = root_path / dir_name
                if (dir_path / '__init__.py').exists():
                    module_path = dir_path.relative_to(package_root)
                    module_parts = list(module_path.parts)
                    
                    if module_parts:
                        # Skip if any part of the module path is private
                        if is_private_module(module_parts):
                            continue
                            
                        module_name = '.'.join(module_parts)
                        package_name = module_parts[0]
                        
                        # Only include modules from documented packages
                        if package_name in DOCUMENTED_PACKAGES:
                            if package_name not in modules:
                                modules[package_name] = set()
                            
                            modules[package_name].add(module_name)
    
    return modules


def should_exclude_submodule(module_name: str, all_modules: Set[str]) -> bool:
    """Check if a submodule should be excluded to avoid duplicate documentation."""
    for pattern, parent_module in EXCLUSION_PATTERNS:
        if re.match(pattern, module_name) and parent_module in all_modules:
            return True
    
    return False


def clean_rst_files(reference_dir: Path) -> None:
    """Clean existing RST files to ensure fresh generation."""
    python_ref_dir = reference_dir / "python"
    if python_ref_dir.exists():
        print("🧹 Cleaning existing .rst files...")
        rst_files = list(python_ref_dir.glob("*.rst"))
        for rst_file in rst_files:
            rst_file.unlink()
        print(f"   Removed {len(rst_files)} existing .rst files")


def generate_rst_files(package_roots: List[Path], reference_dir: Path) -> Set[str]:
    """Generate .rst files for all modules found in the packages."""
    python_ref_dir = reference_dir / "python"
    python_ref_dir.mkdir(exist_ok=True, parents=True)
    
    # Clean existing RST files first
    clean_rst_files(reference_dir)
    
    generated_files = set()
    all_module_names = set()
    
    # First pass: collect all module names
    for package_root in package_roots:
        modules = get_module_hierarchy(package_root)
        for package_name, module_set in modules.items():
            all_module_names.update(module_set)
    
    # Second pass: generate RST files, excluding problematic submodules
    for package_root in package_roots:
        modules = get_module_hierarchy(package_root)
        
        for package_name, module_set in modules.items():
            for module_name in module_set:
                # Skip modules that would cause duplicate documentation
                if should_exclude_submodule(module_name, all_module_names):
                    print(f"   Skipping {module_name} (re-exported by parent)")
                    continue
                
                # Use the proper RST filename pattern (keep dots for submodules)
                rst_filename = module_name + '.rst'
                rst_path = python_ref_dir / rst_filename
                
                # Generate .rst content with proper title formatting
                # Title should use dots as separators, but escape underscores for RST
                title = module_name.replace('_', r'\_')
                underline = '=' * len(title)  # Underline matches title length
                
                rst_content = f"""{title}
{underline}

.. automodule:: {module_name}
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
"""
                
                # Write the .rst file
                with open(rst_path, 'w') as f:
                    f.write(rst_content)
                
                generated_files.add(module_name)
    
    return generated_files


def generate_toctree_from_rst_files(reference_dir: Path) -> Dict[str, List[str]]:
    """Generate toctree entries directly from existing .rst files."""
    # Initialize sections using constants
    toctree_sections: Dict[str, List[str]] = {section: [] for section in PACKAGE_SECTIONS.values()}
    
    python_ref_dir = reference_dir / "python"
    if not python_ref_dir.exists():
        return toctree_sections
    
    # Collect modules by package using constants
    modules_by_section: Dict[str, List[str]] = {section: [] for section in PACKAGE_SECTIONS.values()}
    
    # Get all .rst files and organize them by package
    for rst_file in python_ref_dir.glob("*.rst"):
        module_name = rst_file.stem  # filename without .rst extension
        
        # Find which documented package this module belongs to
        for package_prefix, section_name in PACKAGE_SECTIONS.items():
            if module_name.startswith(package_prefix):
                modules_by_section[section_name].append(module_name)
                break
    
    # Sort modules so parent modules come before child modules
    def sort_modules_hierarchically(modules):
        """Sort modules so that parent modules come before child modules."""
        return sorted(modules, key=lambda x: (x.count('.'), x))
    
    # Apply hierarchical sorting and convert to rst paths
    for section_name, modules in modules_by_section.items():
        toctree_sections[section_name] = [f"python/{m}" for m in sort_modules_hierarchically(modules)]
    
    return toctree_sections


def generate_index_content(toctree_sections: Dict[str, List[str]]) -> str:
    """Generate the complete index.md content with automatic toctrees."""
    
    content = """---
myst:
  html_meta:
    "description lang=en": |
      AutoGen is a community-driven project. Learn how to get involved, contribute, and connect with the community.
---

# API Reference

"""
    
    for section_name, modules in toctree_sections.items():
        if modules:  # Only add section if it has modules
            content += f"""```{{toctree}}
:caption: {section_name}
:maxdepth: 2

"""
            for module in modules:
                content += f"{module}\n"
            content += "```\n\n"
    
    return content


def main():
    """Main function to generate the API documentation index."""
    script_dir = Path(__file__).parent
    reference_dir = script_dir / "reference"
    index_file = reference_dir / "index.md"
    
    print("🔍 Scanning Python packages...")
    package_roots = find_python_packages()
    
    all_modules = {}
    for package_root in package_roots:
        print(f"   📦 Scanning {package_root}")
        modules = get_module_hierarchy(package_root)
        all_modules.update(modules)
    
    print("🏗️  Generating .rst files for all discovered modules...")
    generated_files = generate_rst_files(package_roots, reference_dir)
    print(f"   Generated {len(generated_files)} .rst files")
    
    print("📝 Generating toctree entries from .rst files...")
    toctree_sections = generate_toctree_from_rst_files(reference_dir)
    
    for section, modules in toctree_sections.items():
        print(f"   {section}: {len(modules)} modules")
    
    print("✍️  Writing index.md...")
    content = generate_index_content(toctree_sections)
    
    with open(index_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Generated API documentation index at {index_file}")
    print("\n📖 Summary:")
    total_modules = sum(len(modules) for modules in toctree_sections.values())
    print(f"   Total modules documented: {total_modules}")
    
    for section, modules in toctree_sections.items():
        if modules:
            print(f"   {section}: {len(modules)} modules")


if __name__ == "__main__":
    main()
