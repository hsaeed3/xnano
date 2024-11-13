import requests
from typing import Union, List, Dict

from .._lib import console, XNANOException


# TODO
# build in response model for document response
# model should have document.markdown or document.text or document.html if url scraped
# this is going to be unified into xnano.documents.document_reader.read_documents() return type
# as well as vector store client


def read_urls(
    inputs: Union[str, List[str]],
    max_chars_per_content: int = 5000,
    verbose: bool = False
) -> Union[str, List[Union[str, Dict]]]:
    """
    Fetches content from given URLs and returns nicely formatted text content.
    
    Args:
        inputs (str or list of str): The URLs to process.
        max_chars_per_content (int): Maximum number of characters to return per content.
        verbose (bool): Whether to print verbose output.
    
    Returns:
        str or list of str or dict: The extracted and formatted content.
    """
    from bs4 import BeautifulSoup

    try:
        if isinstance(inputs, str):
            inputs = [inputs]
        
        contents = []
        for url in inputs:
            if url.startswith('http://') or url.startswith('https://'):
                # Fetch content
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', '').split(';')[0]
                    if verbose:
                        console.message(f"Fetched content from URL: {url}, Content-Type: {content_type}")
                    
                    if content_type == 'text/html':
                        # Parse HTML content
                        soup = BeautifulSoup(response.text, 'html.parser')
                        text_content = soup.get_text(separator=' ', strip=True)
                        text_content = text_content[:max_chars_per_content]
                        contents.append(text_content)
                    elif content_type == 'application/pdf':
                        # Read PDF content
                        pdf_content = _read_pdf_from_bytes(response.content)
                        pdf_content = pdf_content[:max_chars_per_content]
                        contents.append(pdf_content)
                    elif content_type == 'text/csv':
                        # Read CSV content
                        csv_content = _read_csv_from_text(response.text)
                        contents.append(csv_content)
                    elif content_type == 'application/json':
                        # Parse JSON content
                        json_content = response.json()
                        contents.append(json_content)
                    elif content_type == 'application/xml' or content_type == 'text/xml':
                        # Parse XML content
                        xml_content = _read_xml_from_text(response.text)
                        contents.append(xml_content)
                    else:
                        # Unknown content type, return as text
                        text_content = response.text[:max_chars_per_content]
                        contents.append(text_content)
                except Exception as e:
                    if verbose:
                        console.message(f"Error fetching URL: {url}, Error: {e}")
                    contents.append(f"Error fetching URL: {url}, Error: {e}")
            else:
                if verbose:
                    console.message(f"Invalid URL: {url}")
                contents.append(f"Invalid URL: {url}")
        
        if len(contents) == 1:
            return contents[0]
        else:
            return contents
    except Exception as e:
        raise XNANOException(f"Error reading URLs: {e}") from e
    

def _read_pdf_from_bytes(pdf_bytes: bytes) -> str:
    """
    Reads PDF content from bytes and extracts text.
    """
    import PyPDF2

    try:
        from io import BytesIO
        pdf_stream = BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_stream)
        text = ''
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() or ''
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
    urls = [
        "https://www.example.com",  # HTML content
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",  # PDF content
        "https://people.sc.fsu.edu/~jburkardt/data/csv/hw_200.csv",  # CSV content
        "https://www.w3schools.com/xml/note.xml",  # XML content
        "https://jsonplaceholder.typicode.com/posts/1",  # JSON content
    ]
    
    results = read_urls(
        urls,
        max_chars_per_content=5000,
        verbose=True
    )
    
    if isinstance(results, list):
        for idx, result in enumerate(results, 1):
            console.message(f"\nResult {idx}:\n{result}")
    else:
        console.message(f"\nResult:\n{results}")
