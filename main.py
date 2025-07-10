from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from openai import OpenAI
from typing import Optional, List
import uuid
import os
import json

# Load environment variables
load_dotenv()

# Init OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Init FastAPI app (Swagger disabled for security)
app = FastAPI(
    title="Auto Translator API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Request model
class TranslateRequest(BaseModel):
    text: str
    from_lang: Optional[str] = None  # Optional, supports auto-detection
    to_lang: str = "zh"
    context: Optional[str] = None
    glossary_id: Optional[str] = None

class GlossaryItem(BaseModel):
    source: str
    target: str

class GlossaryCreate(BaseModel):
    name: str
    entries: List[GlossaryItem]

# Simple file-based storage for glossaries
GLOSSARY_FILE = "glossaries.json"

def load_glossaries():
    """Load glossaries from file"""
    try:
        if os.path.exists(GLOSSARY_FILE):
            with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load glossaries: {e}")
    return {}

def save_glossaries(glossaries_dict):
    """Save glossaries to file"""
    try:
        with open(GLOSSARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(glossaries_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save glossaries: {e}")

# Load glossaries on startup
glossaries = load_glossaries()

# Language detection function
def detect_language(text: str) -> str:
    """Auto-detect text language using OpenAI model"""
    try:
        prompt = f"""Detect the language of the following text and return only the language code (e.g., en, zh, ja, ko, fr, de, es, ru, etc.):

Text: {text}

Language code:"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
            timeout=5
        )
        
        detected_lang = response.choices[0].message.content.strip().lower()
        
        # Standardize language codes
        lang_mapping = {
            "english": "en", "en": "en",
            "chinese": "zh", "zh": "zh", "zh-cn": "zh", "zh-tw": "zh",
            "japanese": "ja", "ja": "ja", "jp": "ja",
            "korean": "ko", "ko": "ko", "kr": "ko",
            "french": "fr", "fr": "fr",
            "german": "de", "de": "de",
            "spanish": "es", "es": "es",
            "russian": "ru", "ru": "ru",
            "italian": "it", "it": "it",
            "portuguese": "pt", "pt": "pt",
            "arabic": "ar", "ar": "ar",
            "hindi": "hi", "hi": "hi"
        }
        
        return lang_mapping.get(detected_lang, detected_lang)
        
    except Exception as e:
        # If detection fails, return default value
        print(f"Language detection failed: {e}")
        return "en"

# Shared translation logic
def perform_translation(req: TranslateRequest, model: str):
    # Auto-detect source language if not specified
    if not req.from_lang:
        req.from_lang = detect_language(req.text)
    
    # Check text length first
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters).")
    
    # Build translation prompt
    prompt = f"Translate from {req.from_lang} to {req.to_lang}:"

    if req.context:
        prompt += f"\nContext: {req.context}"

    if req.glossary_id and req.glossary_id in glossaries:
        glossary = glossaries[req.glossary_id]
        prompt += "\nGlossary:"
        for item in glossary["entries"]:
            prompt += f"\n{item['source']} = {item['target']}"

    prompt += f"\nText: {req.text}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=10
        )
        return {
            "model": model,
            "original": req.text,
            "translated": response.choices[0].message.content.strip(),
            "detected_language": req.from_lang  # Return detected language
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
def health_check():
    try:
        client.models.list()
        return {"status": "ok", "openai": "available"}
    except Exception as e:
        return {"status": "error", "openai": "unavailable", "detail": str(e)}

# Welcome
@app.get("/")
def root():
    return {"message": "Welcome to Auto Translator API"}

@app.post("/glossary")
async def create_glossary(glossary: GlossaryCreate):
    glossary_id = str(uuid.uuid4())
    glossaries[glossary_id] = glossary.dict()
    save_glossaries(glossaries)
    return {"glossary_id": glossary_id}

@app.get("/glossary")
async def list_glossaries():
    """List all available glossaries"""
    return {"glossaries": list(glossaries.keys())}

@app.get("/glossary/{glossary_id}")
async def get_glossary(glossary_id: str):
    """Get specific glossary by ID"""
    if glossary_id not in glossaries:
        raise HTTPException(status_code=404, detail="Glossary not found")
    return {"glossary_id": glossary_id, "glossary": glossaries[glossary_id]}

# Language detection endpoint
@app.post("/detect_language")
async def detect_language_endpoint(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        if len(text) > 1000:
            raise HTTPException(status_code=400, detail="Text too long (max 1000 characters)")
        
        detected_lang = detect_language(text)
        return {
            "text": text,
            "detected_language": detected_lang
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Free version using GPT-3.5
@app.post("/translate_free")
async def translate_free(req: TranslateRequest):
    return perform_translation(req, model="gpt-3.5-turbo")

# Pro version using GPT-4o
@app.post("/translate_pro")
async def translate_pro(req: TranslateRequest):
    return perform_translation(req, model="gpt-4o")

# RapidAPI authentication middleware
class RapidAPIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if request.url.path in ["/", "/health"]:
            return await call_next(request)
         
        expected = os.getenv("RAPIDAPI_SECRET")
        actual = request.headers.get("X-RapidAPI-Proxy-Secret")
        if actual != expected:
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid RapidAPI proxy secret"})
        return await call_next(request)

# Attach middleware
app.add_middleware(RapidAPIAuthMiddleware)
