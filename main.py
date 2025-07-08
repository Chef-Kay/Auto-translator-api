from fastapi import FastAPI, Query
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

@app.post("/translate")
async def translate(req: TranslateRequest):
    prompt = f"Translate this text from {req.from_lang} to {req.to_lang}:\n{req.text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        result = response.choices[0].message.content.strip()
        return {
            "original": req.text,
            "translated": result
        }
    except Exception as e:
        return {"error": str(e)}
