from openai import OpenAI
import os
client = OpenAI(
    api_key = os.getenv("DEEPSEEK_KEY"),
    base_url= "https://api.deepseek.com/v1"
)
print(client.api_key)
print("DEBUG  OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))
print("DEBUG  DEEPSEEK_KEY  =", os.getenv("DEEPSEEK_KEY"))
print(client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role":"user","content":"Hello"}]
))
