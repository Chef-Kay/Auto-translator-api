# Auto-translator-api
AI-powered API to translate game text for Chinese localization.

Auto Translator API is a simple yet powerful API service designed to automatically translate text between languages using OpenAI’s GPT models. It is optimized for applications such as game localization, user-generated content translation, or any scenario requiring high-quality, natural-language translation.

With a single API call, you can submit a string of text, specify the source and target languages, and receive a fluent and context-aware translation — powered by GPT-3.5 or GPT-4 (in the future). The API is lightweight, fast, and easy to integrate into any client, frontend, or backend system.

🎯 Use Cases  
  &emsp;-Game localization (EN → ZH / JP → EN / etc.)  
  &emsp;-Batch subtitle translation  
  &emsp;-Chat bot or NPC dialogue translation  
  &emsp;-E-commerce content translation  
  &emsp;-Mobile apps and browser extensions  

🛠️ Features  
  &emsp;✅ Simple POST /translate endpoint  
  &emsp;🌐 Supports any language-to-language translation  
  &emsp;⚡ Fast and lightweight: powered by OpenAI GPT API  
  &emsp;📦 JSON-based input and output  
  &emsp;🔒 Secure key-based access (API key via environment)  

📌 Endpoints  
  &emsp;-GET /health – Check if the service and OpenAI backend are alive  
  &emsp;-POST /translate – Submit text, source language, and target language  

  本 API 使用 OpenAI 的 GPT 模型进行自动翻译，适用于游戏汉化、字幕翻译、文本本地化等。支持中英日等多语言互译，接口简单易接入，适合网页、桌面和移动端使用。
