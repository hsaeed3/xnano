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
- [LLM Completions w/ any LiteLLM model](#incredibly-simple--extensive-completion-api-thanks-litellm)
    - [Completions w/ Structured Outputs (using Instructor)](#structured-outputs)
    - [Completions w/ Simpler & Quicker Structured Outputs](#simpler--quicker-structured-outputs)
    - [Completions w/ Automatically Run Tools](#automatically-run-tools)
    - [Completions w/ Automatically Generated Tools](#automatically-generated-tools)
    - [Completions Using Multiple Models](#get-completions-from-multiple-models)
    - [Batch Completions](#batch-completions)
    - [Streaming Completions](#streaming-completions)
    - [Asynchronous Completions](#asynchronous-completions)
- [Agents](#a-new-way-to-build-ai-agents)
    - [Creating a Simple Chatbot with Tools](#creating-a-simple-chatbot-with-tools)
    - [Creating Autonomous Workflows](#creating-autonomous-workflows)
    - [Creating Strict & User Augmented Steps in Workflows](#creating-strict--user-augmented-steps-in-workflows)
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
- [Embeddings & Vector Stores](#embeddings--vector-stores)
    - [Generating Embeddings](#generating-embeddings)
    - [Creating & Using Vector Stores](#creating-a-vector-store)
    - [Generating `RAG` Completions w/ Vector Stores](#generating-completions-w-vector-stores-for-rag)

---

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

### __Streaming Completions__

Stream completions with properly typed `chunk` objects using the `stream` argument.

```python
from xnano import completion

# stream a message
response = completion(
    "Tell me a long joke",
    stream=True,
)

# print the response
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

<details>
<summary>
Output
</summary>

```bash
Sure! Here’s a long joke for you:

Once upon a time, in a small village, there lived three friends: a physicist, a mathematician, and a philosopher. They were known for their brilliant minds but also for their inability to communicate effectively. One day, they decided to go on an adventure together to explore the nearby forest, which was rumored to have a magical pond.

As they strolled through the forest, they chatted about their respective fields. The physicist enthusiastically explained the laws of motion, the mathematician scribbled equations in the dirt, and the philosopher pondered the meaning of existence. Just as they were deep in conversation, they stumbled upon the magical pond.

To their surprise, a mystical frog emerged from the water. "Greetings, noble travelers!" the frog croaked. "I am the guardian of this pond. If you each solve a riddle I have for you, I will grant you one wish. But fail, and you must jump into the pond!" 

Intrigued, the friends agreed to the challenge. The frog turned to the physicist first. "Here’s your riddle: What weighs more, a ton of feathers or a ton of bricks?"

The physicist laughed and quickly replied, "They weigh the same! A ton is a ton!" 

“Correct!” the frog said. “Now, what is your wish?”

The physicist thought for a moment and said, “I wish to understand the universe!” 

With a wave of its webbed hand, the frog granted the wish, and the physicist felt a surge of knowledge coursing through him.

Next, the frog turned to the mathematician. "Here’s your riddle: If two’s a company and three’s a crowd, what are four and five?”

The mathematician furrowed his brow and exclaimed, “That’s easy! Nine!” 

“Correct!” smiled the frog. “What is your wish?” 

The mathematician, excited, said, “I wish to solve the greatest equations of all time!” 

The frog granted his wish, and the mathematician felt a rush of equations and theorems flooding his mind.

Finally, it was the philosopher's turn. The frog recited, “What is the sound of one hand clapping?”

The philosopher stared at the frog blankly for a long time, deep in thought. Hours went by as the physicist and mathematician chatted about their newfound wisdom, but the philosopher remained lost in contemplation.

Frustrated, the frog finally interrupted, “Well?! What’s your answer?”

The philosopher smiled and said, “The sound of one hand clapping is a reflection of the individual’s search for meaning in a world constrained by societal norms.”

The frog blinked, taken aback. “Um.. that's... deep, but you got it wrong. You still have to jump in the pond!”

The philosopher sighed, “I’m not worried. You see, while they might be diving into knowledge, I’ll be diving into the unknown!”

And with that, the philosopher took a graceful jump into the pond, while the physicist and mathematician laughed and congratulated themselves on their brilliant minds. 

As the philosopher splashed around in the water, he suddenly yelled, “Hey! Wait! Is this water even real? Or is it just a construct of my mind?”

To which the physicist replied, “No, it’s real! I can measure it!” 

And the mathematician added, “Well, I can prove how deep it is!”

Meanwhile, the philosopher, still swimming, called out, “Looks like my wish was the best of all! I’m swimming in the depths of existence!”

And so, from that day on, the three friends often visited the magical pond. The physicist and the mathematician conducted their experiments and calculations, while the philosopher dived in, pondering the mysteries of life—each believing they had made the best wish of all! 

But you know what they say: all’s well that ends well... as long as you can swim! 

And that’s how three friends found themselves... in a bit of a muddle! 

Hope you enjoyed it!%     
```

</details>

### __Asynchronous Completions__

Generate asynchronous completions easily, with all the functionality of the `completion` function.

```python
from xnano import async_completion
import asyncio

response = asyncio.run(
    async_completion("Hi, how are you?")
)
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

### __Creating Strict & User Augmented Steps in Workflows__

> [!NOTE]
> Currently the implementation for this is a little messy, but will be up to `xnano` standards soon.

Create a pipeline with steps & required dependencies:

```python
from xnano import Agent
from pydantic import BaseModel

# Define structured response models for each step
class CollectedData(BaseModel):
    data: str

class Analysis(BaseModel):
    analysis: str
    confidence: float

# Initialize agent with verbose logging enabled
agent = Agent(verbose=True)
steps = agent.steps()

# define a step
# steps can have structured responses
@steps.step("collect_data", response_model=CollectedData)
def collect_data(agent: Agent, input_data):
    # Send a prompt to the agent to generate mock sales data
    # The prompt specifies the structure we want: revenue, customers, products
    response = agent.completion(
        messages=[{
            "role": "user",
            "content": """Generate mock sales data for the last 3 months including:
            - Monthly revenue
            - Number of customers
            - Top selling products"""
        }]
    )
    
    # Extract the generated data from the response
    # Return in format matching CollectedData model
    return {"data": response.choices[0].message.content}

# analyze the collected data
# depends on collect_data step and returns structured analysis
@steps.step("analyze_data", 
            depends_on=["collect_data"],
            response_model=Analysis)
def analyze_data(agent: Agent, input_data):
    # Extract data from previous step
    # input_data contains results from all dependent steps
    data = input_data["collect_data"].data
    
    # Send the collected data back to agent for analysis
    # Provide specific focus areas in the prompt
    response = agent.completion(
        messages=[{
            "role": "user",
            "content": f"""Analyze this sales data and provide insights:
            {data}
            
            Focus on:
            - Revenue trends
            - Customer growth
            - Product performance"""
        }]
    )
    
    # Return analysis results matching Analysis model
    # Include confidence score for the analysis
    return {
        "analysis": response.choices[0].message.content,
        "confidence": 0.95  # Example confidence score
    }

# Execute all steps in order and get typed results
results = steps.execute()

# Print the analysis results
# Results are typed thanks to the Analysis model
print(results.analyze_data.analysis)
```

Let's view out output!

<details>
<summary>
Output
</summary>

```bash
### Sales Data Analysis

#### 1. Revenue Trends
- **Overall Growth:** There is a clear upward trend in monthly revenue over the three months analyzed:
  - August: $50,000
  - September: $65,000 (30% increase from August)
  - October: $70,000 (7.7% increase from September)
  
- **Total Revenue:** Over the three months, the total revenue is $185,000, indicating a solid performance. The growth
rate from August to September suggests successful promotion or product offering changes, while October's growth rate,
though smaller, indicates consistency and stability in sales.

#### 2. Customer Growth
- **Increased Customer Base:** The customer base has increased steadily each month:
  - August: 1,200 customers
  - September: 1,500 customers (25% increase from August)
  - October: 1,700 customers (13.3% increase from September)

- **Total Customers:** The total number of customers over the three months amounts to 4,400, which reinforces the 
positive trend in customer acquisition and retention.

#### 3. Product Performance
- **Top Products Overview:**
  - **Product A:** Steady performance in both August (300 units) and September (320 units). However, it saw a decline
in October, where it did not feature as a top seller. This may suggest potential market saturation or increased 
competition.
  - **Product B:** Improved performance in October with 400 units sold after 250 in August and reaching 0 in 
September, indicating a strong comeback. This may be due to promotional activities or enhanced features that 
attracted customers.
  - **Product D:** A notable performer introduced in September, selling 350 units and then 370 units in October, 
indicating it has become a strong seller.
  - **Product C and E:** Both products saw declines in unit sales, with Product C not appearing again and Product E 
just maintaining its position. This suggests re-evaluating these products for potential redesign, rebranding, or 
discontinuation.
  - **Product F:** Newly listed in October with 250 units sold; this shows promise and may need further marketing 
focus to capitalize on its initial success.

### Insights
- **Revenue Growth:** The business is experiencing healthy revenue growth which can be attributed to increased 
product offerings and effective customer engagement strategies.
- **Customer Engagement:** The growth in the customer base suggests effective marketing and a potential for brand 
loyalty, but strategies should be in place to maintain this momentum.
- **Inventory Decisions:** The mix of top-selling products indicates that some products may need to be phased out or 
re-evaluated. Strategic decisions regarding inventory and marketing for lower-performing products may also optimize 
profitability.
- **Promotional Strategies:** Evaluating promotional efforts, especially around products that show fluctuating 
performance, can help stabilize revenue and customer interest in specific product lines.

Overall, the data indicates a positive trajectory with opportunities for optimization in product offerings and 
customer engagement strategies. Adjustments based on performance insights will be key to sustaining growth moving 
forward.
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

class Reasoning(GenerativeModel):
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

---

## __Embeddings & Vector Stores__

`xnano` utilizes `Qdrant` and `LiteLLM`'s embedding generation to power vector search. Optionally, you can install `fastembed`, using `pip install 'xnano[fastembed]'`, or `pip install fastembed` to leverage `fastembed`'s fast & fully local embedding generation.

### __Generating Embeddings__

Generate embeddings with `text_embeddings()`.

```python
from xnano import text_embeddings

embeddings = text_embeddings(
    ['this is my first chunk', 'this is my second chunk'], 
    model = "openai/text-embedding-3-large"
)
```

To generate embeddings using `fastembed`, just use the `fastembed/` prefix with any `fastembed` supported model.

```python
from xnano import text_embeddings

embeddings = text_embeddings(
    ['this is my first chunk', 'this is my second chunk'], 
    model = "fastembed/BAAI/bge-base-en"
)
```

### __Creating a Vector Store__

Creating and using vectors in `xnano` is incredbly easy. To begin, lets create a vector store with some `memories`.

```python
from xnano import VectorStore

# all params are optional
store = VectorStore(
    # set this to either :memory: (defualt)
    # or a path to a folder
    # if a store is found in a folder, it will be loaded, otherwise a new store will be created
    location = ":memory:"
)

# with store.add() you can add anything to the store, strings, documents,
# pydantic models, etc.
# long text will automatically be chunked
store.add(
    ["My favorite color is blue", "I like to play soccer"]
)

# to search the store, use store.search()
results = store.search(
    "What is my favorite color?"
)

print(results)
```

<details>

<summary>
Output
</summary>

```bash
# Output
[
    SearchResult(
        id='8cf07d25-715f-4c30-b8f9-930e68dd3a95',
        chunk_id='19ebc4fe-8f6e-4781-b13a-951fec22682f',
        text='My favorite color is blue',
        metadata={
            'time_added': 1732845947.657376,
            'id': '8cf07d25-715f-4c30-b8f9-930e68dd3a95',
            'chunk_id': '19ebc4fe-8f6e-4781-b13a-951fec22682f',
            'embedding': None,
            'document_id': '8cf07d25-715f-4c30-b8f9-930e68dd3a95'
        },
        score=0.7446617009267129
    ),
    SearchResult(
        id='07583029-8349-4c2b-add6-44ff114a1ddf',
        chunk_id='74f459c3-4cd6-4916-a1ac-1e8ab69fc11d',
        text='I like to play soccer',
        metadata={
            'time_added': 1732845947.657393,
            'id': '07583029-8349-4c2b-add6-44ff114a1ddf',
            'chunk_id': '74f459c3-4cd6-4916-a1ac-1e8ab69fc11d',
            'embedding': None,
            'document_id': '07583029-8349-4c2b-add6-44ff114a1ddf'
        },
        score=0.1960301443680059
    )
]
```

</details>

### __Generating Completions w/ Vector Stores for `RAG`__

Vector stores can directly be queried with `VectorStore.completion()`, to generate `RAG` completions based on the most relevant search results.

The base `xnano` completion function is also capable of taking in a single or list of `VectorStore` objects, to generate completions based on the most relevant search results. 

```python
from xnano import VectorStore

# all params are optional
store = VectorStore()

store.add(
    ["My favorite color is blue", "I like to play soccer"]
)

# generate a completion
response = store.completion(
    "what is my favorite color?",
    model = "openai/gpt-4o-mini"
)

print(response.choices[0].message.content)
```

```bash
# Output
Your favorite color is blue!
```