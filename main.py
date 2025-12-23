from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import google.generativeai as genai
import os
import json
import tempfile

app = FastAPI()

# CORS - Permitir todos los orígenes (importante para Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@app.get("/")
def health():
    return {"status": "ok", "service": "pdfplumber-processor"}

@app.post("/process-pdf")
async def process_pdf(file: UploadFile = File(...)):
    try:
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Extraer con pdfplumber
        full_text = ""
        all_tables = []
        
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
        
        os.unlink(tmp_path)
        
        # Estructurar con Gemini
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""Analiza este extracto bancario y devuelve un JSON con esta estructura exacta:
{{
  "banco": "nombre del banco",
  "titular": "nombre del titular",
  "cuenta": "número de cuenta",
  "clabe": "clabe si existe",
  "periodo": "periodo del extracto",
  "saldo_inicial": número,
  "saldo_final": número,
  "movimientos": [
    {{"fecha": "DD/MM/YYYY", "concepto": "descripción", "importe": número, "saldo": número}}
  ]
}}

IMPORTANTE:
- importe: positivo para depósitos/abonos, negativo para retiros/cargos
- fecha: formato DD/MM/YYYY
- Solo devuelve el JSON, sin explicaciones

TEXTO EXTRAÍDO:
{full_text[:15000]}

TABLAS:
{str(all_tables)[:5000]}
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Limpiar respuesta
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
