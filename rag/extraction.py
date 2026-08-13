from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_EXTENSION = ".pdf"


def extract_text(document):
    """Extract UTF-8 text from an uploaded .md, .txt, or .pdf file."""
    document.seek(0)
    if document.name.lower().endswith(PDF_EXTENSION):
        return _extract_pdf(document)
    return document.read().decode("utf-8")


def _extract_pdf(document):
    try:
        reader = PdfReader(document)
    except PdfReadError as exc:
        raise ValueError("The PDF could not be read. It may be corrupted.") from exc
    if reader.is_encrypted:
        raise ValueError("The PDF is password-protected.")
    pages = (page.extract_text() or "" for page in reader.pages)
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not text.strip():
        raise ValueError("No extractable text was found in the PDF.")
    return text
