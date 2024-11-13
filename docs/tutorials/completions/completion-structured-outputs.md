# **LLM Completions with Structured Outputs**

The `xnano` library uses ___[Instructor](https://github.com/jxnl/instructor)___ to generate structured outputs from LLM completions. 

The `completion` function builds in two arguments that directly implement instructor if given:

- ___`response_model`___ : the output schema or model
- ___`mode`___ : the generation & parsing mode used by instructor

The ___`response_model`___ argument follows the `Instructor` pattern, and is able to taken the default `Pydantic` model input, as well as strings, lists of strings, generic types _(such as str, int, etc.)_ & dictionaries. 

The ___`mode`___ argument is incredibly powerful, and although optional, it is still directly used by instructor. Refer to [Instructor Mode - Github](https://github.com/instructor-ai/instructor/blob/main/instructor/mode.py) for the various modes available.

## **Using Pydantic Models for Structured Outputs**

<summary>Instructor Pydantic Completion</summary>

```python
from pydantic import BaseModel
from xnano import completion

# define a pydantic model
class Extraction(BaseModel):
    name : str
    age : int

# generate a completion with a structured output
response = completion(
    "Extract john is 25 years old",
    response_model = Extraction
)

# print the response content
print(response.name)
print(response.age)
```

```
# Output
john
25
```

<summary>Changing the Instructor Mode</summary>

To change the instructor mode, simply pass the `mode` argument to the `completion` function.

```python
completion(
    "Extract john is 25 years old",
    response_model = Extraction,
    mode = "markdown_json_mode",    # mode == "tool_call" by default
)
```

## **Using Strings as Response Models**

An easier way to generate structured outputs is to use strings as response models. This is useful for getting structured outputs much quicker.

<summary>String Response Models</summary>

```python
response = completion(
    "Extract john is 25 years old",
    response_model = ["name", "age : int"]
)

print(response)
```

```
# output
Response(name='john', age=25)
```