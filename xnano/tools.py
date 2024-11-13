# pre-built llm tools

__all__ = ["web_search"]


from typing import List
import json


def execute_code(code: str) -> str:
    """
    A function that executes code and returns the output

    Args:
        code (str): The code to execute

    Returns:
        str: The output of the code
    """
    from ._lib import repl

    return json.dumps(repl.execute_in_sandbox(code))


# search web tool
def web_search(
    query: str,
    max_results: int,
) -> List[str]:
    """
    A function that searches the web and returns a list of content for the first 5 results

    Args:
        query (str): The query to search the web with
        max_results (int): The maximum number of results to return

    Returns:
        List[str]: A list of content for the first 5 results
    """
    from .data import web_url_search
    from .data import web_reader

    results = web_url_search(query, max_results)

    content = []

    for result in results:
        content.append(str(web_reader(result, max_chars_per_content=2500)))

    return content


class TOOLS:
    CODE_EXECUTOR = execute_code
    WEB_SEARCH = web_search


if __name__ == "__main__":
    print(web_search("latest technology news"))
