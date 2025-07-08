from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()

# Init OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
internal_api_key = os.getenv("INTERNAL_API_KEY")

# Init FastAPI app
app = FastAPI(
    title="Auto Translator API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Request model
class TranslateRequest(BaseModel):
    text: str
    from_lang: str = "en"
    to_lang: str = "zh"

@app.get("/")
def root():
    return {
        "message": "👋 Welcome to Auto Translator API. Use /translate_free or /translate_pro to translate text.",
        "docs": "/docs (disabled in production)",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    try:
        models = client.models.list()
        return {
            "status": "ok",
            "openai": "available",
            "model_count": len(models.data)
        }
    except Exception as e:
        return {
            "status": "error",
            "openai": "unavailable",
            "detail": str(e)
        }

# Shared translation logic
def perform_translation(req: TranslateRequest, model: str):
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters).")

    prompt = f"Translate this text from {req.from_lang} to {req.to_lang}:\n{req.text}"

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
            "translated": response.choices[0].message.content.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Free version (GPT-3.5)
@app.post("/translate_free")
async def translate_free(
    req: TranslateRequest,
    x_internal_api_key: str = Header(default=None)
):
    if x_internal_api_key != internal_api_key:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
    return perform_translation(req, model="gpt-3.5-turbo")

# Pro version (GPT-4o)
@app.post("/translate_pro")
async def translate_pro(
    req: TranslateRequest,
    x_internal_api_key: str = Header(default=None)
):
    if x_internal_api_key != internal_api_key:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
    return perform_translation(req, model="gpt-4o")
