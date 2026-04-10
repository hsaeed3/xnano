# simple web scraping / search tools
# defaults to tavily api

from tavily import TavilyClient, AsyncTavilyClient

from typing import Dict, List


def web_reader(
    url: str,
) -> str:
    """
    A simple tool that uses the Tavily API to read the content of a web page and return a string of the content
    """

    client = TavilyClient()

    return client.extract_content(url)


def web_search(query: str, max_results: int = 3) -> Dict:
    """
    A simple tool that uses the Tavily API to search the web and return a list of results

    For more advance search capabilities, consider importing the `TavilyClient` class directly.
    """

    # ensure key is at env level as TAVILY_API_KEY
    client = TavilyClient()

    return client.search(query=query, max_results=max_results, topic="general")


if __name__ == "__main__":
    print(web_search("latest technology news"))


def web_news_search(query: str, max_results: int = 3) -> Dict:
    """
    A simple tool that uses the Tavily API to search the web and return a list of news results

    For more advance search capabilities, consider importing the `TavilyClient` class directly.
    """

    client = TavilyClient()

    return client.search(query, max_results, topic="news")


async def async_web_search(query: str, max_results: int = 3) -> Dict:
    """
    An async version of the `web_search` function

    For more advance search capabilities, consider importing the `AsyncTavilyClient` class directly.
    """

    client = AsyncTavilyClient()

    return await client.search(query=query, max_results=max_results, topic="general")


async def async_web_news_search(query: str, max_results: int = 3) -> Dict:
    """
    An async version of the `web_news_search` function

    For more advance search capabilities, consider importing the `AsyncTavilyClient` class directly.
    """

    client = AsyncTavilyClient()

    return await client.search(query=query, max_results=max_results, topic="news")


async def async_web_reader(url: str) -> str:
    client = AsyncTavilyClient()

    return await client.extract_content(url)
