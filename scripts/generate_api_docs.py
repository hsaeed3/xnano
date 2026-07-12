"""scripts.generate_api_docs"""

import os
import pathlib
import tomlkit
from typing import Any, List, Dict, Union


def pretty_format_navigation(item: Any, indent: int = 0) -> str:
    """Format navigation item recursively to match the zensical.toml style."""
    if isinstance(item, str):
        return f'"{item}"'
    elif isinstance(item, dict):
        assert len(item) == 1
        key, value = list(item.items())[0]
        if isinstance(value, str):
            return f'{{"{key}" = "{value}"}}'
        elif isinstance(value, list):
            inner_indent = indent + 4
            formatted_items = []
            for sub_item in value:
                formatted_items.append(" " * inner_indent + pretty_format_navigation(sub_item, inner_indent))
            items_string = ",\n".join(formatted_items)
            if formatted_items:
                items_string += ","
            return f'{{ "{key}" = [\n{items_string}\n{" " * indent}]}}'
    elif isinstance(item, list):
        inner_indent = indent + 4
        formatted_items = []
        for sub_item in item:
            formatted_items.append(" " * inner_indent + pretty_format_navigation(sub_item, inner_indent))
        items_string = ",\n".join(formatted_items)
        if formatted_items:
            items_string += ","
        return f'[\n{items_string}\n{" " * indent}]'
    return str(item)


def replace_navigation_in_toml(toml_content: str, new_navigation_string: str) -> str:
    """Find and replace the nav list in the TOML content string."""
    start_index = toml_content.find("nav = [")
    if start_index == -1:
        raise ValueError("Could not find 'nav = [' in TOML content")
        
    open_bracket_index = toml_content.find("[", start_index)
    
    depth = 0
    close_bracket_index = -1
    for index in range(open_bracket_index, len(toml_content)):
        character = toml_content[index]
        if character == '[':
            depth += 1
        elif character == ']':
            depth -= 1
            if depth == 0:
                close_bracket_index = index
                break
                
    if close_bracket_index == -1:
        raise ValueError("Could not find matching closing bracket for 'nav'")
        
    prefix = toml_content[:start_index]
    suffix = toml_content[close_bracket_index + 1:]
    return prefix + new_navigation_string + suffix


def get_module_path(base_package_name: str, relative_path: pathlib.Path) -> str:
    """Get the full Python module import path for a given script relative path."""
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([base_package_name] + parts)


def get_navigation_tree(directory_path: pathlib.Path, docs_directory: pathlib.Path) -> List[Any]:
    """Build the navigation tree recursively based on generated markdown files."""
    items = []
    files = []
    subdirectories = []
    
    for path in directory_path.iterdir():
        if path.is_dir():
            subdirectories.append(path)
        elif path.is_file() and path.suffix == ".md":
            files.append(path)
            
    # Custom sorting for files
    def file_sort_key(path_item: pathlib.Path) -> tuple:
        name = path_item.stem
        if name == "xnano":
            return (0, "")
        if name == "xnano-core":
            return (1, "")
        if name == "__init__":
            return (2, "")
        if name == "__main__":
            return (3, "")
        return (4, name)
        
    # Custom sorting for subdirectories
    def dir_sort_key(path_item: pathlib.Path) -> tuple:
        name = path_item.name
        if name == "xnano":
            return (0, "")
        if name == "xnano-core":
            return (1, "")
        return (2, name)
        
    files.sort(key=file_sort_key)
    subdirectories.sort(key=dir_sort_key)
    
    for file_path in files:
        relative_to_docs = file_path.relative_to(docs_directory)
        items.append(str(relative_to_docs))
        
    for subdirectory in subdirectories:
        subdirectory_items = get_navigation_tree(subdirectory, docs_directory)
        if subdirectory_items:
            items.append({subdirectory.name: subdirectory_items})
            
    return items


def cleanup_existing_doc_files(api_directory: pathlib.Path) -> None:
    """Remove any __init__.md, __main__.md, or top-level xnano.md / xnano-core.md files recursively."""
    if not api_directory.exists():
        return
        
    # Delete top-level files from previous run if any
    for file_name in ("xnano.md", "xnano-core.md"):
        file_path = api_directory / file_name
        if file_path.exists():
            file_path.unlink()
            print(f"Cleaned up top-level: {file_path}")
            
    for root, _, files in os.walk(api_directory):
        for file_name in files:
            if file_name in ("__init__.md", "__main__.md"):
                file_path = pathlib.Path(root) / file_name
                file_path.unlink()
                print(f"Cleaned up: {file_path}")
                
    # Remove empty directories recursively
    def remove_empty_dirs(directory: pathlib.Path):
        for path in list(directory.iterdir()):
            if path.is_dir():
                remove_empty_dirs(path)
        if directory != api_directory and not list(directory.iterdir()):
            directory.rmdir()
            print(f"Removed empty directory: {directory}")
            
    remove_empty_dirs(api_directory)


def generate_api_documentation() -> None:
    """Auto-generate API doc files and update zensical.toml navigation."""
    base_directory = pathlib.Path("/Users/hammad/Development/xnano/xnano-main/xnano-docs")
    docs_directory = base_directory / "docs"
    api_directory = docs_directory / "api"
    
    # First, cleanup previous __init__.md and __main__.md files
    cleanup_existing_doc_files(api_directory)
    
    # Target directories to scan for .py files
    targets = [
        ("xnano", base_directory / "xnano", api_directory / "xnano"),
        ("xnano_core", base_directory / "xnano-core" / "python" / "xnano_core", api_directory / "xnano-core")
    ]
    
    created_count = 0
    updated_count = 0
    
    for package_name, source_directory, target_directory in targets:
        if not source_directory.exists():
            print(f"Source directory {source_directory} does not exist!")
            continue
            
        for root, _, files in os.walk(source_directory):
            for file_name in files:
                if file_name.endswith(".py"):
                    python_file_path = pathlib.Path(root) / file_name
                    
                    # Compute path relative to source directory
                    relative_path = python_file_path.relative_to(source_directory)
                    
                    # Handle special files
                    is_top_level = (relative_path == pathlib.Path("__init__.py"))
                    
                    if file_name == "__main__.py":
                        # Skip __main__.py completely
                        continue
                    elif file_name == "__init__.py":
                        if is_top_level:
                            # Map to xnano.md or xnano-core.md inside their respective subdirs
                            if package_name == "xnano":
                                markdown_file_path = target_directory / "xnano.md"
                            else:
                                markdown_file_path = target_directory / "xnano-core.md"
                            module_path = package_name
                        else:
                            # Skip nested __init__.py files
                            continue
                    else:
                        # Standard module
                        markdown_file_path = target_directory / relative_path.with_suffix(".md")
                        module_path = get_module_path(package_name, relative_path)
                        
                    # Ensure parent directories exist
                    markdown_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    content = f'---\ntitle: "{module_path}"\n---\n\n::: {module_path}\n'
                    
                    # Check if file needs to be created or overwritten
                    if not markdown_file_path.exists():
                        with open(markdown_file_path, "w") as f:
                            f.write(content)
                        print(f"Created: {markdown_file_path.relative_to(base_directory)}")
                        created_count += 1
                    else:
                        with open(markdown_file_path, "w") as f:
                            f.write(content)
                        updated_count += 1
                        
    print(f"Created {created_count} files, updated {updated_count} files.")
    
    # Now update zensical.toml
    zensical_toml_path = base_directory / "zensical.toml"
    if not zensical_toml_path.exists():
        print("zensical.toml not found!")
        return
        
    with open(zensical_toml_path, "r") as f:
        toml_content = f.read()
        
    document = tomlkit.parse(toml_content)
    
    # Build the new nav array
    existing_navigation = document["project"]["nav"]
    new_navigation = []
    
    # Keep non-API Reference items
    for item in existing_navigation:
        if isinstance(item, dict) and "API Reference" in item:
            continue
        new_navigation.append(item)
        
    # Build API Reference sub-navigation tree
    api_reference_navigation = get_navigation_tree(api_directory, docs_directory)
    
    api_reference_item = {
        "API Reference": api_reference_navigation
    }
    
    new_navigation.append(api_reference_item)
    
    # Format the new nav array using our custom pretty formatter
    new_navigation_string = "nav = " + pretty_format_navigation(new_navigation, indent=0)
    
    # Replace navigation section in the TOML file content
    updated_toml_content = replace_navigation_in_toml(toml_content, new_navigation_string)
    
    # Write back the updated zensical.toml
    with open(zensical_toml_path, "w") as f:
        f.write(updated_toml_content)
        
    print("Successfully updated navigation in zensical.toml")


if __name__ == "__main__":
    generate_api_documentation()
