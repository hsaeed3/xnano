from pathlib import Path
from typing import Union, List, Dict, Optional, Literal
from ....lib import XNANOException, console

from ....types.data.document import Document
from ...models.mixin import GenerativeModel, patch


def text_reader(
    path: Union[str, Path, List[Union[str, Path]]],
    workers: Optional[int] = None,
    target: Literal["text", "json", "markdown"] = "text",
    string: bool = False,
    verbose: bool = False,
) -> Union[str, Document, List[Document], List[str], GenerativeModel, List[GenerativeModel]]:
    from concurrent.futures import ThreadPoolExecutor
    import os
    import multiprocessing as mp

    paths = [_download_if_url(p) for p in (path if isinstance(path, list) else [path])]
    paths = [Path(p) for p in paths]

    try:
        if len(paths) == 1 and paths[0].is_file():
            content = _read_single_file(paths[0], target, verbose)
            if string:
                return content
            return Document(text=content, metadata={"source": str(paths[0])})
        else:
            with console.progress(
                "Reading Files...",
            ) as progress:
                task_id = progress.add_task("Reading Files...", total=len(paths))

                with ThreadPoolExecutor(
                    max_workers=workers or mp.cpu_count()
                ) as executor:
                    futures = [
                        executor.submit(_read_single_file, file, target, verbose)
                        for p in paths
                        for file in (p.glob("*") if p.is_dir() else [p])
                        if file.is_file()
                    ]
                    results = []
                    for future in futures:
                        result = future.result()
                        if result is not None:
                            if string:
                                results.append(result)
                            else:
                                results.append(
                                    Document(text=result, metadata={"source": str(p)})
                                )
                        progress.update(task_id, advance=1)
                    return (
                        "\n".join(results)
                        if string
                        else patch(result for result in results)
                    )
    finally:
        for p in paths:
            if str(p).startswith("/tmp/") and p.is_file():
                try:
                    os.remove(p)
                except Exception as e:
                    if verbose:
                        print(f"Error removing temporary file {p}: {str(e)}")


def _download_if_url(path: Union[str, Path]) -> Union[str, Path]:
    from urllib.parse import urlparse
    import requests
    import mimetypes
    import uuid

    if isinstance(path, str) and urlparse(path).scheme in ("http", "https"):
        response = requests.get(path)
        response.raise_for_status()
        filename = Path(urlparse(path).path).name or "downloaded_file"
        if not Path(filename).suffix:
            content_type = response.headers.get("Content-Type")
            if content_type:
                extension = mimetypes.guess_extension(content_type.split(";")[0])
                if extension:
                    filename += extension
        local_path = Path("/tmp") / f"{uuid.uuid4()}_{filename}"
        local_path.write_bytes(response.content)
        return local_path
    return path


def _read_single_file(
    path: Path, target: str = "text", verbose: bool = False
) -> Union[str, Dict, None]:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = _guess_mime_type(path)

    try:
        content = _read_file_content(path, mime_type)
        return _format_content(content, target, mime_type)
    except Exception as e:
        if verbose:
            print(f"Error reading file {path}: {str(e)}")
        return None


def _guess_mime_type(path: Path) -> str:
    import json

    with path.open("rb") as f:
        header = f.read(5)
        if header == b"%PDF-":
            return "application/pdf"
        elif header[:2] == b"PK":
            file_content = f.read()
            if b"word/" in file_content:
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif b"xl/" in file_content:
                return (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    try:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)
        return "application/json"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return "text/plain" if path.suffix == ".md" else "application/octet-stream"


def _read_file_content(path: Path, mime_type: str) -> Union[str, List, Dict]:
    if mime_type == "application/pdf":
        return _read_pdf(path)
    elif mime_type == "text/csv":
        return _read_csv(path)
    elif mime_type == "application/json":
        return _read_json(path)
    elif mime_type.startswith("text/"):
        return _read_text(path)
    elif mime_type == "application/xml":
        return _read_xml(path)
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _read_docx(path)
    elif (
        mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        return _read_xlsx(path)
    else:
        return f"Binary file: {path.name}"


def _read_json(path: Path) -> Dict:
    """
    Reads JSON files and returns their content as a dictionary.
    """
    import json

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        raise XNANOException(f"Error reading JSON {path}: {str(e)}")


def _read_pdf(path: Path) -> str:
    """
    Extracts text from a PDF, including proper formatting for tables and paragraphs.
    """
    import PyPDF2

    try:
        with open(path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                extracted_text = page.extract_text() or ""
                # Additional handling for simple table formatting
                # We'll assume columns are separated by enough space to infer table-like structures
                text += _format_pdf_text(extracted_text)
        return text.strip()
    except Exception as e:
        raise XNANOException(f"Error reading PDF {path}: {str(e)}")


def _format_pdf_text(extracted_text: str) -> str:
    """
    Post-process PDF extracted text to ensure proper formatting for tables, paragraphs, etc.
    This function attempts to identify and format tables, preserve paragraph structure,
    and handle common PDF extraction issues.
    """
    lines = extracted_text.split("\n")
    formatted_lines = []
    in_table = False
    table_column_widths = []

    for line in lines:
        stripped_line = line.strip()

        # Detect table start/end
        if "  " in line and not in_table:
            in_table = True
            table_column_widths = [len(col) for col in line.split()]
        elif in_table and not any(
            len(word) > width for word, width in zip(line.split(), table_column_widths)
        ):
            in_table = False

        if in_table:
            # Format table rows
            columns = line.split()
            formatted_line = " | ".join(
                col.ljust(width) for col, width in zip(columns, table_column_widths)
            )
            formatted_lines.append(formatted_line)
        elif stripped_line:
            # Handle regular text, attempting to preserve paragraph structure
            if formatted_lines and not formatted_lines[-1].endswith(
                (".", "!", "?", ":", ";")
            ):
                formatted_lines[-1] += " " + stripped_line
            else:
                formatted_lines.append(stripped_line)
        else:
            # Preserve empty lines between paragraphs
            if formatted_lines and formatted_lines[-1].strip():
                formatted_lines.append("")

    # Post-processing: remove redundant empty lines and fix common OCR issues
    cleaned_lines = []
    for line in formatted_lines:
        cleaned_line = line.replace(" |", "|").replace(
            "| ", "|"
        )  # Clean up table formatting
        cleaned_line = cleaned_line.replace("l", "I").replace(
            "0", "O"
        )  # Common OCR fixes
        if cleaned_line or (cleaned_lines and cleaned_lines[-1]):
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def _read_csv(path: Path) -> List[List[str]]:
    """
    Reads CSV data.
    """
    import csv

    try:
        with open(path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            return list(reader)
    except Exception as e:
        raise XNANOException(f"Error reading CSV {path}: {str(e)}")


def _read_text(path: Path) -> str:
    """
    Reads plain text files.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        raise XNANOException(f"Error reading text file {path}: {str(e)}")


def _read_xml(path: Path) -> Dict:
    """
    Reads XML files and converts them to a dictionary.
    """
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return _element_to_dict(root)
    except Exception as e:
        raise XNANOException(f"Error reading XML {path}: {str(e)}")


def _read_binary(path: Path) -> str:
    return f"Binary file: {path.name}"


def _element_to_dict(element):
    """
    Recursively converts XML elements to a dictionary.
    """
    result = {}
    for child in element:
        if len(child) == 0:
            result[child.tag] = child.text
        else:
            result[child.tag] = _element_to_dict(child)
    return result


def _format_content(
    content: Union[str, List, Dict], target: str, mime_type: str
) -> Union[str, Dict]:
    import json

    if target == "json" and mime_type == "application/json":
        return content
    elif target == "markdown":
        return _to_markdown(content)
    else:
        return content if isinstance(content, str) else json.dumps(content, indent=2)


def _to_markdown(content: Union[str, List, Dict]) -> str:
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        return "\n".join([" | ".join(map(str, row)) for row in content])
    elif isinstance(content, dict):
        return "\n".join([f"**{k}**: {v}" for k, v in content.items()])
    else:
        return str(content)


def _read_docx(path: Path) -> str:
    """
    Reads DOCX files and extracts text content.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(path, "r") as docx:
            xml_content = docx.read("word/document.xml")
            tree = ET.ElementTree(ET.fromstring(xml_content))
            paragraphs = []
            for elem in tree.iter():
                if elem.tag.endswith("}t"):  # Text element
                    paragraphs.append(elem.text)
            return "\n".join(paragraphs)
    except Exception as e:
        raise XNANOException(f"Error reading DOCX {path}: {str(e)}")


def _read_xlsx(path: Path) -> List[List[str]]:
    """
    Reads XLSX files and extracts sheet data.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(path, "r") as xlsx:
            shared_strings = []
            if "xl/sharedStrings.xml" in xlsx.namelist():
                xml_content = xlsx.read("xl/sharedStrings.xml")
                tree = ET.ElementTree(ET.fromstring(xml_content))
                for elem in tree.iter():
                    if elem.tag.endswith("}t"):  # Text element
                        shared_strings.append(elem.text)

            sheet_data = []
            for sheet in xlsx.namelist():
                if sheet.startswith("xl/worksheets/sheet") and sheet.endswith(".xml"):
                    xml_content = xlsx.read(sheet)
                    tree = ET.ElementTree(ET.fromstring(xml_content))
                    rows = []
                    for row in tree.iter():
                        if row.tag.endswith("}row"):
                            cells = []
                            for cell in row:
                                if cell.tag.endswith("}v"):
                                    value = cell.text
                                    if cell.attrib.get("t") == "s":  # Shared string
                                        value = shared_strings[int(value)]
                                    cells.append(value)
                            rows.append(cells)
                    sheet_data.append(rows)
            return sheet_data
    except Exception as e:
        raise XNANOException(f"Error reading XLSX {path}: {str(e)}")


if __name__ == "__main__":
    print(text_reader("https://arxiv.org/pdf/2406.14928"))
