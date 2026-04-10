# Adding Context to Completions

The `completion` function allows for the passing of simple context to the LLM, without explicitly adding it into the `messages` parameter. This context is either added to the most recent system message, or if no system message is present, it will add one to the start of the message history.

## __Adding Context Using the `context` Parameter__

The simplest way to add context to a completion is to use the `context` parameter. This parameter can take in a string, list, dictionary, pydantic model, and a few other types.

Let's look at an example of how to use the `context` parameter:

```python
from xnano import completion

# set some context
context = "My favorite color is green."

# generate a completion
response = completion(
    messages = "What is my favorite color?",
    model = "ollama/llama3.2:3b",

    # add the context
    context = context
)

# print the response
print(response.choices[0].message.content)
```

```bash
# Output

>> Your favorite color is green.
```

## __Adding Context Using [`xnano.VectorStore`](#)__

This feature is not fully integrated yet sadly, but will be soon, supporting adding multiple stores, and building total context. To currently generate `RAG` completions with the `VectorStore`, you can directly call [`.completion()`](#) on the `VectorStore` object.