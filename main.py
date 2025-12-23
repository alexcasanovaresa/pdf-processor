from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import tempfile
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "ok", "library": "PyMuPDF"}

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        all_text = []
        all_tables = []
        
        doc = fitz.open(tmp_path)
        
        for page_num, page in enumerate(doc):
            # Extract text with better formatting
            text = page.get_text("text")
            all_text.append(f"=== Página {page_num + 1} ===\n{text}")
            
            # Try to extract tables using PyMuPDF's table detection
            try:
                tabs = page.find_tables()
                for tab in tabs:
                    table_data = tab.extract()
                    if table_data and len(table_data) > 1:
                        # Clean up table data
                        cleaned_table = []
                        for row in table_data:
                            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                            if any(cleaned_row):  # Skip empty rows
                                cleaned_table.append(cleaned_row)
                        if cleaned_table:
                            all_tables.append(cleaned_table)
            except Exception as e:
                print(f"Table extraction error on page {page_num + 1}: {e}")
        
        doc.close()
        
        return {
            "text": "\n\n".join(all_text),
            "tables": all_tables,
            "pages": len(doc) if doc else 0
        }
    finally:
        os.unlink(tmp_path)
