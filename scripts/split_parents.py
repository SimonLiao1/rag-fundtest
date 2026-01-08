import re
import uuid
import json
from typing import List, Dict

# Config
PARENT_MIN_LEN = 300
PARENT_TARGET_LEN = 1000
PARENT_MAX_LEN = 2000

def split_text_smart(text: str, max_len: int) -> List[str]:
    """
    Splits text into chunks respecting semantic boundaries (lists, paragraphs).
    Prioritizes not breaking lists like (1)... (2)... or 一、... 二、...
    """
    if len(text) <= max_len:
        return [text]
        
    chunks = []
    current_chunk = []
    current_len = 0
    
    # Split by paragraphs first
    paragraphs = text.split('\n')
    
    # Heuristics for list items
    list_pattern = re.compile(r'^(\(\d+\)|\d+\.|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）)')
    
    for p in paragraphs:
        p_len = len(p)
        
        # If adding this paragraph exceeds max_len AND we have enough content
        if current_len + p_len > max_len and current_len > PARENT_MIN_LEN:
            # Check if current paragraph is start of a list item?
            # Ideally we want to keep lists together, but if list is too huge, we must split.
            # Here we just split at paragraph boundary.
            chunks.append("\n".join(current_chunk))
            current_chunk = [p]
            current_len = p_len
        else:
            current_chunk.append(p)
            current_len += p_len
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

def process_parents(sections: List[Dict]) -> List[Dict]:
    """
    Converts Sections into Parent Chunks.
    Adds parent_id and ensures length constraints.
    """
    parents = []
    
    for section in sections:
        content = section['content']
        base_meta = {
            "book": section['book'],
            "chapter": section['chapter'],
            "section": section['section'],
            "figure_ref": section.get('figure_ref'),
            "chunk_type": section.get('chunk_type', 'text'),
            "exam_priority": section.get('exam_priority', 1)
        }
        
        # If it's a table rewrite, keep as single parent (usually)
        if base_meta['chunk_type'] == 'manual_table_rewrite':
            parent_id = str(uuid.uuid4())
            parents.append({
                "parent_id": parent_id,
                "content": content,
                "metadata": base_meta
            })
            continue
            
        # For text, apply splitting rules
        if len(content) > PARENT_MAX_LEN:
            # Split logic
            split_contents = split_text_smart(content, PARENT_TARGET_LEN)
            for i, sub_content in enumerate(split_contents):
                parent_id = str(uuid.uuid4())
                meta = base_meta.copy()
                meta['split_part'] = i + 1
                parents.append({
                    "parent_id": parent_id,
                    "content": sub_content,
                    "metadata": meta
                })
        else:
            # Keep as is
            parent_id = str(uuid.uuid4())
            parents.append({
                "parent_id": parent_id,
                "content": content,
                "metadata": base_meta
            })
            
    return parents



