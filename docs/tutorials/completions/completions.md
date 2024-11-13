# **LLM Completions**

Generating LLM completions is the base functionality of the `xnano` library. The standard for creating completions follows the LiteLLM pattern, using the `completion` function.

The `completion` function in the `xnano` library is a robust extension to create completions with a variety of use cases, the goal was to create an API that does not try to bring in any boilerplate or further configuration to achieve advanced use cases.

## **Generating a Completion**

To generate a completion, simply pass a model and a prompt or a list of messages to the `completion` function. 

The model argument follows the LiteLLM `provider/model` format, so any model compatible with LiteLLM works with `xnano`. If no model is passed, by default the library uses ___gpt-4o-mini___. 

<summary>Simple Completion</summary>

```python
from xnano import completion

response = completion("how are you?")

# is the same as
# completion(messages = [{"role": "user", "content": "how are you?"}])
```

<summary>Using a different model</summary>

```python
# Using a different model
response = completion("how are you?", model = "anthropic/claude-3-5-sonnet-latest")
```

By default, the `completion` function returns the standard OpenAI `ChatCompletion` object. Let's see what the full response object looks like.

<details closed>
<summary>Response</summary>
```bash
# output
ModelResponse(
    id='chatcmpl-ad902c86-7133-4cff-9579-46f86f4b6f9e',
    created=1731461313,
    model='claude-3-5-sonnet-latest',
    object='chat.completion',
    system_fingerprint=None,
    choices=[
        Choices(
            finish_reason='stop',
            index=0,
            message=Message(
                content="I'm doing well, thank you! How are you today?",
                role='assistant',
                tool_calls=None,
                function_call=None
            )
        )
    ],
    usage=Usage(
        completion_tokens=16,
        prompt_tokens=12,
        total_tokens=28,
        completion_tokens_details=None,
        prompt_tokens_details=PromptTokensDetailsWrapper(
            audio_tokens=None,
            cached_tokens=0,
            text_tokens=None,
            image_tokens=None
        ),
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0
    )
)
```
</details>

Let's print just the response message.

```python
print(response.choices[0].message.content)
```

```bash
# output
I'm doing well, thank you! How are you today?
```