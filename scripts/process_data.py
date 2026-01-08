import pdfplumber
import re
import json
import os
import csv
from typing import List, Dict, Optional

# Configuration
RAW_DOC_DIR = "rawdoc"
DATA_DIR = "data"
OUTPUT_CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.jsonl")

# Target PDFs (Map filename to book name)
PDF_FILES = {
    "基金从业资格考试官方教材（证券投资基金上册）.pdf": "上册",
    "基金从业资格考试官方教材（证券投资基金下册）.pdf": "下册"
}

CHUNK_SIZE = 500
OVERLAP = 100

def parse_pdf_structure(pdf_path: str, book_name: str) -> List[Dict]:
    """
    Parses PDF and extracts text organized by Chapter -> Section.
    """
    print(f"--- Parsing {book_name} from {pdf_path} ---")
    
    docs = []
    current_chapter = "前言/未分类"
    current_section = "未分类"
    buffer_text = [] # Buffer for current section content

    # Regex patterns
    # Chapter: "第1章", "第一章", "第 1 章"
    chapter_pattern = re.compile(r'^\s*第[0-9一二三四五六七八九十]+章\s+')
    # Section: "第一节", "第一节 "
    section_pattern = re.compile(r'^\s*第[0-9一二三四五六七八九十]+节\s+')
    
    # Exclude Table of Contents pages logic (Simple heuristic: skip first few pages if needed, 
    # but here we rely on regex to switch context. 
    # NOTE: Actual TOC pages often match these patterns but list page numbers.
    # We will try to filter out lines that end with "...... 123" which indicate TOC)
    toc_line_pattern = re.compile(r'\.{6,}\s*\d+$') 

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            
            # Simple Header/Footer removal (First and Last 2 lines if they are short or look like page nums)
            # This is a heuristic.
            cleaned_lines = []
            for idx, line in enumerate(lines):
                # Skip header/footer heuristics (e.g. just numbers, or known book titles)
                if idx < 2 or idx >= len(lines) - 2:
                    if re.match(r'^\s*\d+\s*$', line): continue # Page number
                    if "证券投资基金" in line: continue # Book title header
                    if "目录" in line: continue 
                
                # Skip TOC lines
                if toc_line_pattern.search(line):
                    continue
                    
                cleaned_lines.append(line)

            for line in cleaned_lines:
                line = line.strip()
                if not line: continue

                # Detect Chapter Start
                if chapter_pattern.match(line):
                    # Save previous section if exists
                    if buffer_text:
                        docs.append({
                            "book": book_name,
                            "chapter": current_chapter,
                            "section": current_section,
                            "content": "\n".join(buffer_text),
                            "chunk_type": "text",
                            "exam_priority": 1,
                            "figure_ref": None
                        })
                        buffer_text = []
                    
                    current_chapter = line
                    current_section = "概述" # Default section start for new chapter
                    # print(f"  > New Chapter: {current_chapter}")
                    continue

                # Detect Section Start
                if section_pattern.match(line):
                    # Save previous section
                    if buffer_text:
                        docs.append({
                            "book": book_name,
                            "chapter": current_chapter,
                            "section": current_section,
                            "content": "\n".join(buffer_text),
                            "chunk_type": "text",
                            "exam_priority": 1,
                            "figure_ref": None
                        })
                        buffer_text = []
                    
                    current_section = line
                    # print(f"    > New Section: {current_section}")
                    continue

                buffer_text.append(line)
        
        # Save last section
        if buffer_text:
            docs.append({
                "book": book_name,
                "chapter": current_chapter,
                "section": current_section,
                "content": "\n".join(buffer_text),
                "chunk_type": "text",
                "exam_priority": 1,
                "figure_ref": None
            })

    print(f"Finished {book_name}: Extracted {len(docs)} sections.")
    return docs

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Simple sliding window chunking.
    Could be improved with sentence boundary detection.
    """
    if not text: return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

TABLE_FILE = os.path.join(RAW_DOC_DIR, "table_explain.csv")

def load_table_explains() -> List[Dict]:
    """
    Load manually rewritten table explanations from CSV.
    Expected columns: book, chapter, section, figure_ref, content
    """
    tables = []
    if not os.path.exists(TABLE_FILE):
        print(f"Warning: Table file not found {TABLE_FILE}")
        return tables
        
    print(f"--- Loading Table Explains from {TABLE_FILE} ---")
    try:
        with open(TABLE_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # CSV Headers: 序号,来源位置,教材,章节,小结,图表,表格转写说明,核心内容
            for row in reader:
                # Map Chinese headers to English keys
                content_val = row.get('核心内容')
                if not content_val: continue
                
                tables.append({
                    "book": row.get('教材', '未知'),
                    "chapter": row.get('章节', '未知'),
                    "section": row.get('小结', '未知'),
                    "figure_ref": row.get('图表', '未命名图表'),
                    "content": content_val,
                    "chunk_type": "manual_table_rewrite",
                    "exam_priority": 2 # Higher priority for tables
                })
        print(f"Loaded {len(tables)} table records.")
    except Exception as e:
        print(f"Error reading table csv: {e}")
        
    return tables

def process_all():
    all_chunks = []
    
    # 1. Process PDFs
    for pdf_file, book_name in PDF_FILES.items():
        pdf_path = os.path.join(RAW_DOC_DIR, pdf_file)
        if not os.path.exists(pdf_path):
            print(f"Warning: File not found {pdf_path}")
            continue
            
        sections = parse_pdf_structure(pdf_path, book_name)
        
        # 2. Chunking
        for section in sections:
            text_content = section["content"]
            # Skip empty or too short sections
            if len(text_content) < 10: continue
            
            text_chunks = chunk_text(text_content, CHUNK_SIZE, OVERLAP)
            
            for chunk_content in text_chunks:
                chunk_record = section.copy()
                chunk_record["content"] = chunk_content
                # Remove full content from metadata to save space
                all_chunks.append(chunk_record)

    # 3. Process Tables
    table_chunks = load_table_explains()
    
    # Save Tables to separate JSONL
    TABLE_OUTPUT_FILE = os.path.join(DATA_DIR, "table_chunks.jsonl")
    print(f"Saving {len(table_chunks)} table chunks to {TABLE_OUTPUT_FILE}...")
    with open(TABLE_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for chunk in table_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    # 4. Save Text Chunks to JSONL
    print(f"Saving {len(all_chunks)} text chunks to {OUTPUT_CHUNKS_FILE}...")
    with open(OUTPUT_CHUNKS_FILE, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    process_all()

