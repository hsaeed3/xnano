# Adding Context to LLM Completions

Adding context is a simple process in `xnano`. You can add context to your completions by passing a `context` argument to the `completion` function.

```python
from xnano import completion

response = completion(
    "What is my favorite color and food?",

    model="anthropic/claude-3-5-haiku-latest",

    # pass the context
    context="My favorite color is blue and my favorite food is pizza."
)

print(response.choices[0].message.content)
```

```bash
Your favorite color is blue, and your favorite food is pizza.
```

Context can be defined as all sorts of objects, including `strings`, `lists`, `dictionaries`, `pydantic models`, and more.

