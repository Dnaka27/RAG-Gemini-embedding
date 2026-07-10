def chunk_text(text, max_size=1500, overlap=100):
    """Dynamic character-based chunking, with overlap between chunks.

    When the cut would fall in the middle of a word, it backs up to the
    nearest whitespace before the limit, avoiding splitting a word in half.
    """
    if overlap >= max_size:
        raise ValueError("overlap must be smaller than max_size")

    text = text.strip()
    if len(text) <= max_size:
        return [text]

    chunks = []
    step = max_size - overlap
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
