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
<<<<<<< HEAD
=======

---

## Easy Pydantic Model Generation & Completions

```python
import xnano as x
from pydantic import BaseModel

# the only thing you have to do is patch your models
@x.patch
class Sentiment(BaseModel):
    sentiment: str

response = Sentiment.model_generate(
    messages=[
        {"role": "system", "content": "You are a world class sentiment classifier."},
        {"role": "user", "content": "I am feeling great today!"}
    ]
)

print(response.sentiment)
```

```bash
# OUTPUT
positive
```

## Single Document QA

```python
import xnano as x

# lets read a paper from arxiv
document = x.read_documents(
    "https://arxiv.org/pdf/2406.14928"
)

# the document is an xnano basemodel by default
# so we can use all the llm functions directly
response = document.model_completion(
    "what is this paper about?",
    response_model = str
)

print(response)
```

<details closed>
<summary>OUTPUT</summary>

```bash
# OUTPUT
Response(
    response='The paper titled "Autonomous Agents for Collaborative Task under Information Asymmetry" introduces a novel multi-agent system paradigm
called iAgents. This paradigm addresses the challenges of information asymmetry that arise when autonomous agents collaborate to perform 
multi-person tasks. In traditional multi-agent systems, agents communicate based on shared information, but in scenarios involving human users, each
agent only has access to information from its respective user, creating a challenge for collaboration.\n\nThe authors propose that agents in the 
iAgents framework proactively exchange relevant human information necessary for task completion, thereby overcoming the problem of information 
asymmetry. They introduce an innovative reasoning mechanism known as InfoNav, which helps navigate the communication between agents to facilitate 
effective information exchange.\n\nThe paper also presents "InformativeBench," a benchmark designed to evaluate how well these agents can solve 
collaborative tasks under conditions of information asymmetry. Experimental results show that the iAgents framework enables collaboration among a 
social network of 140 individuals and can autonomously communicate and resolve tasks efficiently.\n\nOverall, this work contributes significantly by
shifting the research perspective in multi-agent systems from a holistic view to focusing on individual agents and their interactions, thereby 
enhancing human-agent collaboration in complex environments.'
)
```
</details>
>>>>>>> 0111177 (📚 DOCS: update readme examples)
