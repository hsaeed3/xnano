# llxm.utils
# random utility functions

import json
from pydantic import BaseModel, ValidationError, create_model
from ....lib import XNANOException

from ....types.completions.arguments import CompletionArguments
from typing import Any, Optional, Type


def parse_json_string_to_pydantic_model(
    json_string: str, response_format: Optional[BaseModel] = None
) -> BaseModel:
    """
    Parses a JSON string to a pydantic model

    Example:
        ```python
        json_string = '{"name": "John", "age": 30}'
        object = parse_json_string_to_pydantic_model(json_string)
        print(object.name)
        print(object.age)
        ```

    Args:
        json_string (str): The JSON string to parse
        response_format (Optional[BaseModel]): The response format to convert the JSON string to

    Returns:
        BaseModel: The parsed pydantic model
    """

    try:
        # parse the json string
        json_content = json.loads(json_string)

        # dynamically create a pydantic model from the json content
        dynamic_model = create_model(
            "ResponseModel", **{k: (type(v), ...) for k, v in json_content.items()}
        )
        dynamic_model = dynamic_model(**json_content)

        # if response format is provided, convert the dynamic model to the response format
        if response_format:
            dynamic_model = create_model(
                response_format.__name__,
                **{k: (type(v), ...) for k, v in json_content.items()},
            )
            dynamic_model = dynamic_model(**json_content)

        return dynamic_model

    except json.JSONDecodeError as e:
        raise XNANOException(f"Invalid JSON string: {e}")
    except ValidationError as e:
        raise XNANOException(f"Validation error: {e}")
    except Exception as e:
        raise XNANOException(f"Failed to parse JSON string to pydantic model: {e}")


# collect completion args
def collect_completion_args(args: dict[str, Any]) -> CompletionArguments:
    """
    Builds arguments into a CompletionArguments object

    Args:
        args (dict[str, Any]): The arguments to build

    Returns:
        CompletionArguments: The built CompletionArguments object
    """

    try:
        # filter out arguments that are not in the CompletionArguments model
        valid_args = {
            k: v for k, v in args.items() if k in CompletionArguments.model_fields
        }

        # build the completion arguments
        completion_args = CompletionArguments(**valid_args)
    except ValidationError as e:
        raise XNANOException(
            f"Validation error while building completion arguments: {e}"
        )
    except Exception as e:
        raise XNANOException(f"Failed to build completion arguments: {e}")

    return completion_args


# build post request
def build_post_request(
    args: CompletionArguments, instructor: bool = False
) -> dict[str, Any]:
    """
    Filters and prepares the arguments for a post request.

    Args:
        args (CompletionArguments): The completion arguments.
        remove_list (list[str]): The list of argument names to remove.

    Returns:
        dict[str, Any]: The filtered and prepared arguments.
    """
    # Convert CompletionArguments to a dictionary
    args_dict = args.model_dump()

    # args for removal
    remove_list = ["context", "mode", "run_tools", "verbose"]

    if not instructor:
        remove_list.append("response_model")

    # Remove specified arguments
    for arg in remove_list:
        if arg in args_dict:
            del args_dict[arg]

    # Use the tool.formatted_function param from the args as the tool arg
    if args_dict.get("tools") is not None:
        args_dict["tools"] = [
            tool["formatted_function"]
            if isinstance(tool, dict)
            else tool.formatted_function
            for tool in args_dict["tools"]
        ]

    # If tools is None, remove parallel_tool_calls and tool_choice
    if args_dict.get("tools") is None:
        args_dict.pop("parallel_tool_calls", None)
        args_dict.pop("tool_choice", None)

    # remove everything else that is None
    args_dict = {k: v for k, v in args_dict.items() if v is not None}

    return args_dict


if __name__ == "__main__":
    json_string = '{"name": "John", "age": 30}'

    object = parse_json_string_to_pydantic_model(json_string)

    print(object.name)
    print(object.age)
