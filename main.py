from fastapi import FastAPI, Query, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI application
app = FastAPI(title="Auto Translator API")

# Define request body schema
class TranslateRequest(BaseModel):
    text: str
    from_lang: str = "en"
    to_lang: str = "zh"

# Root endpoint
@app.get("/")
def root():
    return {"message": "Welcome to Auto Translator API. Visit /docs to try it."}

# Health check endpoint (checks OpenAI availability)
@app.get("/health")
def health_check():
    try:
        client.models.list()
        return {"status": "ok", "openai": "available"}
    except Exception as e:
        return {"status": "error", "openai": "unavailable", "detail": str(e)}

# Translation endpoint with GPT model switching based on plan
@app.post("/translate")
async def translate(req: TranslateRequest, request: Request):
    # Reject overly long requests to reduce abuse or excessive token cost
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters).")

    # Read user plan from RapidAPI request header
    user_plan = request.headers.get("X-RapidAPI-Plan", "").lower()

    # Default model is GPT-3.5 for free users
    model = "gpt-3.5-turbo"

    # Use GPT-4o for paid users (basic, pro, ultra)
    if user_plan in ["basic", "pro", "ultra"]:
        model = "gpt-4o"

    # Construct translation prompt
    prompt = f"Translate this text from {req.from_lang} to {req.to_lang}:\n{req.text}"
    
    try:
        # Call OpenAI Chat Completion API
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=10
        )
        result = response.choices[0].message.content.strip()

        # Return original and translated text
        return {
            "plan": user_plan,
            "model": model,
            "original": req.text,
            "translated": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
