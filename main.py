from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="Auto Translator API")

class TranslateRequest(BaseModel):
    text: str
    from_lang: str = "en"
    to_lang: str = "zh"

@app.get("/")
def root():
    return {"message": "Welcome to Auto Translator API. Visit /docs to try it."}

@app.get("/health")
def health_check():
    try:
        client.models.list()
        return {"status": "ok", "openai": "available"}
    except Exception as e:
        return {"status": "error", "openai": "unavailable", "detail": str(e)}

@app.post("/translate")
async def translate(req: TranslateRequest):
    if len(req.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters).")

    prompt = f"Translate this text from {req.from_lang} to {req.to_lang}:\n{req.text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=10
        )
        result = response.choices[0].message.content.strip()
        return {
            "original": req.text,
            "translated": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
