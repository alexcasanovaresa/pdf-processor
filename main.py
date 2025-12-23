from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "method": "pymupdf-extract"}

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Extraer texto con PyMuPDF
        doc = fitz.open(tmp_path)
        full_text = ""
        tables_data = []
        
        for page in doc:
            full_text += page.get_text()
            # Extraer tablas con PyMuPDF
            tabs = page.find_tables()
            for tab in tabs:
                tables_data.append(tab.extract())
        
        doc.close()
        os.unlink(tmp_path)

        return {
            "text": full_text,
            "tables": tables_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
