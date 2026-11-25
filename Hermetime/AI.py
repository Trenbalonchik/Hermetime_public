import os
from dotenv import load_dotenv
from db import get_info
from google import genai
load_dotenv()

client = genai.Client(api_key=os.getenv("G_API"))
MODEL_NAME = "gemini-3.5-flash-lite"

def build_system_prompt(business_id: int) -> str:
    business = get_info(business_id)
    return f"""
Ти AI асистент салону краси "{business[0]}".
Контактний телефон: {business[1]}
Про салон: {business[2]}
ТИ СПІЛКУЄШСЯ З КЛЄНТОМ ЦЬОГО САЛОНУ
Твої правила:
- Відповідай тільки про цей салон
- Будь ввічливим і коротким
- Якщо не знаєш відповіді - вічливо перенаправ на контактні данні 
- Не вигадуй інформацію якої немає вище
-НЕ ВІТАЙСЯ КОЖЕН РАЗ
"""

def ask_gemini(system_prompt: str, user_message: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"{system_prompt}\n\nПовідомлення клієнта: {user_message}"
    )
    return response.text