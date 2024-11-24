# Automatic Tool Execution

To automatically execute tools, all we have to do is set the `run_tools` argument to `True`. Currently, you can execute `Python` functions, and `Pydantic` models; with an attached `.execute()` method.

___Please Note:___ Running tools will not run one single completion, it runs an initial completion to get the tool call, and then runs a second completion as a response to the tool's output.

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

    model="openai/gpt-4o-mini",
    tools=[search_news],

    # set run_tools to True
    run_tools=True
)

# print the response content
print(response.choices[0].message.content)
```

```bash
The latest headline suggests that the stock market has gone up 1000% today.
```

### Returning All Messages

If you want to retrieve all the messages ran in the completion, you can set the `return_messages` argument to `True`.

```python
response = completion(
    "What are the latest headlines in the stock market?",
    model="openai/gpt-4o-mini",
    tools=[search_news],
    run_tools=True,

    # set return_messages to True
    return_messages=True
)
```

<details>
<summary>Output</summary>

```python
[
    ModelResponse(
        id='chatcmpl-',
        created=1732359224,
        model='gpt-4o-mini-2024-07-18',
        object='chat.completion',
        system_fingerprint='fp_',
        choices=[
            Choices(
                finish_reason='tool_calls',
                index=0,
                message=Message(
                    content=None,
                    role='assistant',
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            function=Function(
                                arguments='{"query":"latest stock 
market headlines"}',
                                name='search_news'
                            ),
                            id='call_NASRcnZcpKGzzgXykK9oFDH2',
                            type='function'
                        )
                    ],
                    function_call=None
                )
            )
        ],
        usage=Usage(
            completion_tokens=17,
            prompt_tokens=71,
            total_tokens=88,
            completion_tokens_details=CompletionTokensDetailsWrapp
er(
                accepted_prediction_tokens=0,
                audio_tokens=0,
                reasoning_tokens=0,
                rejected_prediction_tokens=0,
                text_tokens=None
            ),
            prompt_tokens_details=PromptTokensDetailsWrapper(
                audio_tokens=0,
                cached_tokens=0,
                text_tokens=None,
                image_tokens=None
            )
        ),
        service_tier=None
    ),
    {
        'role': 'tool',
        'content': '"the stock market has gone up 1000% today"',
        'tool_call_id': 'call_NASRcnZcpKGzzgXykK9oFDH2'
    },
    ModelResponse(
        id='chatcmpl-',
        created=1732359226,
        model='gpt-4o-mini-2024-07-18',
        object='chat.completion',
        system_fingerprint='fp_',
        choices=[
            Choices(
                finish_reason='stop',
                index=0,
                message=Message(
                    content='One of the latest headlines in the 
stock market states that "the stock market has gone up 1000% 
today."',
                    role='assistant',
                    tool_calls=None,
                    function_call=None
                )
            )
        ],
        usage=Usage(
            completion_tokens=25,
            prompt_tokens=109,
            total_tokens=134,
            completion_tokens_details=CompletionTokensDetailsWrapp
er(
                accepted_prediction_tokens=0,
                audio_tokens=0,
                reasoning_tokens=0,
                rejected_prediction_tokens=0,
                text_tokens=None
            ),
            prompt_tokens_details=PromptTokensDetailsWrapper(
                audio_tokens=0,
                cached_tokens=0,
                text_tokens=None,
                image_tokens=None
            )
        ),
        service_tier=None
    )
]
```
</details>

<br/>

# Generating Tools

If you want to just 'have fun' or play around with using tools, you can automatically generate tools by passing a string to the `tools` argument. Generating tools utilizes `xnano's` [`Code Generators`](../code-generation/generating-code-outputs.md) to create a function from a string.

```python
from xnano import completion

# generate a completion with the tool
response = completion(
    "What is my OS version?",

    # define tool as a string
    tools=["run_cli_command"],
    run_tools=True,
)

print(response.choices[0].message.content)
```

```bash
Your operating system is macOS ("Darwin") with the version 23.6.0.
```
