# this file for parse md , extract YAML from them to embed the .md after, text extracting from pdf,
from typing import List
import re

def word_splitter(source_text: str) -> List[str]:
    # Replace multiple whitespaces with a single space
    source_text = re.sub(r'\s+', ' ', source_text)
    # Split text by single whitespace
    return re.split(r'\s', source_text)

def get_chunks_fixed_size(text: str, chunk_size: int) -> List[str]:
    text_words = word_splitter(text)
    chunks = []
    for i in range(0, len(text_words), chunk_size):
        chunk_words = text_words[i: i + chunk_size]
        chunk = ' '.join(chunk_words)
        chunks.append(chunk)
    return chunks

def get_chunks_fixed_size_with_overlap(text: str, chunk_size: int, overlap_fraction: float) -> List[str]:
    text_words = word_splitter(text)
    overlap_int = int(chunk_size * overlap_fraction)
    chunks = []
    for i in range(0, len(text_words), chunk_size):
        start_index = max(i - overlap_int, 0)
        end_index = i + chunk_size
        chunk_words = text_words[start_index: end_index]
        chunk = ' '.join(chunk_words)
        chunks.append(chunk)
    return chunks



