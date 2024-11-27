from pathlib import Path
from typing import Any, Dict, Union, Optional
import yaml
from pydantic import BaseModel, create_model

from ...lib import XNANOException, console


def convert_yaml_to_pydantic(path: Union[str, Path], verbose: bool = False) -> BaseModel:
    """
    Reads a YAML file and creates a Pydantic model from its contents.
    
    Args:
        path (Union[str, Path]): The path to the YAML file.
    
    Returns:
        BaseModel: An instance of a Pydantic model representing the YAML structure.
    """
    if isinstance(path, str):
        path = Path(path)

    if verbose:
        console.message(f"Converting YAML to Pydantic model from {path}")

    try:
        with open(path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)
            if verbose:
                console.message(f"YAML content loaded: {yaml_content}")
            model_class = create_pydantic_model(yaml_content, verbose=verbose)
            return model_class(**yaml_content)  # Instantiate the model with the loaded data
    except Exception as e:
        raise XNANOException(f"Error reading YAML {path}: {str(e)}")


def create_pydantic_model(data: Dict[str, Any], model_name: str = "DynamicModel", verbose: bool = False) -> BaseModel:
    """
    Recursively creates a Pydantic model from a dictionary.
    
    Args:
        data (Dict[str, Any]): The dictionary representation of the YAML content.
        model_name (str): The name of the Pydantic model to create.
    
    Returns:
        BaseModel: A Pydantic model representing the data structure.
    """
    fields = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            # Create a nested model for dictionaries without the DynamicModel_ prefix
            nested_model = create_pydantic_model(value, model_name=key, verbose=verbose)
            fields[key] = (nested_model, ...)  # Add nested model as a field
        else:
            # Handle primitive values
            if value is None:
                fields[key] = (Optional[Any], None)  # Treat null as Optional
            elif isinstance(value, str):
                fields[key] = (str, value)  # Use string type with actual value
            elif isinstance(value, int):
                fields[key] = (int, value)  # Use int type with actual value
            elif isinstance(value, float):
                fields[key] = (float, value)  # Use float type with actual value
            elif isinstance(value, bool):
                fields[key] = (bool, value)  # Use bool type with actual value
            else:
                fields[key] = (Any, value)  # Fallback to Any for other types

    model = create_model(model_name, **fields)
    return model


if __name__ == "__main__":
    model_instance = convert_yaml_to_pydantic("config.yaml", verbose=True)
    print(model_instance)  
    print(model_instance.model_dump())
