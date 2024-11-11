from xnano import completion, web_search

# define a tool as a python function
def search_web(query: str) -> str:
    return web_search(query)

# The response will return a tool call
response = completion("who won the 2024 euro cup final?", tools = [search_web], run_tools = True)

print(response)