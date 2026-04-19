def chunk_text(text: str, page_number: int, file_id: str,
               chunk_size: int = 500,
               overlap: int = 200):
    """
    Chunk berbasis karakter.
    500 karakter dengan overlap 200.
    """

    chunks = []
    step = chunk_size - overlap
    text_length = len(text)

    start = 0
    chunk_index = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        chunk_content = text[start:end].strip()

        # Hindari chunk terlalu kecil (misalnya < 50 karakter)
        if len(chunk_content) >= 50:
            chunks.append({
                "chunk_id": f"{file_id}_p{page_number}_c{chunk_index}",
                "file_id": file_id,
                "page": page_number,
                "start_char": start,
                "end_char": end,
                "content": chunk_content
            })

            chunk_index += 1

        start += step

    return chunks
