# __xnano__

> _`the most super duper simple & fun llm library out there`_

`xnano` is an llm project built to be as developer & human friendly as possible, to help you build _extremely nano llm workflows_. 

> [!NOTE] 
> Currently examples for 'Agents', all LLM-Task oriented functions "Generators" & Text Processing/Vector Store are not included yet in this readme.

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
- [Agents](#a-new-way-to-build-ai-agents)
    - [Creating a Simple Chatbot with Tools](#creating-a-simple-chatbot-with-tools)
    - [Creating Autonomous Workflows](#creating-autonomous-workflows)
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
- [Generators - Task LLM Oriented Functions](#generators)
    - [Code Generators w/ `.generate_code()` & `.generate_function()`](#code-generators-w-generate_code--generate_function)
    - [Label Based Classification w/ `.generate_classification()`](#label-based-classification-w-generate_classification)
    - [Context Enhanced Text Chunking w/ `.generate_chunks()`](#context-enhanced-text-chunking)

---

## __Try The CLI App__

```bash
# run this command in your terminal!
xnano chat

# or xnano chat --model "anthropic/claude-3-5-sonnet-latest"
```

---

## __A New Way to Build AI Agents__

Extensive AI Agent documentation & examples will be available soon.

Creating `on-message` based agents was something I've wanted to do for a while, and `xnano` provides an easy way to get started building with LLM agents capable of multi agent collaboration & workflows.

### __Creating a Simple Chatbot with Tools__

To create an agent, we can either instantiate the `Agent` class, or create an agent using `create_agent()`.

```python
import xnano as x

# lets create an agent
# all params are optional!
agent = x.create_agent(
    name = "Steve",
    role = "AI Researcher",

    # xnano provides a few premade tools in the 'Tools' class
    # this tool uses the Tavily API to search the web for information
    # ensure you have `TAVILY_API_KEY` in your environment variables
    tools = [x.Tools.web_search]
)

# try running this script to chat with the agent in your terminal!
while True:

    user_input = input("You >>  ")

    # agent.completion works just as our standard .completion()
    # so you can give it a string, or a list of messages for the messages parameter
    response = agent.completion(messages = user_input)

    # print the response
    # it is a standard openai response object
    print("\nSteve: " + response.choices[0].message.content + "\n")
```

<details>
<summary> Conversation Example </summary>

```bash
You >>  hi

Steve: Hello! How can I assist you today?

You >>  who are you?

Steve: I am Steve, a world-class AI researcher specializing in solving complex problems and providing insightful 
answers. I'm here to help you with any questions or challenges you may have related to AI or other topics. How can
I assist you today?

You >>  do you have any tools?

Steve: Yes, I have access to a tool that allows me to perform web searches. If you have a specific question or 
topic in mind, I can use this tool to gather relevant information. What would you like to know?

You >>  can you search the web for the latest ai research?

Steve: Here are some recent articles on the latest AI research:

1. **[AI Index: State of AI in 13 Charts - Stanford 
HAI](https://hai.stanford.edu/news/ai-index-state-ai-13-charts)**  
   This year's AI Index is a comprehensive 500-page report tracking worldwide trends in AI for 2023, highlighting 
the rise of multimodal foundation models.

2. **[AI for Everything: 10 Breakthrough Technologies 2024 - MIT Technology 
Review](https://www.technologyreview.com/2024/01/08/1085096/artificial-intelligence-generative-ai-chatgpt-open-ai-
breakthrough-technologies)**  
   This article discusses how Google DeepMind utilized a large language model to solve an unsolved math problem, 
emphasizing the potential of generative AI in various fields, including financial services.

3. **[Artificial Intelligence | MIT News](https://news.mit.edu/topic/artificial-intelligence2)**  
   - Highlights include techniques to accelerate AI tasks while ensuring data security, findings of 
self-supervised models simulating mammalian brain activity, and challenges faced by generative AI in engineering 
design.

Feel free to explore any of these articles for more detailed insights! If you have further questions or need 
information on a specific topic, let me know!
```

</details>

### __Creating Autonomous Workflows__

`xnano` agents implement agentic `Worfklows` as pydantic basemodels, where each field in the model is a step in the workflow. Let's look at an example.

```python
import xnano as x
from pydantic import BaseModel

# create a workflow
# each field in the model is a step in the workflow
class Refinement(BaseModel):
    determine_errors : str
    plan_steps_to_fix : list[str]
    solution : str

# now lets create an agent with this workflow
# workflows are selected to the agent similar to tools, and the agent
# is able to interpret the response of the workflow as a whole
agent = x.create_agent(workflows = [Refinement])

# lets try running this example, with a sample piece of code that contains errors
code = """
def calculate_sum(a, b)
    sum = a + b;
    print("The sum is: " sum)
    retrun sum
"""

# now we can give this code to the agent, and it will refine it
response = agent.completion(
    messages = f"I'm having trouble with this code: {code}, could you refine it?"
)

# we can check for completed workflows in the response, the same way we check for tools;
# just with a different key
if response.workflow:
    print(response.workflow)

# lets' print the response content as well
print(response.choices[0].message.content)
```

<details>
<summary>
Workflow Output
</summary>

```bash
Refinement(
    determine_errors="1. Missing colon (:) at the end of the function definition line. \n2. Incorrect syntax for the 
print statement; it should use a comma (,) or a formatted string.\n3. There is a typo in the 'return' statement; it 
is spelled as 'retrun'. \n4. Using 'sum' as a variable name is not recommended because it shadows the built-in sum() 
function.",
    plan_steps_to_fix=[
        "Add a colon (:) at the end of the function definition line: 'def calculate_sum(a, b):'",
        "Modify the print statement to use proper syntax, either: 'print('The sum is:', sum)' or 'print(f'The sum is:
{sum}')'",
        "Correct the spelling of 'return' in the return statement: 'return sum'",
        "Consider renaming the variable 'sum' to avoid shadowing the built-in function, e.g., 'total' instead of 
'sum'."
    ],
    solution="def calculate_sum(a, b):\n    total = a + b\n    print(f'The sum is: {total}')\n    return total"
)
```

</details>

<details>
<summary>
Response Content
</summary>

```bash
Certainly! Your code has a few syntax errors that need correcting. Here’s the refined version:

def calculate_sum(a, b):
    total = a + b
    print("The sum is:", total)
    return total

### Changes made:
1. Added a colon (`:`) at the end of the function definition line.
2. Changed the variable name `sum` to `total` to avoid shadowing the built-in `sum()` function.
3. Changed the print statement to use a comma to separate the string and the variable.
4. Corrected the spelling of `return`.

Now, the function should work correctly and print the sum of `a` and `b`.

```

</details>

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

---

## __LLM 'Generators' - Task Oriented LLM Powered Functions__

### __Code Generators w/ `.generate_code()` & `.generate_function()`__

Generate code objects with `generate_code()`.

```python
import xnano as x

response = x.generate_code(
    instructions="Create an instance of a logger named `my_logger`. That can print to the console",
    model = "openai/gpt-4o-mini"
)

# response is a logger object
response.debug("Hello!")
```

```bash
# Output
2024-11-28 17:17:35,152 - my_logger - DEBUG - Hello!
```

Create generative functions with `generate_function()`.

```python
from xnano import generate_function

# default is mock = True
# set mock to false to generate actual functions like
# .generate_code()
# but llm generated code should never be 'depended' on or 
# used for anything important
@generate_function(mock = True)
def capitalize_string(data : str) -> str:
    """fully capitalizes a string"""


data = capitalize_string("Hello, world!")

print(data)
```

```bash
# Output
HELLO, WORLD!
```

### __Label Based Classification w/ `.generate_classification()`__

The upside of performing nlp tasks with LLMs is that without having to train a model, you can perform tasks with random / not commonly used labels & data.

#### __Single Label Classification__

```python
# generates only the label and confidence score
from xnano import generate_classification

response = generate_classification(
    inputs = [
        "I am a happy person",
        "I do not like apples"
    ],
    labels = ["positive", "negative"],
    model = "openai/gpt-4o-mini"
)

print(response)
```

```bash
# Output
[Classification(text='I am a happy person', label='positive', confidence=0.95), Classification(text='I do not like apples', label='negative', confidence=0.9)]
```

#### __Multi Label Classification__

To change the classification type, just set the `classification` argument to `"multi"`. Default is `"single"`.

```python
from xnano import generate_classification

inputs = ["I am a happy and sad person"]
labels = ["positive", "negative"]

response = generate_classification(
    inputs=inputs, labels=labels, classification="multi"
)

print(response)
```

```bash
Classification(text='I am a happy and sad person', label=['positive', 'negative'], confidence=None)
```

## __Context Enhanced Text Chunking__

Use a combination of `semchunk` and `LLMs` to create contextually aware text chunks.

```python
from xnano import generate_chunks


text = """
How do I decide what to put in a paragraph?

    Before you can begin to determine what the composition of a particular paragraph will be, you must first decide on an argument and a working thesis statement for your paper. What is the most important idea that you are trying to convey to your reader? The information in each paragraph must be related to that idea. In other words, your paragraphs should remind your reader that there is a recurrent relationship between your thesis and the information in each paragraph. A working thesis functions like a seed from which your paper, and your ideas, will grow. The whole process is an organic one—a natural progression from a seed to a full-blown paper where there are direct, familial relationships between all of the ideas in the paper.

    The decision about what to put into your paragraphs begins with the germination of a seed of ideas; this “germination process” is better known as brainstorming. There are many techniques for brainstorming; whichever one you choose, this stage of paragraph development cannot be skipped. Building paragraphs can be like building a skyscraper: there must be a well-planned foundation that supports what you are building. Any cracks, inconsistencies, or other corruptions of the foundation can cause your whole paper to crumble.

    So, let's suppose that you have done some brainstorming to develop your thesis. What else should you keep in mind as you begin to create paragraphs? Every paragraph in a paper should be:

    Unified: All of the sentences in a single paragraph should be related to a single controlling idea (often expressed in the topic sentence of the paragraph).
    Clearly related to the thesis: The sentences should all refer to the central idea, or thesis, of the paper (Rosen and Behrens 119).
    Coherent: The sentences should be arranged in a logical manner and should follow a definite plan for development (Rosen and Behrens 119).
    Well-developed: Every idea discussed in the paragraph should be adequately explained and supported through evidence and details that work together to explain the paragraph's controlling idea (Rosen and Behrens 119).
    How do I organize a paragraph?

    There are many different ways to organize a paragraph. The organization you choose will depend on the controlling idea of the paragraph. Below are a few possibilities for organization, with links to brief examples:

    Narration: Tell a story. Go chronologically, from start to finish. (See an example.)
    Description: Provide specific details about what something looks, smells, tastes, sounds, or feels like. Organize spatially, in order of appearance, or by topic. (See an example.)
    Process: Explain how something works, step by step. Perhaps follow a sequence—first, second, third. (See an example.)
    Classification: Separate into groups or explain the various parts of a topic. (See an example.)
    Illustration: Give examples and explain how those examples support your point. (See an example in the 5-step process below.)
    """

chunks = generate_chunks(text)

for chunk in chunks:
    print(chunk + "\n\n")
```

<details>

<summary>
Output
</summary>

```bash
=== CHUNK ===
TEXT:

How do I decide what to put in a paragraph?

    Before you can begin to determine what the composition of a particular paragraph will be, you must first decide 
on an argument and a working thesis statement for your paper. What is the most important idea that you are trying to 
convey to your reader? The information in each paragraph must be related to that idea. In other words, your 
paragraphs should remind your reader that there is a recurrent relationship between your thesis and the information 
in each paragraph. A working thesis functions like a seed from which your paper, and your ideas, will grow. The whole
process is an organic one—a natural progression from a seed to a full-blown paper where there are direct, familial 
relationships between all of the ideas in the paper.

    The decision about what to put into your paragraphs begins with the germination of a seed of ideas; this 
“germination process” is better known as brainstorming. There are many techniques for brainstorming; whichever one 
you choose, this stage of paragraph development cannot be skipped. Building paragraphs can be like building a 
skyscraper: there must be a well-planned foundation that supports what you are building. Any cracks, inconsistencies,
or other corruptions of the foundation can cause your whole paper to crumble.

    So, let's suppose that you have done some brainstorming to develop your thesis. What else should you keep in mind
as you begin to create paragraphs? Every paragraph in a paper should be:

    Unified: All of the sentences in a single paragraph should be related to a single controlling idea (often 
expressed in the topic sentence of the paragraph).
    Clearly related to the thesis: The sentences should all refer to the central idea, or thesis, of the paper (Rosen
and Behrens 119).
    Coherent: The sentences should be arranged in a logical manner and should follow a definite plan for development 
(Rosen and Behrens 119).
    Well-developed: Every idea discussed in the paragraph should be adequately explained and supported through 
evidence and details that work together to explain the paragraph's controlling idea (Rosen and Behrens 119).
    How do I organize a paragraph?

    There are many different ways to organize a paragraph. The organization you choose will depend on the controlling
idea of the paragraph. Below are a few possibilities for organization, with links to brief examples:

CONTEXT:
This text chunk provides guidance on how to construct and organize paragraphs in academic writing. It emphasizes the 
importance of having a clear argument and thesis statement as the foundation for developing paragraphs. The author 
discusses the process of brainstorming as a necessary step in forming cohesive ideas and highlights key 
characteristics that every paragraph should possess, such as unity, relevance to the thesis, coherence, and thorough 
development. The segment concludes by hinting at various organizational strategies for paragraphs, suggesting that 
the choice of organization is influenced by the controlling idea of the paragraph. This section serves as an 
instructional guide for writers aiming to improve their paragraph structure.
=============


=== CHUNK ===
TEXT:
    Narration: Tell a story. Go chronologically, from start to finish. (See an example.)
    Description: Provide specific details about what something looks, smells, tastes, sounds, or feels like. Organize
spatially, in order of appearance, or by topic. (See an example.)
    Process: Explain how something works, step by step. Perhaps follow a sequence—first, second, third. (See an 
example.)
    Classification: Separate into groups or explain the various parts of a topic. (See an example.)
    Illustration: Give examples and explain how those examples support your point. (See an example in the 5-step 
process below.)
    

CONTEXT:
This text chunk outlines various narrative techniques and writing strategies that can be utilized to enhance 
storytelling. It categorizes approaches such as narration, description, process explanation, classification, and 
illustration, providing brief definitions for each method. The mention of examples suggests the content aims to 
instruct or guide on how to effectively employ these techniques in writing.
=============
```

</details>

