# llm usable tools

from ..data._routing import (
    web_search,
    web_news_search,
    web_reader,
)
from typing import Dict


class Tools:
    @staticmethod
    def web_search(query: str, max_results: int) -> Dict:
        """
        A tool to search the web and return a dictionary of results

        Args:
            query (str): The query to search the web with
            max_results (int): The maximum number of results to return

        Returns:
            Dict: A dictionary containing the search results
        """
        return web_search(query, 3)

    @staticmethod
    def news_search(query: str, max_results: int) -> Dict:
        """
        A tool to search the web for news and return a dictionary of results

        Args:
            query (str): The query to search the web with
            max_results (int): The maximum number of results to return

        Returns:
            Dict: A dictionary containing the search results
        """
        return web_news_search(query, max_results)

    @staticmethod
    def url_reader(url: str) -> str:
        """
        A tool to read the content of a web page and return a string of the content

        Args:
            url (str): The URL of the web page to read

        Returns:
            str: A string containing the content of the web page
        """
        return web_reader(url)
