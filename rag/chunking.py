def chunk_text(text, max_size=1500, overlap=100):
    """Chunking dinâmico por caracteres, com sobreposição entre blocos.

    Quando o corte cairia no meio de uma palavra, recua até o espaço em
    branco mais próximo antes do limite, evitando quebrar uma palavra ao meio.
    """
    if overlap >= max_size:
        raise ValueError("overlap deve ser menor que max_size")

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
