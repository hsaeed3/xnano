import requests
from typing import Union, List, Optional, Any, Sequence
from pydantic import BaseModel
import re


class WebDocument(BaseModel):
    url: str
    content: Optional[str] = None  # Plain text content
    markdown: Optional[str] = None  # Markdown formatted content
    title: Optional[str] = None  # Webpage title
    description: Optional[str] = None  # Meta description
    html: Optional[str] = None  # Cleaned HTML content


class MarkdownifyTransformer:
    """Converts HTML documents to Markdown format with customizable options for handling
    links, images, other tags and heading styles using the markdownify library.
    """

    def __init__(
        self,
        strip: Optional[Union[str, List[str]]] = None,
        convert: Optional[Union[str, List[str]]] = None,
        autolinks: bool = True,
        heading_style: str = "ATX",
        **kwargs: Any,
    ) -> None:
        self.strip = [strip] if isinstance(strip, str) else strip
        self.convert = [convert] if isinstance(convert, str) else convert
        self.autolinks = autolinks
        self.heading_style = heading_style
        self.additional_options = kwargs

        from markdownify import markdownify
        self.markdownify = markdownify

    def transform_documents(
        self,
        documents: Sequence[WebDocument],
        **kwargs: Any,
    ) -> Sequence[WebDocument]:
    
        converted_documents = []
        for doc in documents:
            # Skip markdown conversion if HTML is None
            if doc.html is None:
                converted_documents.append(doc)
                continue
            
            markdown_content = (
                self.markdownify(
                    html=doc.html,
                    strip=self.strip,
                    convert=self.convert,
                    autolinks=self.autolinks,
                    heading_style=self.heading_style,
                    **self.additional_options,
                )
                .replace("\xa0", " ")
                .strip()
            )

            cleaned_markdown = re.sub(r"\n\s*\n", "\n\n", markdown_content)

            converted_documents.append(
                WebDocument(
                    url=doc.url,
                    content=doc.content,
                    markdown=cleaned_markdown,
                    title=doc.title,
                    description=doc.description,
                    html=doc.html
                )
            )

        return converted_documents


def fetch_and_extract(url: str, max_chars: int = 5000) -> WebDocument:
    """
    Fetches a webpage and extracts various content formats (plain text, HTML, Markdown)
    with metadata such as title and description.
    """
    from bs4 import BeautifulSoup
    from readability import Document

    try:
        # Fetch the webpage
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()

        # Parse the webpage with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        title = soup.title.string.strip() if soup.title else None

        # Extract description from meta tags
        meta_description = soup.find("meta", attrs={"name": "description"})
        description = meta_description["content"].strip() if meta_description else None

        # Use readability-lxml to extract clean content and HTML
        doc = Document(response.text)
        readable_html = doc.summary()
        readable_title = doc.title()

        # Extract plain text content
        readable_soup = BeautifulSoup(readable_html, "html.parser")
        for script_or_style in readable_soup(["script", "style"]):
            script_or_style.extract()
        plain_text_content = ' '.join(readable_soup.stripped_strings)

        # Limit content to max_chars
        content = plain_text_content[:max_chars] if plain_text_content else None
        html = readable_html[:max_chars] if readable_html else None

        return WebDocument(
            url=url,
            content=content,
            markdown=None,  # Markdown will be added later
            title=readable_title or title,
            description=description,
            html=html
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

    # Transform HTML to Markdown
    transformer = MarkdownifyTransformer(strip=["a", "img"], autolinks=True, heading_style="ATX")
    documents = transformer.transform_documents(documents)

    return documents if len(documents) > 1 else documents[0]


if __name__ == "__main__":
    example_urls = [
        "https://example.com",
        "https://www.bbc.com/news/world-60525350",
        "https://www.google.com"
    ]

    results = web_reader(example_urls, max_chars_per_content=5000)

    for result in results if isinstance(results, list) else [results]:
        print(result.model_dump_json(indent=4))