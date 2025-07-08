from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os
from openai import OpenAI

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
    from_lang: str = "en"
    to_lang: str = "zh"

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
        expected = os.getenv("RAPIDAPI_SECRET")
        actual = request.headers.get("X-RapidAPI-Proxy-Secret")
        if actual != expected:
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid RapidAPI proxy secret"})
        return await call_next(request)

# Attach middleware
app.add_middleware(RapidAPIAuthMiddleware)
