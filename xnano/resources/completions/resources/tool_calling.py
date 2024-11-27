# tool calling helpers & converters


from pydantic import create_model, Field, BaseModel
import inspect
from typing import Any, Callable, Dict, Type, Union

from ....lib import XNANOException
from ....types.completions.tools import Tool


# tool generator
def generate_tool(client, tool_name: str, model: str) -> Tool:
    """Dynamically generate a tool function from its name"""

    function_prompt = f"""Create a Python function named '{tool_name}' that:
    
    1. Has typed arguments and return value
    2. Includes clear docstring
    3. Handles errors with try/except
    4. Places imports inside function body
    5. Implements core functionality implied by '{tool_name}'
    6. OPTS TO USING STANDARD PYTHON LIBRARIES UNLESS SPECIFICALLY REQUESTED
    """

    from ...generators.code_generators import generate_code

    # Use coder to generate the implementation
    generated_code = generate_code(
        instructions=function_prompt,
        model=model,
        temperature=0.2,
        client=client,
        verbose=client.verbose,
        return_code=True,
        progress_bar=False,
    )

    # Create function object from code
    namespace = {}
    try:
        exec(generated_code, namespace)
        generated_function = namespace[tool_name]
    except Exception as e:
        raise ValueError(f"Failed to create function object for {tool_name}: {str(e)}")

    # Create and return a Tool instance
    tool = Tool(
        name=get_function_name(generated_function),
        function=generated_function,
        description=get_function_description(generated_function),
        arguments=get_function_arguments(generated_function),
        formatted_function=convert_to_openai_tool(generated_function),
    )

    return tool


# convert to tool model
def convert_to_tool(function: Union[Callable, Type[BaseModel], Dict[str, Any]]) -> Tool:
    """
    Builds a raw function/class into a CompletionsTool.

    Args:
        function (Union[Callable, Type[BaseModel], Dict[str, Any]]): The function/class to convert.

    Returns:
        CompletionsTool: The CompletionsTool.
    """

    # setup tool
    tool = Tool(function=function)

    try:
        # format tool
        tool.formatted_function = convert_to_openai_tool(function)
    except Exception as e:
        raise XNANOException(f"Failed to convert tool: {e}")

    try:
        tool.name = get_function_name(function)
        tool.description = get_function_description(function)
        tool.arguments = get_function_arguments(function)
    except Exception as e:
        raise XNANOException(f"Failed to format tool: {e}")

    return tool


# convert to openai tool
def convert_to_openai_tool(
    function: Union[Dict[str, Any], Type[BaseModel], Callable],
) -> Dict[str, Any]:
    """Convert a raw function/class to an OpenAI tool.

    Examples:
        >>> convert_to_openai_tool(lambda x: x + 1)
        >>> convert_to_openai_tool(MyModel)
        >>> convert_to_openai_tool({"name": "my_tool", "description": "my tool", "function": lambda x: x + 1})

    Args:
        function (Union[Dict[str, Any], Type[BaseModel], Callable]): The function/class to convert.

    Returns:
        Dict[str, Any]: The OpenAI tool.
    """
    from openai import pydantic_function_tool

    if isinstance(function, dict):
        # If it's already a dictionary, assume it's in the correct format
        return function
    elif isinstance(function, type) and issubclass(function, BaseModel):
        # If it's a Pydantic model, use pydantic_function_tool directly
        return pydantic_function_tool(function)
    elif callable(function):
        # If it's a callable, convert it to a Pydantic model first
        pydantic_model = create_pydantic_model_from_function(function)
        return pydantic_function_tool(pydantic_model)
    else:
        raise ValueError(f"Unsupported function type: {type(function)}")


# create pydantic model from function
def create_pydantic_model_from_function(function: Callable) -> Type[BaseModel]:
    """Create a Pydantic model from a Python function.

    Args:
        function (Callable): The function to convert.

    Returns:
        Type[BaseModel]: The Pydantic model.
    """
    signature = inspect.signature(function)
    fields = {}
    for name, param in signature.parameters.items():
        annotation = (
            param.annotation if param.annotation != inspect.Parameter.empty else Any
        )
        default = ... if param.default == inspect.Parameter.empty else param.default
        fields[name] = (annotation, Field(default=default))

    # Use the original function name for the model
    model = create_model(function.__name__, **fields)
    model.__doc__ = function.__doc__ or ""

    # Store the original function as an attribute
    model._original_function = function

    return model


# get function name helper
def get_function_name(
    function: Union[Callable, Type[BaseModel], Dict[str, Any]],
) -> str:
    """Get the name of a function."""

    # if in callable format
    if callable(function):
        return function.__name__
    # if in model format
    elif isinstance(function, type) and issubclass(function, BaseModel):
        return function.__name__
    # if already openai dict
    elif isinstance(function, dict):
        return function.get("name", None)
    else:
        raise ValueError(f"Unsupported function type: {type(function)}")


# get function description helper
def get_function_description(
    function: Union[Callable, Type[BaseModel], Dict[str, Any]],
) -> str:
    """Get the description of a function

    Args:
        function (Union[Callable, Type[BaseModel], Dict[str, Any]]): The function to get the description of.

    Returns:
        str: The description of the function.
    """
    if isinstance(function, dict):
        return function.get("description", None)
    else:
        return function.__doc__


# get function arguments helper
def get_function_arguments(
    function: Union[Callable, Type[BaseModel], Dict[str, Any]],
) -> Dict[str, Any]:
    """Get the arguments of a function.

    Args:
        function (Union[Callable, Type[BaseModel], Dict[str, Any]]): The function to get the arguments of.

    Returns:
        Dict[str, Any]: The arguments of the function.
    """
    # if in callable format
    if callable(function):
        return inspect.signature(function).parameters
    # if in model format
    elif isinstance(function, type) and issubclass(function, BaseModel):
        return function.model_fields
    else:
        raise ValueError(f"Unsupported function type: {type(function)}")


if __name__ == "__main__":
    # Example usage of get_function_name
    def example_function(x):
        return x + 1

    class ExampleModel(BaseModel):
        field: int

    example_dict = {
        "name": "example_dict",
        "description": "This is an example dictionary",
    }

    print(get_function_name(example_function))  # Output: example_function
    print(get_function_name(ExampleModel))  # Output: ExampleModel
    print(get_function_name(example_dict))  # Output: example_dict

    # Example usage of get_function_description
    def example_function_with_doc(x):
        """This is an example function with a docstring."""
        return x + 1

    example_dict_with_description = {
        "name": "example_dict",
        "description": "This is an example dictionary with a description",
    }

    print(
        get_function_description(example_function_with_doc)
    )  # Output: This is an example function with a docstring.
    print(
        get_function_description(ExampleModel)
    )  # Output: None (assuming BaseModel does not have a docstring)
    print(
        get_function_description(example_dict_with_description)
    )  # Output: This is an example dictionary with a description

    # Example usage of get_function_arguments
    def example_function_with_args(a, b, c=3):
        return a + b + c

    class ExampleModelWithFields(BaseModel):
        field1: int
        field2: str

    print(
        get_function_arguments(example_function_with_args)
    )  # Output: OrderedDict([('a', <Parameter "a">), ('b', <Parameter "b">), ('c', <Parameter "c=3">)])
    print(
        get_function_arguments(ExampleModelWithFields)
    )  # Output: {'field1': <FieldInfo>, 'field2': <FieldInfo>}
