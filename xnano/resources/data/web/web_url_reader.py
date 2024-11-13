import requests
from typing import Union, List, Optional
from pydantic import BaseModel
import json


class WebDocument(BaseModel):
    url: str
    content: Optional[str] = None
    markdown: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    html: Optional[str] = None


def fetch_and_extract(url: str, max_chars: int = 5000) -> WebDocument:
    """
    Fetches a webpage and extracts various content formats (plain text, markdown, HTML)
    with metadata such as title and description.
    """
    import trafilatura

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        response.raise_for_status()
        downloaded = response.text

        extracted_data = None
        markdown_data = None
        html_data = None

        # Optimized extraction using trafilatura
        extracted_data = trafilatura.extract(downloaded, 
                                          include_comments=True,
                                          include_tables=True,
                                          include_images=True,
                                          with_metadata=True,
                                          include_formatting=True,
                                          include_links=True,
                                          deduplicate=True,
                                          output_format='json')

        markdown_data = trafilatura.extract(downloaded, 
                                          include_comments=True,
                                          include_tables=True,
                                          include_images=True,
                                          with_metadata=True,
                                          include_formatting=True,
                                          include_links=True,
                                          deduplicate=True,
                                          output_format='markdown')

        html_data = trafilatura.extract(downloaded, 
                                          include_comments=True,
                                          include_tables=True,
                                          include_images=True,
                                          with_metadata=True,
                                          include_links=True,
                                          deduplicate=True,
                                          output_format='html')

        # Parse extracted data
        if extracted_data:
            extracted_dict = json.loads(extracted_data)
            extracted_txt = extracted_dict.get('text')
            extracted_markdown = extracted_dict.get('markdown') if not markdown_data else markdown_data
            extracted_html = extracted_dict.get('html') if not html_data else html_data
            title = extracted_dict.get('title')
            description = extracted_dict.get('description')
        else:
            extracted_txt = extracted_markdown = extracted_html = title = description = None

        # Construct WebDocument with all extracted data
        return WebDocument(
            url=url,
            content=extracted_txt[:max_chars] if extracted_txt else None,
            markdown=extracted_markdown[:max_chars] if extracted_markdown else None,
            title=title,
            description=description,
            html=extracted_html
        )

    except requests.RequestException as e:
        return WebDocument(url=url, content=f"Request error: {e}")
    except Exception as e:
        return WebDocument(url=url, content=f"Error: {e}")


def web_reader(
    inputs: Union[str, List[str]],
    max_chars_per_content: int = 5000
) -> Union[WebDocument, List[WebDocument]]:
    """
    Fetches and extracts content from one or more URLs, returning results as WebDocument(s).
    """
    if isinstance(inputs, str):
        inputs = [inputs]

    documents = [fetch_and_extract(url, max_chars_per_content) for url in inputs]
    return documents if len(documents) > 1 else documents[0]


if __name__ == "__main__":
    example_urls = [
        "https://example.com",
        "https://www.bbc.com/news/world-60525350",
        "https://www.google.com"
    ]

    results = web_reader(example_urls, max_chars_per_content=5000)

    print(results)