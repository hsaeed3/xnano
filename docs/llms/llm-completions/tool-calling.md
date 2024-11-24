# Tool Calling

[`Tool Calling`](#) is extended in `xnano completions`, through which tools are easier to use, and an introduction to `Agent` like behavior through automatic tool execution.

## Generating a Tool Call

Let's start with a simple example. Let's create a tool that "searches" the web for the latest headlines, and query the LLM with it.

```python
from xnano import completion

# define a tool
def search_news(query: str) -> str:
    """
    Search the web for the latest headlines.
    """
    return "the stock market has gone up 1000% today"

# generate a completion with the tool
response = completion(
    "What are the latest headlines in the stock market?",

    # pass the tool
    tools=[search_news],

    # all standard tool calling arguments are supported
    tool_choice = "auto",
    parallel_tool_calls=True
)

# print the tool calls
print(response.choices[0].message.tool_calls)
```

<details>
<summary>Output</summary>

```bash
[
    ChatCompletionMessageToolCall(
        function=Function(
            arguments='{"query":"latest headlines in the stock 
market"}',
            name='search_news'
        ),
        id='call_CjV5jtq7hp14eGRmu0HTSjvj',
        type='function'
    )
]
```
</details>

<br/>

## Using Pydantic Models as Tools

If our goal is only to retrieve a `tool call` itself, a good way to do this is to use a `Pydantic` model as a tool. This provides proper typing to the tool call arguments.

```python
from xnano import completion
from pydantic import BaseModel

# define a tool
class SearchWeb(BaseModel):
    """
    Search the web for the latest headlines.
    """

    query: str
    num_results: int


# generate a completion with the tool
response = completion(
    "What are the latest headlines in the stock market?",

    model="ollama/llama3.2:3b",
    tools=[SearchWeb]
)
```

Now, we can validate the tool call and print the results.

```python
import json

# validate the tool call
tool_calls = response.choices[0].message.tool_calls
arguments = json.loads(tool_calls[0].function.arguments)

arguments = SearchWeb(**arguments)

# print the results
print(arguments)
```

```bash
SearchWeb(
    query='latest headlines in the stock market',
    num_results=5
)
```

<br/>

## Parallel Tool Calls

Generating tool calls in parallel is supported through the `parallel_tool_calls` argument, and follows the universal format.

```python
from xnano import completion

def get_favorite_color() -> str:
    """
    Get the user's favorite color.
    """
    return "blue"

def get_favorite_food() -> str:
    """
    Get the user's favorite food.
    """
    return "pizza"


# generate a completion with the tools
response = completion(
    "What is my favorite color and food?",
    tools=[get_favorite_color, get_favorite_food],
    parallel_tool_calls=True
)

# print the results
print(response.choices[0].tool_calls)
```

<details>
<summary>Output</summary>

```bash
[
    ChatCompletionMessageToolCall(
        function=Function(
            arguments='{}',
            name='get_favorite_color'
        ),
        id='call_jhAuarf80kdh16mZjJJW5PyD',
        type='function'
    ),
    ChatCompletionMessageToolCall(
        function=Function(
            arguments='{}',
            name='get_favorite_food'
        ),
        id='call_rRQf2RBZ3VgVt4JYX8xOtPNO',
        type='function'
    )
]
```
</details>
