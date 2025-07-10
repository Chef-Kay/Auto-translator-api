# Auto-translator-api
AI-powered API to translate game text for Chinese localization.    
本 API 使用 OpenAI 的 GPT 模型进行自动翻译，适用于游戏汉化、字幕翻译、文本本地化等。支持中英日等多语言互译，接口简单易接入，适合网页、桌面和移动端使用。

Auto Translator API is a simple yet powerful API service designed to automatically translate text between languages using OpenAI’s GPT models. It is optimized for applications such as game localization, user-generated content translation, or any scenario requiring high-quality, natural-language translation.

With a single API call, you can submit a string of text, specify the source and target languages, and receive a fluent and context-aware translation — powered by GPT-3.5 or GPT-4 (in the future). The API is lightweight, fast, and easy to integrate into any client, frontend, or backend system.

### 🎯 Use Cases  
  &emsp;- Game localization (EN → ZH / JP → EN / etc.)  
  &emsp;- Batch subtitle translation  
  &emsp;- Chat bot or NPC dialogue translation  
  &emsp;- E-commerce content translation  
  &emsp;- Mobile apps and browser extensions  

### 🛠️ Features  
  &emsp;✅ Simple POST /translate endpoint  
  &emsp;🌐 Supports any language-to-language translation  
  &emsp;⚡ Fast and lightweight: powered by OpenAI GPT API  
  &emsp;📦 JSON-based input and output  
  &emsp;🔒 Secure key-based access (API key via environment)  

### 📌 Endpoints  
  &emsp;- GET /health – Check if the service and OpenAI backend are alive  
  &emsp;- POST /translate_free – Free translation using GPT-3.5  
  &emsp;- POST /translate_pro – Pro translation using GPT-4o  
  &emsp;- POST /translate_batch_free – Batch translation using GPT-3.5  
  &emsp;- POST /translate_batch_pro – Batch translation using GPT-4o  
  &emsp;- POST /detect_language – Auto-detect source language  
  &emsp;- POST /glossary – Create custom terminology glossary  
  &emsp;- GET /glossary – List all glossaries  
  &emsp;- GET /glossary/{id} – Get specific glossary  
  &emsp;- GET /translation_memory/stats – Get memory statistics  
  &emsp;- DELETE /translation_memory/clear – Clear translation memory  


## New Features

### 🔍 Auto Language Detection
- No need to specify source or target language, API automatically detects both
- Supports multiple languages: English, Chinese, Japanese, Korean, French, German, Spanish, Russian, etc.
- Smart target language detection based on common translation pairs
- Dedicated language detection endpoint: `/detect_language`

### 📚 Glossary Management
- Create custom glossaries to ensure translation consistency
- Supports professional terms, game-specific terminology, etc.
- Automatically applied during translation via `glossary_id`
- Persistent storage - glossaries survive server restarts

### 🎯 Context-Aware Translation
- Provide translation context via `context` parameter
- Improves translation quality for game dialogues, movie subtitles, etc.

### 📦 Batch Translation
- Translate multiple texts in a single request
- Concurrent processing with rate limiting
- Perfect for game localization and subtitle translation
- Supports up to 100 texts per request

### 🧠 Translation Memory
- Automatically cache and reuse previous translations
- Saves API costs and improves response time
- Persistent storage across server restarts
- Memory statistics and management endpoints

## Usage Examples

### Auto-detect language translation
```json
POST /translate_free
{
  "text": "Hello, how are you?"
}
```

### Specify target language
```json
POST /translate_free
{
  "text": "Hello, how are you?",
  "to_lang": "ja"
}
```

### Language detection
```json
POST /detect_language
{
  "text": "こんにちは、お元気ですか？"
}
```

### Create glossary
```json
POST /glossary
{
  "name": "Game Terms",
  "entries": [
    {"source": "HP", "target": "生命值"},
    {"source": "MP", "target": "魔法值"}
  ]
}
```

### List glossaries
```json
GET /glossary
```

### Get specific glossary
```json
GET /glossary/{glossary_id}
```

### Translation memory management
```json
GET /translation_memory/stats
```

```json
DELETE /translation_memory/clear
```

### Batch translation
```json
POST /translate_batch_free
{
  "texts": [
    "Hello, how are you?",
    "Welcome to our game!",
    "Press any key to continue"
  ],
  "context": "Game UI text",
  "max_concurrent": 3
}
```

### Batch translation with specific target
```json
POST /translate_batch_free
{
  "texts": [
    "Hello, how are you?",
    "Welcome to our game!",
    "Press any key to continue"
  ],
  "to_lang": "es",
  "context": "Game UI text",
  "max_concurrent": 3
}
```

### Batch translation with glossary
```json
POST /translate_batch_pro
{
  "texts": [
    "Your HP is low",
    "Use MP to cast spells",
    "Level up to gain more power"
  ],
  "glossary_id": "your-glossary-id",
  "context": "RPG game dialogue"
}
```
