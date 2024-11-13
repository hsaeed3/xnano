from typing import List, Optional


def web_url_search(
    query: str, max_results: int = 10, verbose: bool = False
) -> List[str]:
    """
    Performs a web search using DuckDuckGo and returns the links of the search results.

    Example:
    ```python
    links = web_search("latest technology news")
    ```

    Returns:
        List[str]: A list of links to the search results.
    """
    from duckduckgo_search import DDGS

    client = DDGS()

    if verbose:
        print(f"Performing web search for query: {query}")

    results = client.text(query, max_results=max_results)
    if not results:
        if verbose:
            print("No search results found.")
        return []

    links = [result["href"] for result in results if "href" in result]
    if verbose:
        print(f"Found {len(links)} links from search results.")
    return links


if __name__ == "__main__":
    print(web_url_search("latest technology news"))
