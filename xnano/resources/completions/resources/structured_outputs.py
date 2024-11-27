# llxm.structured_outputs
# converter & helper methods for structured outputs

from pydantic import BaseModel, create_model, Field
from typing import Type, Union, List, Optional

from ....lib import XNANOException


# HACK
# HACK
def make_nice_with_instructor(messages: list) -> list[dict[str, str]]:
    formatted_messages = []
    tool_output_map = {}

    # First pass: Collect tool outputs
    for message in messages:
        if message["role"] == "tool":
            tool_call_id = message.get("tool_call_id")
            tool_output = message.get("content", "unknown output")
            if tool_call_id:
                tool_output_map[tool_call_id] = tool_output

    # Second pass: Format messages
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                tool_name = tool_call.get("function", {}).get("name", "unknown tool")
                tool_args = tool_call.get("function", {}).get(
                    "arguments", "unknown arguments"
                )
                tool_call_id = tool_call.get("id")
                tool_output = tool_output_map.get(tool_call_id, "unknown output")
                formatted_messages.append(
                    {
                        "role": "assistant",
                        "content": f"I executed the {tool_name} tool with the arguments {tool_args} and got the following output: {tool_output}.",
                    }
                )
        elif message["role"] != "tool":  # Skip messages with the role 'tool'
            formatted_messages.append(message)

    if formatted_messages and formatted_messages[-1]["role"] != "user":
        formatted_messages.append({"role": "user", "content": "Proceed."})

    return formatted_messages


# converter
def handle_response_model(
    response_model: Union[Type[BaseModel], Type, str, List[str]],
) -> Type[BaseModel]:
    """
    Takes in a pydantic model (type) or a type, or a string or list of strings;
    if it's already a pydantic model, returns the model; otherwise uses our functions to build, then returns.

    Args:
        response_model (Union[Type[BaseModel], Type, str, List[str]]): The input type to process.

    Returns:
        Type[BaseModel]: The pydantic model.
    """
    try:
        if isinstance(response_model, type) and issubclass(response_model, BaseModel):
            return response_model
        elif isinstance(response_model, type):
            return create_response_model(response_model)
        elif isinstance(response_model, (str, list)):
            # New logic to handle string with type annotations
            if isinstance(response_model, str):
                # Check for type annotation in a single string
                if ":" in response_model:
                    name, type_annotation = response_model.split(":", 1)
                    return create_model(
                        "Response",
                        **{name.strip(): (eval(type_annotation.strip()), ...)},
                    )
                else:
                    return create_dynamic_response_model([response_model])
            elif isinstance(response_model, list):
                fields = {}
                for item in response_model:
                    if isinstance(item, str):
                        # Check for type annotation
                        if ":" in item:
                            name, type_annotation = item.split(":", 1)
                            fields[name.strip()] = (eval(type_annotation.strip()), ...)
                        else:
                            fields[item] = (str, ...)
                    else:
                        raise ValueError(
                            "List elements must be strings or lists of strings."
                        )
                return create_model("Response", **fields)
            else:
                raise ValueError(
                    "Input must be a string or a list of strings or nested lists."
                )
        else:
            raise ValueError(
                "Input for [bold]'response_model'[/bold] must be a pydantic model, a type, a string, or a list of strings."
            )
    except Exception as e:
        raise XNANOException(f"Failed to get or create response model: {e}")


def create_response_model(response_model: Type) -> Type[BaseModel]:
    """
    Creates a pydantic model with a single field 'response' of the given type.

    Args:
        response_model (Type): The type of the 'response' field.

    Returns:
        Type[BaseModel]: The created pydantic model.
    """
    return create_model("Response", response=(response_model, ...))


def get_empty_fields(model: Union[BaseModel, Type[BaseModel]]) -> List[str]:
    """
    Returns a list of field names that have empty values in the given pydantic model.
    Empty values are considered to be None, empty string, empty list, empty dict, or empty set.
    Works with both model instances and model classes.

    Args:
        model (Union[BaseModel, Type[BaseModel]]): The pydantic model instance or class to check for empty fields.

    Returns:
        List[str]: List of field names that have empty values.
    """
    empty_fields = []

    # If model is a class, get fields from model_fields
    if isinstance(model, type):
        return list(model.model_fields.keys())

    # If model is an instance, check values
    model_data = model.model_dump()
    for field_name, value in model_data.items():
        if value in (None, "", [], {}, set()):
            empty_fields.append(field_name)

    return empty_fields


def create_patch_model(
    response_model_instance: Union[BaseModel, Type[BaseModel]],
    fields: Optional[List[str]] = None,
) -> Type[BaseModel]:
    """
    Creates a pydantic model with the same name as the input response_model_instance,
    but only includes the selected fields if provided, otherwise includes all fields.

    Args:
        response_model_instance (BaseModel): The input pydantic model instance.
        fields (Optional[List[str]]): The list of field names to include in the model.

    Returns:
        Type[BaseModel]: The created pydantic model with the selected fields.
    """
    if fields is not None:
        # Only include specified fields
        selected_fields = {
            field_name: (
                response_model_instance.model_fields[field_name].annotation,
                ...,
            )
            for field_name in fields
            if field_name in response_model_instance.model_fields
        }
    else:
        # Include all empty fields
        selected_fields = {
            field_name: (field.annotation, ...)
            for field_name, field in response_model_instance.model_fields.items()
            if response_model_instance.__dict__.get(field_name)
            in (None, "", [], {}, set())
        }

    model_name = (
        response_model_instance.__class__.__name__
        if isinstance(response_model_instance, BaseModel)
        else response_model_instance.__name__
    )
    if selected_fields:
        return create_model(f"{model_name}Patch", **selected_fields)
    return response_model_instance.__class__


def merge_models(x: BaseModel, y: BaseModel) -> BaseModel:
    """
    Merges two pydantic models with the same fields, filling empty fields in x with values from y.

    Args:
        x (BaseModel): The first pydantic model.
        y (BaseModel): The second pydantic model.

    Returns:
        BaseModel: The merged pydantic model with empty fields filled.
    """
    try:
        # Create a copy of x and update with y's fields
        if isinstance(x, type):
            # If x is a BaseModel class, instantiate it with default values
            merged = x(**{field: None for field in x.model_fields.keys()}).model_copy()
        else:
            merged = x.model_copy()

        merged.model_update(y.model_dump(exclude_unset=True))
        return merged

    except Exception as e:
        raise XNANOException(f"Failed to merge models: {e}")


def create_dynamic_response_model(
    response_model: Union[str, List[Union[str, List[str]]]],
) -> Type[BaseModel]:
    """
    Creates a pydantic model with fields based on the input string or list of strings.
    Supports nested lists to create nested pydantic models.

    Args:
        response_model (Union[str, List[Union[str, List[str]]]]): A string or a list of strings or nested lists representing the field names.

    Returns:
        Type[BaseModel]: The created pydantic model.
    """
    try:
        if isinstance(response_model, str):
            return create_model("Response", **{response_model: (str, ...)})
        elif isinstance(response_model, list):
            fields = {}
            for name in response_model:
                if isinstance(name, str):
                    fields[name] = (str, ...)
                elif isinstance(name, list):
                    nested_model = create_dynamic_response_model(name)
                    fields[f"nested_{response_model.index(name)}"] = (nested_model, ...)
                else:
                    raise ValueError(
                        "List elements must be strings or lists of strings."
                    )
            return create_model("Response", **fields)
        else:
            raise ValueError(
                "Input must be a string or a list of strings or nested lists."
            )
    except Exception as e:
        raise XNANOException(f"Failed to create dynamic response model: {e}")


def check_if_model_instantiated(model: BaseModel) -> bool:
    """
    Checks if a Pydantic model instance has been instantiated with any non-default values.

    Args:
        model (BaseModel): The Pydantic model instance to check.

    Returns:
        bool: True if the model has been instantiated with any non-default values, False otherwise.
    """
    try:
        for field_name in model.model_fields.keys():
            if hasattr(model, field_name) and getattr(model, field_name) not in (
                None,
                "",
                [],
                {},
                set(),
            ):
                return True
        return False
    except Exception as e:
        raise XNANOException(f"Failed to check if model is instantiated: {e}")


def merge_new_values(
    model1: Union[BaseModel, Type[BaseModel]], model2: Union[BaseModel, dict]
) -> BaseModel:
    """
    Merges values from the second Pydantic model instance or dictionary into the first,
    updating only the specified fields.

    Args:
        model1 (BaseModel): The original Pydantic model instance.
        model2 (Union[BaseModel, dict]): The Pydantic model instance or dictionary containing new values to be merged.

    Returns:
        BaseModel: The updated Pydantic model instance with the new values merged.
    """
    try:
        # Get non-empty fields from model1
        model1_data = {
            k: v
            for k, v in model1.model_dump().items()
            if v not in (None, "", [], {}, set())
        }

        # Handle model2 being either a BaseModel or dict
        if isinstance(model2, dict):
            model2_data = model2
        elif isinstance(model2, BaseModel):
            model2_data = model2.model_dump()
        else:
            raise ValueError(
                "Second argument must be either a BaseModel or a dictionary."
            )

        # Merge model1's non-empty fields with model2's fields
        combined_data = {**model2_data, **model1_data}

        # Instantiate a new model1 with the combined data
        return model1.__class__(**combined_data)
    except Exception as e:
        raise XNANOException(f"Failed to merge new values into model: {e}")


# tests
if __name__ == "__main__":
    # Example 1: Merging two models with empty fields filled
    from pydantic import BaseModel

    class User(BaseModel):
        name: Optional[str] = None
        age: Optional[int] = None

    print(get_empty_fields(User(name="Alice")))

    print(create_patch_model(User(name="Alice", age=25), fields=["age"]))

    print(
        create_patch_model(
            User(name="Alice", age=25), fields=["name"]
        ).model_json_schema()
    )
