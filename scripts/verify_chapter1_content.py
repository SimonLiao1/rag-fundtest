import pdfplumber
import re

pdf_path = "rawdoc/基金从业资格考试官方教材（证券投资基金上册）.pdf"

def extract_chapter_1(pdf_path):
    print(f"Extracting Chapter 1 from {pdf_path}...")
    content = []
    in_chapter_1 = False
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                # Normalizing whitespace
                line = line.strip()
                
                # Check for Chapter 1 Start
                # Using a broad pattern to catch "第1章" or "第一章"
                if re.match(r'^第[1一]章', line):
                    in_chapter_1 = True
                    print(f"DEBUG: Found Start of Chapter 1 on page {i+1}: {line}")
                
                # Check for Chapter 2 Start (End of Chapter 1)
                if re.match(r'^第[2二]章', line) and in_chapter_1:
                    in_chapter_1 = False
                    print(f"DEBUG: Found Start of Chapter 2 on page {i+1}: {line}")
                    return content # Stop after Chapter 1
                
                if in_chapter_1:
                    content.append(line)
                    
    return content

if __name__ == "__main__":
    lines = extract_chapter_1(pdf_path)
    
    # Save to file to verify encoding
    with open("chapter1_preview.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"Extracted {len(lines)} lines. Saved to chapter1_preview.txt")



