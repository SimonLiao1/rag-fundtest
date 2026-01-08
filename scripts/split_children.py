from typing import List, Dict

CHILD_SIZE = 300
CHILD_OVERLAP = 50

def split_children(parent_chunks: List[Dict]) -> List[Dict]:
    """
    Splits Parent Chunks into Child Chunks.
    """
    children = []
    
    for parent in parent_chunks:
        text = parent['content']
        parent_id = parent['parent_id']
        meta = parent['metadata']
        
        # Sliding window
        if not text: continue
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # If text is shorter than window, take it all
            if len(text) - start < CHILD_SIZE:
                end = len(text)
            else:
                end = start + CHILD_SIZE
                
            chunk_content = text[start:end]
            
            # Create Child Record
            children.append({
                "parent_id": parent_id,
                "content": chunk_content,
                "metadata": meta # Inherit parent metadata
            })
            
            # Break if we reached end
            if end == len(text):
                break
                
            start += (CHILD_SIZE - CHILD_OVERLAP)
            chunk_index += 1
            
    return children



