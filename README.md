# xnano
build extremely 'nano' llm workflows

### Install with pip
```bash
pip install xnano
```

---

## Examples

### The most useful completion function any llm library provides

__xnano__ is built on top of one robust extension of the base litellm completion function. The following examples will show it's various capabilities.

**Starting with a simple, single completion**

```python
from xnano import completion

response = completion("who won the 2024 euro cup final?")

# response is a standard chatcompletion object
print(response.choices[0].message.content)
```

```bash
# output
I'm sorry, but I don't have information about events occurring after October 2023, including the results of the 2024 
Euro Cup final. You may want to check the latest sports news or official UEFA sources for that information
```

**Let's give our completion a tool to help it answer the question**

```python
from xnano import completion, web_search

# define a tool as a python function
def search_web(query: str) -> str:
    return web_search(query)

# The response will return a tool call
response = completion("who won the 2024 euro cup final?", tools = [search_web])

print(response.choices[0].message.tool_calls)
```

```bash
# output
[
    ChatCompletionMessageToolCall(
        function=Function(arguments='{"query":"2024 euro cup final winner"}', name='search_web'),
        id='call_vxsblOWR6I1rb1dfn7475poi',
        type='function'
    )
]
```

**Now, just by setting `run_tools = True`, __xnano__ will automatically execute the tool call and return the response**

```python
response = completion("who won the 2024 euro cup final?", tools = [search_web], run_tools = True)

# setting run tools to true will return a list of messages if a tool was executed
# the messages follow the progression
#    user -> tool call -> assistant
if isinstance(response, list):
    # lets print the latest message
    print(response[-1].choices[0].message.content)
```

```bash
# output
Spain won the 2024 Euro Cup final, defeating England 2-1.
```

**Now we're getting somewhere; but for simplicity, we can even define our tools as a **string!!** and __xnano__ will generate the function for us using a safe **sandboxed** execution environment**

```python
response = completion("who won the 2024 euro cup final?", tools = ["search_web"], run_tools = True)

if isinstance(response, list):
    print(response[-1].choices[0].message.content)
```

```bash
# output
Spain won the 2024 Euro Cup final, defeating England 2-1.
```

**If we want a structured response, the simplest way is to define a response model using a string or a list of strings**

```python
response = completion("who won the 2024 euro cup final?", response_model = ["winner", "score"])

print(response)
```

```bash
# output
{'winner': 'Spain', 'score': '2-1'}
```