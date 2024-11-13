# chatbot with guardrails

# creating a validator with custom guardrails is incredibly
# simple with xnano
# lets utilize the .completion() & .validate() methods to create a chatbot
# with a simple guardrail layer

# try running this script, and trying different inputs to see how the guardrails work

import xnano as x


# lets create the guidelines for our validator
# this example will create a 'customer support' chatbot
# that can answer questions about the product
guardrails = """
As an expert support agent for a a software & compliance company that creates software tools & widgets, you do not accept
any questions or queries that are not related to the product. General chat messages like
`hi` are allowed.
"""


# initialize our messages
messages = []


# lets create our chatbot
while True:

    # get user input
    user_input = input("You: ")

    # validate the user input
    validation = x.validate(
        inputs = user_input,
        guardrails = guardrails
    )

    # print the validation result
    print(validation)

    # if the user input is valid, generate a response
    if not validation.violates_guardrails:

        # add the user message to the message history
        messages.append({"role": "user", "content": user_input})

        # generate a response
        response = x.completion(
            messages = messages,
            model = "gpt-4o-mini",
            temperature = 0.5
        )

        # add the response to the message history
        messages.append(response.choices[0].message.model_dump())

        # print the response
        print(f"Bot: {response.choices[0].message.content}")

    
    # if the user input violates the guardrails, print an error message
    else:
        print("Error: Invalid input")
