import os
import json
import sqlite3
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
FAISS_INDEX_DIR = os.path.join(INDEX_DIR, "faiss_v2")
SQLITE_DB_PATH = os.path.join(INDEX_DIR, "sqlite_v2.db")

PARENTS_FILE = os.path.join(DATA_DIR, "parents.jsonl")
CHILDREN_FILE = os.path.join(DATA_DIR, "children.jsonl")

def load_jsonl(file_path: str) -> List[Dict]:
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line))
    return data

def build_sqlite_v2(parents: List[Dict], children: List[Dict]):
    """
    Builds SQLite DB with:
    1. doc_parents (Regular Table): id, content, metadata (json)
    2. doc_children_fts (FTS Table): content, parent_id, metadata (json)
    """
    print("--- Building SQLite V2 ---")
    
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 1. Parent Table (Regular)
    cursor.execute('''
        CREATE TABLE doc_parents (
            id TEXT PRIMARY KEY,
            content TEXT,
            metadata TEXT
        )
    ''')
    
    # 2. Child FTS Table (Virtual)
    cursor.execute('''
        CREATE VIRTUAL TABLE doc_children_fts USING fts5(
            content,
            parent_id,
            metadata
        )
    ''')
    
    # Insert Parents
    print(f"Inserting {len(parents)} parents...")
    parent_data = [
        (p['parent_id'], p['content'], json.dumps(p['metadata'], ensure_ascii=False))
        for p in parents
    ]
    cursor.executemany('INSERT INTO doc_parents VALUES (?, ?, ?)', parent_data)
    
    # Insert Children
    print(f"Inserting {len(children)} children to FTS...")
    child_data = [
        (c['content'], c['parent_id'], json.dumps(c['metadata'], ensure_ascii=False))
        for c in children
    ]
    cursor.executemany('INSERT INTO doc_children_fts VALUES (?, ?, ?)', child_data)
    
    conn.commit()
    conn.close()
    print(f"SQLite V2 saved to {SQLITE_DB_PATH}")

def build_faiss_v2(children: List[Dict]):
    """
    Builds FAISS index for Children.
    Metadata includes 'parent_id' for mapping.
    """
    print("--- Building FAISS V2 (Children) ---")
    
    documents = []
    for c in children:
        meta = c['metadata'].copy()
        meta['parent_id'] = c['parent_id'] # Crucial for mapping
        
        doc = Document(
            page_content=c['content'],
            metadata=meta
        )
        documents.append(doc)
        
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    print(f"Embedding {len(documents)} children...")
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)
        
    vectorstore.save_local(FAISS_INDEX_DIR)
    print(f"FAISS V2 saved to {FAISS_INDEX_DIR}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found.")
        exit(1)
        
    parents = load_jsonl(PARENTS_FILE)
    children = load_jsonl(CHILDREN_FILE)
    
    build_sqlite_v2(parents, children)
    build_faiss_v2(children)



