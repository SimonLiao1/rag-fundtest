import pdfplumber
import re
import sys

# File path
pdf_path = "rawdoc/基金从业资格考试官方教材（证券投资基金上册）.pdf"

def analyze_pdf_structure(pdf_path, start_page=0, end_page=30):
    """
    Analyzes the first few pages to identify:
    1. Header/Footer regions (by y-position).
    2. Chapter/Section regex patterns.
    """
    print(f"--- Analyzing {pdf_path} (Pages {start_page}-{end_page}) ---")
    
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(start_page, min(len(pdf.pages), end_page)):
            page = pdf.pages[i]
            text = page.extract_text()
            
            # Simple heuristic for header/footer analysis: look at top/bottom lines
            lines = text.split('\n') if text else []
            if not lines:
                continue
                
            print(f"\n[Page {i+1}] (Height: {page.height})")
            
            # Print first 3 and last 3 lines to spot headers/footers
            print("  Top lines:")
            for line in lines[:3]:
                print(f"    {line}")
            print("  Bottom lines:")
            for line in lines[-3:]:
                print(f"    {line}")
                
            # Try to match Chapter/Section
            for line in lines:
                if re.match(r'^\s*第[一二三四五六七八九十0-9]+章', line):
                    print(f"  >>> FOUND CHAPTER: {line}")
                if re.match(r'^\s*第[一二三四五六七八九十0-9]+节', line):
                    print(f"  >>> FOUND SECTION: {line}")

if __name__ == "__main__":
    try:
        analyze_pdf_structure(pdf_path)
    except ImportError:
        print("Please install pdfplumber: pip install pdfplumber")
    except FileNotFoundError:
        print(f"File not found: {pdf_path}")



