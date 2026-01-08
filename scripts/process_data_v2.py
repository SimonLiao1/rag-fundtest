import os
import json
import shutil
from typing import List, Dict

# Import components
from scripts.process_data import parse_pdf_structure, load_table_explains, RAW_DOC_DIR, PDF_FILES
from scripts.split_parents import process_parents
from scripts.split_children import split_children

# Config
DATA_DIR = "data"
OUTPUT_PARENTS_FILE = os.path.join(DATA_DIR, "parents.jsonl")
OUTPUT_CHILDREN_FILE = os.path.join(DATA_DIR, "children.jsonl")

def main():
    print("--- Starting Phase 1 Refactor: Parent-Child Chunking ---")
    
    # 1. Load Raw Sections (PDF + Table)
    all_sections = []
    
    # PDF
    for pdf_file, book_name in PDF_FILES.items():
        pdf_path = os.path.join(RAW_DOC_DIR, pdf_file)
        if os.path.exists(pdf_path):
            sections = parse_pdf_structure(pdf_path, book_name)
            all_sections.extend(sections)
            
    # Tables
    tables = load_table_explains()
    all_sections.extend(tables)
    
    print(f"Total raw sections loaded: {len(all_sections)}")
    
    # 2. Process Parents
    parents = process_parents(all_sections)
    print(f"Total Parent Chunks generated: {len(parents)}")
    
    # Save Parents
    with open(OUTPUT_PARENTS_FILE, 'w', encoding='utf-8') as f:
        for p in parents:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
            
    # 3. Process Children
    children = split_children(parents)
    print(f"Total Child Chunks generated: {len(children)}")
    
    # Save Children
    with open(OUTPUT_CHILDREN_FILE, 'w', encoding='utf-8') as f:
        for c in children:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
            
    print("--- Phase 1 Refactor Complete ---")
    print(f"Parents saved to {OUTPUT_PARENTS_FILE}")
    print(f"Children saved to {OUTPUT_CHILDREN_FILE}")

if __name__ == "__main__":
    main()



