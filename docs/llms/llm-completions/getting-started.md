# Getting Started with LLM Completions in `xnano`

All [`LLM`](#) methods and functions in [`xnano`](#) are powered by a single function to serve as a drop-in wrapper for [`LiteLLM`](#)'s `completion` method. 

<br/>

## Overview

The `xnano` completion method began as a simple wrapper to use [`Instructor`](https://github.com/instructor-ai/instructor) structured outputs with all [`LiteLLM`](https://github.com/BerriAI/litellm) models easily, but has expanded to include the following features:

<div class="grid cards" markdown>

- :material-earth: <span style="color: var(--md-code-hl-variable-color);">__Use any LLM Provider__</span>: as the module is powered by [`LiteLLM`](https://github.com/BerriAI/litellm), all LiteLLM models are supported.
- :material-data-matrix: <span style="color: var(--md-code-hl-variable-color);">__Structured Outputs__</span>: Easy access to [`Instructor`](https://github.com/instructor-ai/instructor) structured outputs using `response_model=`
- :material-tools: <span style="color: var(--md-code-hl-variable-color);">__Tool Calling__</span>: Use any `Pydantic Model`, `Python Function` or `OpenAI Function` as a tool.
- :material-tooltip-check: <span style="color: var(--md-code-hl-variable-color);">__Automatic Tool Execution__</span>: Easily run your tools and get LLM results using `run_tools=True`
- :material-flask: <span style="color: var(--md-code-hl-variable-color);">__Tool Generation__</span>: Define tools as `strings` and the LLM will safely __`generate`__ & __`execute`__ them for you.
- :material-brain: <span style="color: var(--md-code-hl-variable-color);">__Context Aware__</span>: Add any context to your completions using `context=`, or connect an `xnano` Vector Store to your completions.

</div>

<br/>

## Basic Usage

To use the function, simply import it from the `xnano` library:

```python
from xnano import completion

response = completion(
    # messages can be a string or a list of messages
    "What is my CLI version?",

    # all litellm models are supported
    model = "openai/gpt-4o-mini",

    # easily define response models without having to create a pydantic model
    response_model = ["os_name", "os_version : float"],

    # generate tools using strings
    tools = ["run_cli_command"],

    # automatically execute tools and return the results
    run_tools = True
)
```

```bash
# OUTPUT
Response(os_name='Darwin', os_version=23.6)
```