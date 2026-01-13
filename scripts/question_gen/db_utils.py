import sqlite3
import json
import os
import re
from typing import List, Dict, Any, Tuple

DB_PATH = os.path.join("index", "sqlite_v2.db")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clean_chapter_name(name: str) -> str:
    """
    Removes trailing numbers from chapter names to deduplicate.
    Handles standard spaces, non-breaking spaces, full-width spaces.
    Example: "第6章 投资管理基础 151" -> "第6章 投资管理基础"
    """
    if not name:
        return "Unknown Chapter"
    
    # Regex explanation:
    # [\s\xa0\u3000]+ : Match one or more whitespace characters (including NBSP \xa0 and full-width space \u3000)
    # \d+             : Match one or more digits
    # [\s\xa0\u3000]* : Match zero or more trailing whitespace characters
    # $               : End of string
    return re.sub(r'[\s\xa0\u3000]+\d+[\s\xa0\u3000]*$', '', name).strip()

def fetch_chapter_tree() -> Dict[str, Dict[str, List[str]]]:
    """
    Fetches all unique Book -> Chapter -> Section structures.
    Groups by CLEANED chapter names.
    Returns:
        {
            "BookName": {
                "CleanedChapterName": ["Section1", "Section2", ...]
            }
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # We only need metadata to build the tree
    cursor.execute("SELECT metadata FROM doc_parents")
    rows = cursor.fetchall()
    conn.close()

    tree = {}

    for row in rows:
        try:
            meta = json.loads(row['metadata'])
            book = meta.get('book', 'Unknown Book')
            raw_chapter = meta.get('chapter', 'Unknown Chapter')
            section = meta.get('section', 'Unknown Section')

            # Clean the chapter name
            chapter = clean_chapter_name(raw_chapter)

            if book not in tree:
                tree[book] = {}
            
            if chapter not in tree[book]:
                tree[book][chapter] = []
            
            if section and section not in tree[book][chapter]:
                tree[book][chapter].append(section)
                
        except json.JSONDecodeError:
            continue

    # Sort lists for better UI
    for book in tree:
        for chapter in tree[book]:
            tree[book][chapter].sort()
            
    return tree

def fetch_parent_chunks(chapters: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches parent chunks, optionally filtered by a list of chapters.
    Matches against CLEANED chapter names.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, content, metadata FROM doc_parents"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        try:
            meta = json.loads(row['metadata'])
            raw_chapter = meta.get('chapter', '')
            
            # Clean the chapter name from DB to compare with input selection
            clean_row_chapter = clean_chapter_name(raw_chapter)
            
            # If chapters filter is provided, check if cleaned row's chapter is in the list
            if chapters and clean_row_chapter not in chapters:
                continue
                
            results.append({
                "id": row['id'],
                "content": row['content'],
                "metadata": meta # Keep original metadata including raw chapter
            })
        except:
            continue
            
    return results
