# pre-built llm tools

__all__ = ["search_web"]

from typing import List


# search web tool
def search_web(
        query : str,
        max_results : int = 5,
) -> List[str]:
    """
    A function that searches the web and returns a list of content for the first 5 results

    Args:
        query (str): The query to search the web with
        max_results (int): The maximum number of results to return

    Returns:
        List[str]: A list of content for the first 5 results
    """
    from ...web.web_searcher import web_search
    from ...web.url_reader import read_urls

    results = web_search(query, max_results)

    content = []

    for result in results:
        content.append(read_urls(result, max_chars_per_content = 2500))

    return content


if __name__ == "__main__":

    print(search_web("latest technology news"))
