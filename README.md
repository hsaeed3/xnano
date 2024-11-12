# xnano

```bash
pip install xnano
```

---

## Examples

### The most extensive llm completion function any library provides

```python
import xnano as x

response = x.completion(
    # messages can be a list of messages or just a string
    # you can also pass a list of lists of messages to create batch completions
    messages = "what os am i running?",

    # any litellm model is supported
    model = "openai/gpt-4o-mini",

    # tools can be python functions, pydantic models, openai functions or even strings!
    # string tools are generated & optionally executed at runtime in a sandboxed environment
    tools = ["run_cli_command"],

    # automatically run tools!
    run_tools = True,

    # structured responses with instructor!
    # response models can be defined as pydantic models, or just like tools; even strings, lists of strings & dictionaries!
    # you can also pass in a generic type into the list or as is (str, int, etc...)
    response_model = ["operating_system", "version"]
)

print(response)
```

```bash
# OUTPUT
Response(operating_system='Darwin', version='23.6.0')
```
