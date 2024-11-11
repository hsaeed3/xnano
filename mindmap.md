mindmap

uh so how do i make these agents work

currently: init agent -> inits a list of messages & able to call .completion()

how to implement agent to agent conversation?
how to implement workflows?

i think i need to somehow augment
for agent to agent conversation, to have the agents each think they are the 'assistant' and send the other agent's messages as user messages

this way, the agents will be able to see the other agent's messages as context, and be able to respond to them as if they are the assistant

and since for each agent i can make it think it's the assistant, i can make it so that each agent can call the other agent's completion() method