from desktop_agent.core.provider import DeepSeekProvider
import os
prov = DeepSeekProvider(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_KEY"),
    base_url="https://api.deepseek.com/v1"
)
msg = [{"role":"user","content":"ping"}]
print(prov.chat(msg, temperature=0))
