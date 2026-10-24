# this file to embed the required data to the vector db
from typing import List
from chunking.vectordb_handlers import pdf_chunking, md_chunking, get_all_files_by_ex
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

def get_course_documents() -> List[Document]:
    """Loads all 30 course markdown files into LangChain Document objects."""
    courses_files = get_all_files_by_ex("data/lms/course_pages", "md")
    docs = []
    for f in courses_files:
        c = md_chunking(f)
        meta = c.get("metadata", {})
        text = (
            f"Course ID: {meta.get('course_id')}\n"
            f"Title (EN): {meta.get('title_en')}\n"
            f"Title (AR): {meta.get('title_ar')}\n"
            f"Skills: {meta.get('skills')}\n"
            f"{c['text']}"
        )
        docs.append(Document(
            page_content=text,
            metadata=meta,
            id=str(c.get("id"))
        ))
    return docs

def get_policy_documents() -> List[Document]:
    """Chunks the learning and development policy PDF into LangChain Document objects."""
    policy_pdf_path = "data/policy/learning_and_development_policy.pdf"
    chunks = pdf_chunking(chunk_size=120, overlap_fraction=0.15, pdf_path=policy_pdf_path, doc_type="policy")
    docs = []
    for c in chunks:
        docs.append(Document(
            page_content=c["text"],
            metadata=c["metadata"],
            id=str(c["id"])
        ))
    return docs

def get_vectorstore(collection_name: str, docs: List[Document] = None) -> Chroma:
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma(
        collection_name=collection_name,
        persist_directory="data/vector_db",
        embedding_function=embeddings
    )
    if docs and vectorstore._collection.count() == 0:
        vectorstore.add_documents(docs)
    return vectorstore

def retrieve_courses(target: str, top_k: int = 10, sparse_weight: float = 0.3, dense_weight: float = 0.7) -> List[Document]:
    """
    Hybrid retriever (BM25 + Dense Chroma) searching strictly within the course catalogue.
    """
    docs = get_course_documents()
    vectorstore = get_vectorstore("courses_collection", docs)
    
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = top_k
    
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, dense_retriever],
        weights=[sparse_weight, dense_weight]
    )
    return hybrid_retriever.invoke(target)

# Alias for backwards compatibility with filters/__init__.py
embedder_retriever = retrieve_courses

def retrieve_policy(target: str, top_k: int = 5) -> List[Document]:
    """
    Dense retriever searching strictly within company policy documents.
    """
    docs = get_policy_documents()
    vectorstore = get_vectorstore("policies_collection", docs)
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    return retriever.invoke(target)

# if __name__ == "__main__":
#     print("--- Testing Course Retrieval ---")
#     course_results = retrieve_courses("I'd like to be a Finance Manager one day. What should I be learning next?", top_k=5)
#     for i, doc in enumerate(course_results):
#         print(f"{i}: {doc.metadata.get('course_id')} - {doc.metadata.get('title_en')}")

#     print("\n--- Testing Policy Retrieval ---")
#     policy_results = retrieve_policy("I'd like to be a Finance Manager one day. What should I be learning next?", top_k=2)
#     for i, doc in enumerate(policy_results):
#         print(f"Policy Chunk {i} [{doc.metadata.get('source')}]:\n{doc.page_content[:150]}...\n")
