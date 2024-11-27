# pre-built llm tools

__all__ = ["web_search"]

from typing import List, Union, Dict, Optional


# search web tool
def web_search(
    query: str,
    max_results: int = 10,
    verbose: bool = False,
    max_chars_per_content: int = 2500,
    batch_size: int = 5
) -> Dict[str, Union[str, List[str]]]:
    """
    Searches the web for a query and returns the results in a dictionary.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        verbose: Whether to print progress
        max_chars_per_content: Maximum number of characters to return per content
        batch_size: Number of results to fetch per batch
    """
    from .web_url_searcher import web_url_search
    from .web_url_reader import web_reader

    if verbose:
        print(f"Searching the web for: {query}")

    # Get URLs in batches
    results = web_url_search(query, max_results, batch_size=batch_size, verbose=verbose)

    if not results:
        return {"error": "No results found."}

    returned_results = {}

    # Process content in batches
    for i in range(0, len(results), batch_size):
        batch_urls = results[i:i + batch_size]
        if verbose:
            print(f"Processing batch of {len(batch_urls)} URLs")
            
        batch_content = web_reader(
            batch_urls,
            max_chars_per_content=max_chars_per_content,
            batch_size=batch_size
        )
        
        # Add batch results to returned_results
        for url, content in zip(batch_urls, batch_content if isinstance(batch_content, list) else [batch_content]):
            returned_results[url] = content

    if verbose:
        print(f"Completed processing {len(returned_results)} results")

    return returned_results


if __name__ == "__main__":
    results = web_search("latest technology news", max_results=5, verbose=True)
    for url, content in results.items():
        print(f"\nContent from {url}:\n{content}")
