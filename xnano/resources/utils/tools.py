# pre-built llm tools

__all__ = ["tools"]


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
    from ...lib import repl

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
    from ..web.web_url_searcher import web_url_search
    from ..web.web_url_reader import web_reader

    results = web_url_search(query, max_results)

    content = []

    for result in results:
        content.append(str(web_reader(result, max_chars_per_content=2500)))

    return content


class tools:
    execute_code = execute_code
    web_search = web_search


if __name__ == "__main__":
    print(web_search("latest technology news"))
