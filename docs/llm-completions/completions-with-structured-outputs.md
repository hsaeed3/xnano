# Generating Completions with Structured Outputs

Although [`LiteLLM`](https://github.com/BerriAI/litellm) supports structured outputs through the use of the `response_format` parameter, I've always been a very heavy user of the [`Instructor`](https://github.com/instructor-ai/instructor) library, for its rich functionality, so [`xnano`] defaults to using [`Instructor`](https://github.com/instructor-ai/instructor) for all __non-batch__ structured outputs.

## Generating Completions with Structured Outputs

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