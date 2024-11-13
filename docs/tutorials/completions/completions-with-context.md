# **LLM Completions with Context**

The `completion` function provides a simple method to add context without much setup to your LLM completions. The method builds the context into the system message, depending on context length.

### **Adding Context to a Completion**

<summary>Generating a Completion with Context</summary>

```python
from xnano import completion

# define some context
# context can be any type
context = "My favorite color is blue"

# generate a completion with context
response = completion(
    "What is my favorite color?",
    context = context
)

# print the response content
print(response.choices[0].message.content)
```

```
# Output
Your favorite color is blue.
```

