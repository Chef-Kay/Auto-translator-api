from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from openai import OpenAI
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
import os
import json
import asyncio

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

# Request models
class TranslateRequest(BaseModel):
    text: str
    from_lang: Optional[str] = None  # Optional, supports auto-detection
    to_lang: Optional[str] = None  # Optional, supports auto-detection
    context: Optional[str] = None
    glossary_id: Optional[str] = None

class BatchTranslateRequest(BaseModel):
    texts: List[str]
    from_lang: Optional[str] = None  # Optional, supports auto-detection
    to_lang: Optional[str] = None  # Optional, supports auto-detection
    context: Optional[str] = None
    glossary_id: Optional[str] = None
    max_concurrent: Optional[int] = 5  # Limit concurrent requests to avoid rate limits

class GlossaryItem(BaseModel):
    source: str
    target: str

class GlossaryCreate(BaseModel):
    name: str
    entries: List[GlossaryItem]

# Simple file-based storage for glossaries
GLOSSARY_FILE = "glossaries.json"

class TranslationMemory:
    def __init__(self):
        self.memory = {}
        self.memory_file = "translation_memory.json"
        self.load_memory()
    
    def get(self, source: str, target_lang: str) -> Optional[str]:
        return self.memory.get((hash(source), target_lang))
    
    def save(self, source: str, target: str, target_lang: str):
        self.memory[(hash(source), target_lang)] = target
        self.save_memory()
    
    def load_memory(self):
        """Load translation memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys back to tuples
                    self.memory = {eval(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Failed to load translation memory: {e}")
            self.memory = {}
    
    def save_memory(self):
        """Save translation memory to file"""
        try:
            # Convert tuple keys to strings for JSON serialization
            data = {str(k): v for k, v in self.memory.items()}
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save translation memory: {e}")
    
    def clear(self):
        """Clear all translation memory"""
        self.memory.clear()
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)

# 初始化翻译记忆
translation_memory = TranslationMemory()

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

# Smart target language detection
def detect_target_language(text: str, source_lang: str) -> str:
    """Smart detection of target language based on context and common patterns"""
    
    # Common language pairs for translation
    common_pairs = {
        "en": ["zh", "ja", "ko", "es", "fr", "de"],
        "zh": ["en", "ja", "ko"],
        "ja": ["en", "zh", "ko"],
        "ko": ["en", "zh", "ja"],
        "es": ["en", "fr", "pt"],
        "fr": ["en", "es", "de"],
        "de": ["en", "fr", "es"],
        "ru": ["en", "zh", "es"],
        "it": ["en", "es", "fr"],
        "pt": ["en", "es", "fr"]
    }
    
    # If source language is in common pairs, suggest the most common target
    if source_lang in common_pairs:
        return common_pairs[source_lang][0]  # Return the first (most common) target
    
    # Default fallback
    return "en"

# Shared translation logic
def perform_translation(req: TranslateRequest, model: str):
    # Auto-detect source language if not specified
    if not req.from_lang:
        req.from_lang = detect_language(req.text)
    
    # Auto-detect target language if not specified
    if not req.to_lang:
        # Use smart detection based on source language
        req.to_lang = detect_target_language(req.text, req.from_lang)
    
    # Check text length first
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters).")
    
    # Check translation memory first
    if cached := translation_memory.get(req.text, req.to_lang):
        return {
            "model": "cache",
            "original": req.text,
            "translated": cached,
            "detected_language": req.from_lang,
            "cached": True
        }
    
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
        
        translated_text = response.choices[0].message.content.strip()
        
        # Save to translation memory
        translation_memory.save(req.text, translated_text, req.to_lang)
        
        return {
            "model": model,
            "original": req.text,
            "translated": translated_text,
            "detected_language": req.from_lang,
            "cached": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Batch translation logic
def perform_batch_translation(req: BatchTranslateRequest, model: str):
    """Perform batch translation with rate limiting and error handling"""
    
    # Validate input
    if not req.texts:
        raise HTTPException(status_code=400, detail="No texts provided")
    
    if len(req.texts) > 100:
        raise HTTPException(status_code=400, detail="Too many texts (max 100)")
    
    # Check total character count
    total_chars = sum(len(text) for text in req.texts)
    if total_chars > 10000:
        raise HTTPException(status_code=400, detail="Total text too long (max 10000 characters)")
    
    # Auto-detect source language if not specified
    if not req.from_lang:
        # Use the first text for language detection
        req.from_lang = detect_language(req.texts[0])
    
    # Auto-detect target language if not specified
    if not req.to_lang:
        # Use smart detection based on source language
        req.to_lang = detect_target_language(req.texts[0], req.from_lang)
    
    # Build base prompt components
    base_prompt = f"Translate from {req.from_lang} to {req.to_lang}:"
    
    if req.context:
        base_prompt += f"\nContext: {req.context}"
    
    if req.glossary_id and req.glossary_id in glossaries:
        glossary = glossaries[req.glossary_id]
        base_prompt += "\nGlossary:"
        for item in glossary["entries"]:
            base_prompt += f"\n{item['source']} = {item['target']}"
    
    results = []
    errors = []
    
    def translate_single_text(text: str, index: int):
        """Translate a single text"""
        try:
            if len(text) > 1000:
                return {
                    "index": index,
                    "original": text,
                    "translated": None,
                    "error": "Text too long (max 1000 characters)"
                }
            
            # Check translation memory first
            if cached := translation_memory.get(text, req.to_lang):
                return {
                    "index": index,
                    "original": text,
                    "translated": cached,
                    "error": None,
                    "cached": True
                }
            
            prompt = base_prompt + f"\nText: {text}"
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=10
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Save to translation memory
            translation_memory.save(text, translated_text, req.to_lang)
            
            return {
                "index": index,
                "original": text,
                "translated": translated_text,
                "error": None,
                "cached": False
            }
            
        except Exception as e:
            return {
                "index": index,
                "original": text,
                "translated": None,
                "error": str(e),
                "cached": False
            }
    
    # Use ThreadPoolExecutor for concurrent translation
    max_workers = min(req.max_concurrent, len(req.texts))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all translation tasks
        future_to_index = {
            executor.submit(translate_single_text, text, i): i 
            for i, text in enumerate(req.texts)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_index):
            result = future.result()
            if result["error"]:
                errors.append(result)
            else:
                results.append(result)
    
    # Sort results by original index
    results.sort(key=lambda x: x["index"])
    errors.sort(key=lambda x: x["index"])
    
    # Count cached results
    cached_count = sum(1 for r in results if r.get("cached", False))
    
    return {
        "model": model,
        "detected_language": req.from_lang,
        "total_texts": len(req.texts),
        "successful_translations": len(results),
        "failed_translations": len(errors),
        "cached_translations": cached_count,
        "new_translations": len(results) - cached_count,
        "results": results,
        "errors": errors
    }

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

# Translation memory management endpoints
@app.get("/translation_memory/stats")
async def get_translation_memory_stats():
    """Get translation memory statistics"""
    return {
        "total_entries": len(translation_memory.memory),
        "memory_size_mb": len(str(translation_memory.memory).encode()) / (1024 * 1024)
    }

@app.delete("/translation_memory/clear")
async def clear_translation_memory():
    """Clear all translation memory"""
    translation_memory.clear()
    return {"message": "Translation memory cleared successfully"}

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

# free version using GPT-3.5
@app.post("/translate_free")
async def translate_free(req: TranslateRequest):
    return perform_translation(req, model="gpt-3.5-turbo")

# Pro version using GPT-4o
@app.post("/translate_pro")
async def translate_pro(req: TranslateRequest):
    return perform_translation(req, model="gpt-4o")

# Batch translation endpoints
@app.post("/translate_batch_free")
async def translate_batch_free(req: BatchTranslateRequest):
    """Batch translation using GPT-3.5 (free tier)"""
    return perform_batch_translation(req, model="gpt-3.5-turbo")

@app.post("/translate_batch_pro")
async def translate_batch_pro(req: BatchTranslateRequest):
    """Batch translation using GPT-4o (pro tier)"""
    return perform_batch_translation(req, model="gpt-4o")

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
