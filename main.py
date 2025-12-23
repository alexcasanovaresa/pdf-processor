# main.py para Railway con pdfplumber (más robusto que Camelot para PDFs digitales)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        all_text = []
        all_tables = []
        
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                # Extraer texto
                text = page.extract_text() or ""
                all_text.append(text)
                
                # Extraer tablas con configuración optimizada
                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                    "join_tolerance": 5,
                })
                
                for table in tables:
                    if table and len(table) > 1:  # Al menos header + 1 fila
                        all_tables.append(table)
        
        return {
            "text": "\n".join(all_text),
            "tables": all_tables
        }
    finally:
        os.unlink(tmp_path)
