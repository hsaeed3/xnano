# __Structured Outputs__

Although [`LiteLLM`](https://github.com/BerriAI/litellm) supports structured outputs through the use of the `response_format` parameter, I've always been a very heavy user of the [`Instructor`](https://github.com/instructor-ai/instructor) library, for its rich functionality, so [`xnano`] defaults to using [`Instructor`](https://github.com/instructor-ai/instructor) for all __non-batch__ structured outputs.

## __Generating Completions with Structured Outputs__

### __Using `Pydantic` Models__

Let's start with a simple example, utilizing instructor to return a `Pydantic` model.

```python
from xnano import completion
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

response = completion(
    "Extract john is 20 years old",
    response_model = User
)

print(response)
```

```bash
User(name='john', age=20)
```

## __Using Strings & Lists as Response Models__

An `ease-of-use` feature added to creating structured outputs with `completion` is the ability to input strings and lists as the `response_model` parameter, and `xnano` will automatically convert them into the correct `Pydantic` models.

Defining response models using strings follows the simple schema below:

```
"field_name: field_type"
```

so, for example

```
"name: str"
```

Any fields not given a type will be automatically converted to `str` types. Let's view an example of this in action.

```python
from xnano import completion

response = completion(
    "Extract john is 20 years old",
    response_model = ["name", "age: int"]
)

print(response)
```

```bash
Response(name='john', age=20)
```

## __Using Standard Types as Response Models__

The simplest way to generate a structured output is to use standard types as the `response_model` parameter. This feature currently does not support lists of types, so currently only a single 'field' or generation is created.

If a `response_model` is given as a type, the output will itself only be that type as well.

```python
from xnano import completion

response = completion(
    "Extract john is 20 years old",
    response_model = int
)

print(response)
```

```bash
20
```

## __Changing the Instructor Mode__

One of the main features of [`Instructor`](https://github.com/instructor-ai/instructor) is the ability to change the mode in which it generated and parses structured outputs. This can be done by setting the [`instructor_mode`]("previously `mode`") parameter. The various modes are available to use as strings, and will be properly interpreted by the library.

To view the different modes available, please refer to [`Instructor Mode - GitHub`](https://github.com/instructor-ai/instructor/blob/main/instructor/mode.py). Modes are also visible as type hints, when setting the `instructor_mode` parameter.

The standard mode when generating structured outputs is `tool_use`. Let's view an example that shows the difference between instructor's modes.

### __Using the Default Mode__

```python
import xnano as x
from pydantic import BaseModel

class Capital(BaseModel):
    capital: str

response = x.completion(
    "What is the capital of France?",

    # Instructor Default Mode
    instructor_mode = "tool_call",
    response_format = Capital
)

print(response)
```

```bash
# Output

Capital(capital='Paris')
```

### __Changing the Mode__

Now, let's change the mode to `markdown_json_mode`, and see the difference in the output.

```python
response = x.completion(
    "What is the capital of France?",

    # Instructor Default Mode
    instructor_mode = "markdown_json_mode",
    response_format = Capital
)
```

```bash
Capital(capital='Paris')
```

Uhh.... what happened? It seems the responses are the exact same. The difference is in the way the responses are generated and parsed, let's view the requests made to the LLM to really see the difference.

<details>
<summary>Mode : "tool_call"</summary>

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    }
  ],
  "model": "gpt-4o-mini",
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": {
        "properties": {
          "capital": {
            "title": "Capital",
            "type": "string"
          }
        },
        "required": [
          "capital"
        ],
        "title": "Capital",
        "type": "object",
        "additionalProperties": false
      },
      "name": "Capital",
      "strict": true
    }
  },
  "tool_choice": {
    "type": "function",
    "function": {
      "name": "Capital"
    }
  },
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "Capital",
        "description": "Correctly extracted `Capital` with all the required parameters with correct types",
        "parameters": {
          "properties": {
            "capital": {
              "title": "Capital",
              "type": "string"
            }
          },
          "required": [
            "capital"
          ],
          "type": "object"
        }
      }
    }
  ]
}
```

</details>

<details>
<summary>Mode : "markdown_json_mode"</summary>

```json
{
  "messages": [
    {
      "role": "system",
      "content": "\n        As a genius expert, your task is to understand the content and provide\n        the parsed objects in json that match the following json_schema:\n\n\n        {\n  \"properties\": {\n    \"capital\": {\n      \"title\": \"Capital\",\n      \"type\": \"string\"\n    }\n  },\n  \"required\": [\n    \"capital\"\n  ],\n  \"title\": \"Capital\",\n  \"type\": \"object\"\n}\n\n        Make sure to return an instance of the JSON, not the schema itself\n"
    },
    {
      "role": "user",
      "content": "What is the capital of France?\n\nReturn the correct JSON response within a ```json codeblock. not the JSON_SCHEMA"
    }
  ],
  "model": "gpt-4o-mini",
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": {
        "properties": {
          "capital": {
            "title": "Capital",
            "type": "string"
          }
        },
        "required": [
          "capital"
        ],
        "title": "Capital",
        "type": "object",
        "additionalProperties": false
      },
      "name": "Capital",
      "strict": true
    }
  }
}
```

</details>

As you can see here, there is a massive difference in the requests made to the LLM, this example was incredibly simple, but this difference will become more apparent when generating more complex structured outputs; or using different LLM providers & models.