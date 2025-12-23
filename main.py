from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import io

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

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf_document = fitz.open(stream=contents, filetype="pdf")
        
        all_text = []
        all_tables = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text
            text = page.get_text("text")
            all_text.append(text)
            
            # Extract tables using PyMuPDF's table finder
            tables = page.find_tables()
            for table in tables:
                table_data = table.extract()
                if table_data and len(table_data) > 0:
                    # Clean table data
                    cleaned_table = []
                    for row in table_data:
                        cleaned_row = []
                        for cell in row:
                            if cell is None:
                                cleaned_row.append("")
                            else:
                                cleaned_row.append(str(cell).strip())
                        cleaned_table.append(cleaned_row)
                    
                    if any(any(cell for cell in row) for row in cleaned_table):
                        all_tables.append(cleaned_table)
        
        pdf_document.close()
        
        combined_text = "\n\n".join(all_text)
        
        return {
            "success": True,
            "text": combined_text,
            "tables": all_tables,
            "page_count": len(pdf_document) if pdf_document else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "tables": []
        }
