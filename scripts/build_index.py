import os
import json
import sqlite3
import shutil
from typing import List, Dict
from dotenv import load_dotenv

# LangChain Imports
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# Load env
load_dotenv()

# Config
DATA_DIR = "data"
INDEX_DIR = "index"
FAISS_INDEX_DIR = os.path.join(INDEX_DIR, "faiss")
SQLITE_DB_PATH = os.path.join(INDEX_DIR, "sqlite_fts.db")

CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.jsonl")
TABLE_CHUNKS_FILE = os.path.join(DATA_DIR, "table_chunks.jsonl")

def load_chunks() -> List[Dict]:
    """Load all chunks from JSONL files."""
    chunks = []
    
    # Load Text Chunks
    if os.path.exists(CHUNKS_FILE):
        with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))
    
    # Load Table Chunks
    if os.path.exists(TABLE_CHUNKS_FILE):
        with open(TABLE_CHUNKS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))
                
    print(f"Total chunks loaded: {len(chunks)}")
    return chunks

def build_faiss_index(chunks: List[Dict]):
    """Builds and saves FAISS vector index."""
    print("--- Building FAISS Index ---")
    
    # Prepare Documents for LangChain
    documents = []
    for chunk in chunks:
        # Create metadata dict
        metadata = {
            "book": chunk.get("book"),
            "chapter": chunk.get("chapter"),
            "section": chunk.get("section"),
            "figure_ref": chunk.get("figure_ref"),
            "chunk_type": chunk.get("chunk_type"),
            "exam_priority": chunk.get("exam_priority")
        }
        
        doc = Document(
            page_content=chunk["content"],
            metadata=metadata
        )
        documents.append(doc)
    
    # Initialize Embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small") # Cost-effective model
    
    # Create VectorStore
    # Using from_documents will call OpenAI API to get embeddings
    print(f"Generating embeddings for {len(documents)} documents. This may take a while...")
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    # Save
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)
        
    vectorstore.save_local(FAISS_INDEX_DIR)
    print(f"FAISS index saved to {FAISS_INDEX_DIR}")

def build_sqlite_fts_index(chunks: List[Dict]):
    """Builds SQLite FTS5 Full-Text Search index."""
    print("--- Building SQLite FTS5 Index ---")
    
    # Reset DB
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # Create FTS5 Table
    # content, book, chapter, section, figure_ref
    # We use 'tokenize="jieba"' or 'trigram' if available, but default 'porter' is for English.
    # For Chinese in SQLite FTS5, we often just use standard tokenizer or trigram if compiled.
    # Here we use default. For better Chinese support, we might need pre-segmentation,
    # but for simplicity we rely on standard FTS matching or simple space-segmentation if needed.
    # To improve simple Chinese matching without extensions: we can insert text as-is.
    
    cursor.execute('''
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            content,
            book,
            chapter,
            section,
            figure_ref,
            chunk_type,
            exam_priority UNINDEXED
        )
    ''')
    
    # Batch Insert
    data_to_insert = []
    for chunk in chunks:
        data_to_insert.append((
            chunk["content"],
            chunk.get("book", ""),
            chunk.get("chapter", ""),
            chunk.get("section", ""),
            chunk.get("figure_ref", "") or "", # Handle None
            chunk.get("chunk_type", ""),
            chunk.get("exam_priority", 1)
        ))
        
    cursor.executemany('''
        INSERT INTO docs_fts (content, book, chapter, section, figure_ref, chunk_type, exam_priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data_to_insert)
    
    conn.commit()
    conn.close()
    print(f"SQLite FTS5 index saved to {SQLITE_DB_PATH}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file.")
        exit(1)
        
    all_chunks = load_chunks()
    
    # Build both indices
    build_faiss_index(all_chunks)
    build_sqlite_fts_index(all_chunks)



