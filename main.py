from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "healthy", "library": "pymupdf"}

def extract_tables_from_text(text: str) -> list:
    """Extract table-like data from text using patterns"""
    tables = []
    lines = text.split('\n')
    
    current_table = []
    # Pattern for dates like DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY
    date_pattern = re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
    # Pattern for money amounts like 1,234.56 or -1,234.56
    money_pattern = re.compile(r'-?[\d,]+\.\d{2}')
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_table and len(current_table) >= 3:
                tables.append(current_table)
            current_table = []
            continue
        
        # Check if line looks like a transaction row
        has_date = date_pattern.search(line)
        has_money = money_pattern.search(line)
        
        if has_date or has_money:
            # Split by multiple spaces or tabs
            parts = re.split(r'\s{2,}|\t', line)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                current_table.append(parts)
    
    if current_table and len(current_table) >= 3:
        tables.append(current_table)
    
    return tables

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf_document = fitz.open(stream=contents, filetype="pdf")
        
        all_text = []
        all_tables = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text with better layout preservation
            text = page.get_text("text", sort=True)
            all_text.append(f"=== PÁGINA {page_num + 1} ===\n{text}")
            
            # Try PyMuPDF table extraction first
            try:
                tables = page.find_tables()
                for table in tables:
                    table_data = table.extract()
                    if table_data and len(table_data) > 2:  # Only tables with 3+ rows
                        cleaned = []
                        for row in table_data:
                            cleaned_row = [str(c).strip() if c else "" for c in row]
                            if any(cleaned_row):
                                cleaned.append(cleaned_row)
                        if len(cleaned) > 2:
                            all_tables.append(cleaned)
            except Exception as e:
                print(f"Table extraction error on page {page_num}: {e}")
        
        pdf_document.close()
        
        combined_text = "\n\n".join(all_text)
        
        # If no tables found, try extracting from text
        if not all_tables:
            all_tables = extract_tables_from_text(combined_text)
        
        print(f"Extracted: {len(combined_text)} chars, {len(all_tables)} tables")
        for i, t in enumerate(all_tables[:3]):
            print(f"Table {i}: {len(t)} rows, first row: {t[0] if t else 'empty'}")
        
        return {
            "success": True,
            "text": combined_text,
            "tables": all_tables,
            "page_count": len(pdf_document) if pdf_document else 0
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "tables": []
        }
