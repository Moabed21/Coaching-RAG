import pymupdf
import frontmatter
import pandas as pd
from typing import List, Dict, Any
from chunking.chunk import get_chunks_fixed_size_with_overlap
from pathlib import Path

# we use clean_metadata function for both pdf and md files cuz vectordb does not support list in metadata and some metadata are like tags in md files
def clean_metadata(meta: dict) -> dict:
    cleaned = {}
    for k, v in meta.items():
        if isinstance(v, list):
            cleaned[k] = ", ".join(map(str, v))  # convert list to string
        elif v is None:
            cleaned[k] = ""
        else:
            cleaned[k] = v
    return cleaned

def pdf_chunking(chunk_size: int, overlap_fraction: float, pdf_path: str, doc_type: str = "policy") -> List[Dict[str, Any]]:
    try:
        doc = pymupdf.open(pdf_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error opening PDF file: {e}")

    policy_text = ""
    for page in doc:
        policy_text += page.get_text() + "\n"
    doc.close()
    raw_chunks = get_chunks_fixed_size_with_overlap(policy_text, chunk_size, overlap_fraction)

    # Attach metadata to each chunk
    chunks_with_metadata: List[Dict[str, Any]] = []
    for i, chunk_text in enumerate(raw_chunks, 1):
        chunks_with_metadata.append({
            "id": f"{doc_type}_chunk_{i}",
            "text": chunk_text,
            "metadata": {
                "source": pdf_path,
                "doc_type": doc_type,
                "chunk_index": i,
            }
        })

    
    for i in chunks_with_metadata:
        i["metadata"] = clean_metadata(i["metadata"])
    return chunks_with_metadata
        
def md_chunking(file: str) -> Dict[str, Any]:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error opening markdown file: {e}")
    post = frontmatter.loads(md_text)
    doc_id = post.metadata.get("course_id") or post.metadata.get("role_profile_id")
    final ={
        'id' : doc_id,
        'text': post.content,
        'metadata': clean_metadata(post.metadata)
    }
    return final


def get_all_files_by_ex(folder_path: str, ext: str) -> List[str]:
    # glob means to find files matching a pattern
    files = [str(f) for f in Path(folder_path).glob(f"*.{ext}")]
    return files


def csv_chunking(file: str) -> Dict[str, Any]:
    try:
        df = pd.read_csv(file)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error opening CSV file: {e}")
    return df.to_dict(orient="records")

