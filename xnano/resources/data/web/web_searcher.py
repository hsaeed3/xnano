# pre-built llm tools

__all__ = ["search_web"]

from typing import List, Union, Dict, Optional


# search web tool
def web_search(
    query: str,
    max_results: int = 10,
    verbose: bool = False,
    max_chars_per_content: int = 2500,
) -> Union[List[str], Dict[str, Union[str, List[str]]]]:
    """
    A function that searches the web and returns a list of content for the specified number of results.

    Args:
        query (str): The query to search the web with.
        max_results (int): The maximum number of results to return.
        verbose (bool): Whether to print verbose output.
        max_chars_per_content (int): Maximum number of characters to return per content.

    Returns:
        Union[List[str], Dict[str, Union[str, List[str]]]]: A list of content for the search results or a dictionary with detailed information.
    """
    from .web_url_searcher import web_url_search
    from .web_url_reader import web_reader

    if verbose:
        print(f"Searching the web for: {query} with a limit of {max_results} results.")

    results = web_url_search(query, max_results, verbose)

    if not results:
        return {"error": "No results found."}

    content = []
    returned_results = {}

    for idx, result in enumerate(results):
        if verbose:
            print(f"Fetching content from: {result}")
        fetched_content = web_reader(
            result, max_chars_per_content=max_chars_per_content, verbose=verbose
        )
        content.append(fetched_content)
        returned_results[result] = fetched_content

    if verbose:
        print(f"Fetched content for {len(results)} results.")

    return returned_results


if __name__ == "__main__":
    results = web_search("latest technology news", max_results=5, verbose=True)
    for url, content in results.items():
        print(f"\nContent from {url}:\n{content}")
