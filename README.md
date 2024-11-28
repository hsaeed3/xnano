# __xnano__

> _`the most super duper simple & fun llm library out there`_

`xnano` is an llm project built to be as developer & human friendly as possible, to help you build _extremely nano llm workflows_. 

> [NOTE] - Currently examples for 'Agents', all LLM-Task oriented functions "Generators" & Text Processing/Vector Store are not included yet in this readme.

# __Installation__

Install `xnano` using pip:

```bash
pip install xnano
```

```bash
xnano
```

# __Features__

**Table of Contents**

- [Terminal Application](#try-the-cli)
- [LLM Completions w/ any LiteLLM model](#incredibly-simple--extensive-completion-api-thanks-litellm)
    - [Completions w/ Structured Outputs (using Instructor)](#structured-outputs)
    - [Completions w/ Simpler & Quicker Structured Outputs](#simpler--quicker-structured-outputs)
    - [Completions w/ Automatically Run Tools](#automatically-run-tools)
    - [Completions w/ Automatically Generated Tools](#automatically-generated-tools)
    - [Completions Using Multiple Models](#get-completions-from-multiple-models)
    - [Batch Completions](#batch-completions)
- [Generative Pydantic Models](#generative-pydantic-models)
    - [Creating a Generative Model](#creating-a-generative-model)
    - [Generating Synthetic Data w/ `.model_generate()`](#generating-synthetic-data-w-model_generate)
    - [Regenerating Specific Fields](#regenerating-specific-fields)
    - [Using Sequential Generation (_Chain of Thought_)](#using-sequential-generation-chain-of-thought)
    - [Using Pydantic Models as Context w/ `.model_completion()`](#using-pydantic-models-as-context-w-model_completion)

## __Try The CLI App__

```bash
# run this command in your terminal!
xnano chat

# or xnano chat --model "anthropic/claude-3-5-sonnet-latest"
```

---

## __Incredibly Simple & Extensive `.completion()` API__ _(thanks litellm)_

```python
from xnano import completion
```

<br/>

Generate completions without strictly defining a list of messages

```python
from xnano import completion

# Messages can be either a string, a list of messages, or a list of list of messages (Batching)
# (thanks litellm)
response = completion("Hello, how are you?")
```

<details>
<summary>
Output
</summary>

```bash
ModelResponse(
    id='chatcmpl-AYGnqICW9kvWuFIFbiJY6agBSSaBA',
    created=1732731106,
    model='gpt-4o-mini-2024-07-18',
    object='chat.completion',
    system_fingerprint='fp_0705bf87c0',
    choices=[
        Choices(
            finish_reason='stop',
            index=0,
            message=Message(
                content="Hello! I'm just a program, so I don't have feelings, but I'm here and ready to help you. How can I assist you today?",
                role='assistant',
                tool_calls=None,
                function_call=None
            )
        )
    ],
    usage=Usage(
        completion_tokens=29,
        prompt_tokens=13,
        total_tokens=42,
        completion_tokens_details=CompletionTokensDetailsWrapper(accepted_prediction_tokens=0, audio_tokens=0, reasoning_tokens=0, rejected_prediction_tokens=0, text_tokens=None),
        prompt_tokens_details=PromptTokensDetailsWrapper(audio_tokens=0, cached_tokens=0, text_tokens=None, image_tokens=None)
    ),
    service_tier=None
)
```

</details>

Use any LiteLLM model, with all normal & completely typed completion arguments

```python
from xnano import completion

# Supports any LiteLLM compatible model
# (thanks litellm)
response = completion(
    messages = [
        {"role" : "system", "content" : "You are a helpful assistant who only speaks in haiku"},
        {"role" : "user", "content" : "What is the capital of France?"}
    ],
    model = "anthropic/claude-3-5-haiku-latest",

    # all normal chat completion arguments work & are typed as standard
    temperature = 0.223,
    max_completion_tokens = 1000,
    top_p = 0.99
)
```

<details>
<summary>
Output
</summary>

```bash
Paris gleams brightly
Eiffel Tower touches sky
France's heart beats here
```

</details>

### __Structured Outputs__

Generate structured outputs using `Instructor` or the OpenAI `structured outputs` API.

```python
# Structured Outputs w/ Instructor
from xnano import completion
from pydantic import BaseModel

class Extraction(BaseModel):
    name : str
    age : int

response = completion(
    messages = [
        {"role" : "user", "content" : "Extract the name and age from the following text: John is 30 years old."}
    ],

    # super, super useful argument
    instructor_mode = "markdown_json_mode",
    # use either 'response_format' for litellm's structured output or 'response_model' for instructor
    response_model = Extraction
)
```

```bash
# Output
Extraction(name='John', age=30)
```

### __Simpler & Quicker Structured Outputs__

Use strings as replacements for pydantic models for even quicker structured outputs. Use a string in the `field_name: field_type` format. If a type is not specified, it will default to a `str`.

> Note: this is not something you should do when actually trying to build something meaningful. Using this method, although simple does not add any extra prompting that defines the response format or any of its fields.

```python
import xnano as x

response = x.completion(
    "Extract the name and age from the following text: John is 30 years old.",

    response_model = ["name", "age : int"]
)
```

```bash
# Output
Response(name='John', age=30)
```

Or use a type hint itself as a replacement for a pydantic model. This will return the type as the response itself.

```python
import xnano as x

response = x.completion(
    "Extract the age from the following text: John is 30 years old.",
    response_model = int
)
```

```bash
# Output
30
```

### __Automatically Run Tools__

Use any `python function`, `pydantic model`, or `OpenAI function` as a tool when generating completions. Automatically execute any python functions when passed as tools, using `run_tools = True`.

```python
from xnano import completion

def book_flight(destination : str, date : str) -> str:
    return f"NO DATES AVAILABLE"

response = completion(
    "Book a flight to Paris for 2024-12-01",

    tools = [book_flight],
    # set run tools to true for automatic tool execution
    run_tools = True,

    # optionally set to true to get back all messages
    # return_messages = True
)

print(response.choices[0].message.content)
```

```bash
# Output
It seems that no flights are available to Paris on December 1, 2024. Would you like to choose a different date or destination?
```

### __Automatically Generate Tools__

A '_just for fun_' feature that automatically generates & executes python functions in a safe sandboxed environment. To generate tools, just pass a `string` as a tool!

```python
from xnano import completion

response = completion(
    "What is my OS?",
    tools = ["run_cli_command"]
)

print(response.choices[0].message.content)
```

```bash
Your operating system is macOS (Darwin), running on an ARM64 architecture.
```

### __Get Completions From Multiple Models__

(thanks litellm)

Get completions from multiple models in a single call.

```python
from xnano import completion

# batch completions using multiple models
responses = completion(
    "Who are you?",
    model = ["gpt-4o-mini", "anthropic/claude-3-5-sonnet-latest"]
)

for response in responses:
    print(response.choices[0].message.content + "\n")
```

<details>
<summary>
Output
</summary>

```bash
I am an AI language model created by OpenAI, designed to assist with a wide range of queries by providing information and generating text based 
on the input I receive. How can I assist you today?

I'm Claude, an AI created by Anthropic to be helpful, honest, and harmless. I always aim to be direct and truthful about what I am.
```

</details>

### __Batch Completions__

Batch completions using using multiple threads of messages.

> Currently not supported for multiple models.

```python
from xnano import completion

responses = completion(
    messages = [
        [
            {"role" : "system", "content" : "You are a helpful assistant who only speaks in haiku"},
            {"role" : "user", "content" : "What is the capital of France?"}
        ],
        [
            {"role" : "system", "content" : "You are a helpful assistant who only speaks in not very useful statements"},
            {"role" : "user", "content" : "What is the capital of France?"}
        ]
    ],

    model = "gpt-4o-mini"
)

for response in responses:
    print(response.choices[0].message.content + "\n")
```

<details>
<summary>
Output
</summary>

```bash
City of lights shines,  
Paris, heart of France, aglow,  
History unfolds.

Some people enjoy visiting Europe.
```
</details>

---

## __Generative Pydantic Models__

`xnano` integrated something that I think is super cool, and very simple to use. `xnano.GenerativeModel` is a simple wrapper around `pydantic.BaseModel` that builds in a ton on LLM functionality.

### __Creating a Generative Model__

The API for `GenerativeModel` is extremely simple, and it follows both the `pydantic` naming convention and is usable two different ways.

**Creating a model directly**

```python
from xnano import GenerativeModel

class Person(GenerativeModel):
    name : str
    age : int
```

**Patching Existing Pydantic Models**

```python
import xnano as x
from pydantic import BaseModel

@x.model_patch
class Person(BaseModel):
    name : str
    age : int
```

or

```python
class Person(BaseModel):
    name : str
    age : int

person = Person(name = "John", age = 30)

person = x.model_patch(person)
```

### __Generating Synthetic Data w/ `.model_generate()`__

All LLM functions in the `GenerativeModel` class will begin with the `model_` prefix to fit `Pydantic's naming convention`.

```python
from xnano import GenerativeModel

class Person(GenerativeModel):
    name : str
    age : int

# instructions are optional
# the function will automatically create distilled and authentic data
# set n to the number of models you want to generate
person = Person.model_generate()

print(person)
```

```bash
Person(name='Emily', age=28)
```

#### __Generating Multiple (Batches of) Models__

```python
from xnano import GenerativeModel

class Person(GenerativeModel):
    name : str
    age : int

# can take in either a string or a list of messages
people = Person.model_generate(
    n = 5,
    messages = "The people must be superheroes",
    model = "openai/gpt-4o-mini"
)

print(people)
```

```bash
[
    Person(name='Captain Valor', age=30),
    Person(name='Mystic Shadow', age=27),
    Person(name='Thunderstrike', age=34),
    Person(name='Vortex', age=22),
    Person(name='Iron Guardian', age=31)
]
```

#### __Regenerating Specific Fields__

By passing fields in the `fields` argument in `.model_generate()`, you can regenerate specific fields of a model; using other fields as context!

```python
import xnano as x
from pydantic import BaseModel

@x.model_patch
class Recommendation(BaseModel):
    weather : str
    outfit : str

recommendation = Recommendation(weather = "snowing", outfit = "t-shirt")

recommendation = recommendation.model_generate(fields = ["outfit"])

print(recommendation)
```

```bash
Recommendation(weather='snowing', outfit='heavy coat')
```

#### __Using Sequential Generation (_Chain of Thought_)__

The `model_generate()` function contains a `process` argument that is set to `batch` by default. This is the standard behaviour you would expect from using `response_model` in a completion, where the entire class is generated at once. Setting the `process` argument to `sequential` will generate the class one field at a time, using the previously generated fields as context.

```python
from xnano import GenerativeModel

class Reasoning(BaseModel):
    step_1 : str
    step_2 : str
    step_3 : str
    conclusion : str

reasoning = Reasoning.model_generate(
    messages = "I want to buy a new laptop, but I'm not sure which one to buy.",
    process = "sequential"
)

print(reasoning)
```

<details>

<summary>
Output
</summary>

```bash
Reasoning(
    step_1='Determine your primary needs for the laptop, such as gaming, business, graphic design, or general use.',
    step_2='Research different laptop models that fit your needs, comparing specifications, prices, and user reviews.',
    step_3='Make a decision based on your findings, taking into account the warranty, customer support, and after-purchase service options.',
    conclusion='After carefully evaluating your requirements and researching various options, choose the laptop that best aligns with your needs and 
budget.'
)
```

</details>

### __Using Pydantic Models as Context w/ `.model_completion()`__

A simple way of using `Pydantic` models as a RAG resource,is to use the `.model_completion()`. This method builds the model's content into a formatted context string, which is used in completions.

```python
from xnano import GenerativeModel

class Information(GenerativeModel):
    secret_instruction : str

information = Information(secret_instruction = "RUNNNNNN AWAYY")

response = information.model_completion(
    messages = "what does our secret instruction mean?"
)

print(response.choices[0].message.content)
```

```bash
The phrase "RUNNNNNN AWAYY" in your secret instruction seems to imply a sense of urgency or a warning to escape a situation.
If you need to discuss this in a specific context or require assistance related to it, please let me know!
```

## __LLM 'Generators' - Task Oriented LLM Powered Functions__

### __Code Generators__



