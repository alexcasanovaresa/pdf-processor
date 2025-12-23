from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import camelot
import tempfile
import os
import json
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@app.get("/")
async def root():
    return {"status": "ok", "method": "camelot+pymupdf"}

@app.post("/process-pdf")
async def process_pdf(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Extraer texto con PyMuPDF
        doc = fitz.open(tmp_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        # Extraer tablas con Camelot
        tables_data = []
        try:
            tables = camelot.read_pdf(tmp_path, pages='all', flavor='lattice')
            if len(tables) == 0:
                tables = camelot.read_pdf(tmp_path, pages='all', flavor='stream')
            
            for table in tables:
                tables_data.append(table.df.to_dict('records'))
        except Exception as e:
            print(f"Camelot error: {e}")

        os.unlink(tmp_path)

        # Enviar a Gemini para estructurar
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""Analiza este estado de cuenta bancario mexicano.

TEXTO EXTRAÍDO:
{full_text[:15000]}

TABLAS EXTRAÍDAS:
{json.dumps(tables_data[:10], ensure_ascii=False, default=str)[:10000]}

Devuelve JSON con esta estructura EXACTA:
{{
  "banco": "nombre del banco",
  "cuenta": "número de cuenta",
  "clabe": "CLABE si existe",
  "titular": "nombre del titular",
  "periodo": "periodo del estado",
  "saldo_inicial": numero,
  "saldo_final": numero,
  "movimientos": [
    {{"fecha": "DD/MM/YYYY", "concepto": "descripción", "importe": numero, "saldo": numero}}
  ]
}}

IMPORTANTE: importe positivo=depósito, negativo=retiro. Solo JSON válido."""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        result = json.loads(text)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
