from typing import List, Optional


def web_url_search(
    query: str, max_results: int = 10, batch_size: int = 5, verbose: bool = False
) -> List[str]:
    """
    Performs a web search using DuckDuckGo and returns the links in batches.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        batch_size: Number of results to fetch per batch
        verbose: Whether to print progress
    """
    from duckduckgo_search import DDGS
    
    client = DDGS()
    all_links = []
    remaining = max_results

    if verbose:
        print(f"Performing web search for query: {query}")

    # Process in batches
    while remaining > 0:
        current_batch = min(batch_size, remaining)
        results = client.text(query, max_results=current_batch)
        
        if not results:
            break
            
        batch_links = [result["href"] for result in results if "href" in result]
        all_links.extend(batch_links)
        
        if verbose:
            print(f"Fetched batch of {len(batch_links)} links")
            
        remaining -= len(batch_links)
        
    if verbose:
        print(f"Found total of {len(all_links)} links")
        
    return all_links[:max_results]


if __name__ == "__main__":
    print(web_url_search("latest technology news"))
