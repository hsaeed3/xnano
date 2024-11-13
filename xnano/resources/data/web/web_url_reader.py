import requests
from typing import Union, List, Dict, Optional
from pydantic import BaseModel as PydanticBaseModel
from ...models.mixin import patch

from ...._lib import console, XNANOException


class WebDocument(PydanticBaseModel):
    url: str
    content: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None


def web_reader(
    inputs: Union[str, List[str]],
    max_chars_per_content: int = 5000,
    verbose: bool = False,
) -> Union[WebDocument, List[WebDocument]]:
    """
    Fetches content from given URLs and returns nicely formatted text content.

    Args:
        inputs (str or list of str): The URLs to process.
        max_chars_per_content (int): Maximum number of characters to return per content.
        verbose (bool): Whether to print verbose output.

    Returns:
        WebDocument or list of WebDocument: The extracted and formatted content.
    """
    from bs4 import BeautifulSoup

    try:
        if isinstance(inputs, str):
            inputs = [inputs]

        contents = []
        for url in inputs:
            if url.startswith("http://") or url.startswith("https://"):
                # Fetch content
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").split(";")[
                        0
                    ]
                    if verbose:
                        console.message(
                            f"Fetched content from URL: {url}, Content-Type: {content_type}"
                        )

                    web_doc = WebDocument(url=url)  # Initialize WebDocument with URL

                    if content_type == "text/html":
                        # Parse HTML content
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Remove navigation, footer, header, and aside elements to focus on main content
                        for nav in soup.find_all(["nav", "footer", "header", "aside"]):
                            nav.decompose()

                        # Extract the main content while preserving the structure
                        main_content = soup.find(
                            "main"
                        )  # Attempt to find a <main> tag for primary content
                        if main_content:
                            text_content = main_content.get_text(
                                separator=" ", strip=True
                            )
                        else:
                            text_content = soup.get_text(
                                separator=" ", strip=True
                            )  # Fallback to entire text if <main> not found

                        # Limit the content to the specified maximum character count
                        text_content = text_content[:max_chars_per_content]
                        web_doc.content = text_content  # Set content in WebDocument
                        web_doc.html = response.text  # Store the raw HTML
                        web_doc.markdown = _convert_to_markdown(
                            text_content
                        )  # Convert to markdown

                    elif content_type == "application/pdf":
                        # Read PDF content
                        pdf_content = _read_pdf_from_bytes(response.content)
                        pdf_content = pdf_content[:max_chars_per_content]
                        web_doc.content = pdf_content  # Set content in WebDocument
                    elif content_type == "text/csv":
                        # Read CSV content
                        csv_content = _read_csv_from_text(response.text)
                        web_doc.content = csv_content  # Set content in WebDocument
                    elif content_type == "application/json":
                        # Parse JSON content
                        json_content = response.json()
                        web_doc.content = json_content  # Set content in WebDocument
                    elif (
                        content_type == "application/xml" or content_type == "text/xml"
                    ):
                        # Parse XML content
                        xml_content = _read_xml_from_text(response.text)
                        web_doc.content = xml_content  # Set content in WebDocument
                    else:
                        # Unknown content type, return as text
                        text_content = response.text[:max_chars_per_content]
                        web_doc.content = text_content  # Set content in WebDocument

                    contents.append(web_doc)  # Append WebDocument to contents
                except Exception as e:
                    if verbose:
                        console.message(f"Error fetching URL: {url}, Error: {e}")
                    contents.append(
                        WebDocument(
                            url=url, content=f"Error fetching URL: {url}, Error: {e}"
                        )
                    )
            else:
                if verbose:
                    console.message(f"Invalid URL: {url}")
                contents.append(WebDocument(url=url, content=f"Invalid URL: {url}"))

        if len(contents) == 1:
            return contents[patch(0)]
        else:
            return [patch(content) for content in contents]
    except Exception as e:
        raise XNANOException(f"Error reading URLs: {e}") from e


def _convert_to_markdown(content: str) -> str:
    """
    Converts the given content to an enhanced markdown format.

    This function applies advanced formatting to the input text, including:
    - Proper line breaks
    - Escaping special markdown characters
    - Converting URLs to markdown links

    Args:
        content (str): The content to convert to markdown.

    Returns:
        str: The converted markdown string.
    """
    import re

    # Escape markdown special characters
    escaped_content = re.sub(r"([\\`*_{}\[\]()#+\-.!])", r"\\\1", content)

    # Convert URLs to markdown links
    escaped_content = re.sub(r"(https?://\S+)", r"<\1>", escaped_content)

    # Replace single newline with markdown line break
    markdown_content = escaped_content.replace("\n", "  \n")

    return markdown_content


def _read_pdf_from_bytes(pdf_bytes: bytes) -> str:
    """
    Reads PDF content from bytes and extracts text.
    """
    import PyPDF2

    try:
        from io import BytesIO

        pdf_stream = BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_stream)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        raise XNANOException(f"Error reading PDF content: {e}") from e


def _read_csv_from_text(csv_text: str) -> List[List[str]]:
    """
    Reads CSV content from text.
    """
    import csv

    try:
        from io import StringIO

        f = StringIO(csv_text)
        reader = csv.reader(f)
        return list(reader)
    except Exception as e:
        raise XNANOException(f"Error reading CSV content: {e}") from e


def _read_xml_from_text(xml_text: str) -> Dict:
    """
    Reads XML content from text and converts it to a dictionary.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
        return _element_to_dict(root)
    except Exception as e:
        raise XNANOException(f"Error reading XML content: {e}") from e


def _element_to_dict(element):
    """
    Recursively converts XML elements to a dictionary.
    """
    result = {}
    for child in element:
        if len(child):
            result[child.tag] = _element_to_dict(child)
        else:
            result[child.tag] = child.text
    return result


if __name__ == "__main__":
    # Example usage
    example_urls = [
        "https://example.com",  # Sample HTML page
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",  # Sample PDF file
        "https://people.sc.fsu.edu/~jburkardt/data/csv/hw_200.csv",  # Sample CSV file
        "https://www.w3schools.com/xml/note.xml",  # Sample XML file
        "https://jsonplaceholder.typicode.com/posts/1",  # Sample JSON API
    ]

    fetched_results = web_reader(example_urls, max_chars_per_content=5000, verbose=True)

    for index, result in enumerate(fetched_results, start=1):
        console.message(f"\nResult {index}:\n{result.content}")

    print
