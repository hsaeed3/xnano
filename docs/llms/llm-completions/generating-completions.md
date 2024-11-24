# Generating LLM Completions

The [`completion()`](#) function is usable from two different locations, and is usable __asynchronously__ through [`async_completion()`](#). The following example will go the most basic `completion` arguments.

## Example

Let's create a simple completion that includes a simple system prompt.

### Passing Messages

Messages in the `completion` function can be a string or a list of `OpenAI` API formatted messages. Since we need to add a system prompt, we'll use a list of messages.

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you today?"}
]
```

### Generating a Completion

=== "Standard Completion"

    ```python
    import xnano as x

    response = x.completion(
        model="gpt-4o-mini",
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you today?"}
        ],

        # all standard llm arguments are supported
        temperature=0.5,
        max_completion_tokens=100,
        # ...
    )

    print(response)
    ```

=== "Asynchronous Completion"

    ```python
    import xnano as x
    import asyncio

    result = asyncio.run(x.async_completion(
        model="gpt-4o-mini",
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you today?"}
        ],

        # all standard llm arguments are supported
        temperature=0.5,
        max_completion_tokens=100,
        # ...
    ))

    print(result)
    ```

### Getting Responses

Non structured outputs are returned as `LiteLLM` `ModelResponse` objects, which follow the same structure as the `ChatCompletion` object from the `openai` library.

=== "To Print Response Content"

    ```python
    print(response.choices[0].message.content)
    ```

=== "To Print Tool Calls"

    ```python
    print(response.choices[0].message.tool_calls)
    ```