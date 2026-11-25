import os, asyncio, logging
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.error")

from db import (
    get_info, get_available_dates, get_slots_by_date, book_slot,
    register_business, register_client, get_business_by_owner_phone,
    add_schedule_template_entry, generate_slots_from_template, get_schedule_template,
    get_user_by_phone, get_client_by_phone_full, create_telegram_link_token,
    get_bookings, get_services, add_service, delete_service,
    edit_info
)
from AI import build_system_prompt, ask_gemini
from scheduler import start_scheduler

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def on_startup():
    start_scheduler()

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- Business (клієнтський перегляд) ----------

@app.get("/businesses/{business_id}")
def business_info(business_id: int):
    info = get_info(business_id)
    if not info:
        raise HTTPException(status_code=404, detail="Не знайдено")
    return {"name": info[0], "phone": info[1], "description": info[2]}

@app.get("/businesses/{business_id}/available-dates")
def available_dates(business_id: int, year: int, month: int):
    dates = get_available_dates(business_id, year, month)
    return {"dates": [d.isoformat() for d in dates]}

@app.get("/businesses/{business_id}/slots")
def slots_for_date(business_id: int, day: date):
    slots = get_slots_by_date(business_id, day)
    return {"slots": [{"id": s[0], "time": s[1].strftime("%H:%M")} for s in slots]}

# ---------- Booking ----------

class BookingRequest(BaseModel):
    business_id: int
    slot_id: int
    name: str
    phone: str
    email: str | None = None
    service_id: int | None = None

@app.post("/book")
def create_booking(payload: BookingRequest):
    client_id = register_client(payload.phone, payload.name, payload.email)
    success = book_slot(payload.business_id, payload.slot_id, client_id, payload.name, payload.phone, payload.service_id)
    if not success:
        raise HTTPException(status_code=409, detail="Цей час вже зайняли")
    return {"status": "confirmed"}

# ---------- Owner: реєстрація і розклад ----------

class BusinessRegisterRequest(BaseModel):
    owner_name: str
    phone: str
    business_name: str
    business_phone: str
    description: str

@app.post("/businesses")
def create_business(payload: BusinessRegisterRequest):
    business_id = register_business(
        payload.phone, payload.owner_name,
        payload.business_name, payload.business_phone, payload.description
    )
    return {"business_id": business_id}

@app.get("/businesses/by-owner-phone/{phone}")
def business_by_owner_phone(phone: str):
    business = get_business_by_owner_phone(phone)
    if not business:
        raise HTTPException(status_code=404, detail="Салон з таким телефоном власника не знайдено")
    return {"business_id": business[0], "name": business[1]}

class ScheduleTemplateRequest(BaseModel):
    days: list[int]
    times: list[str]
    duration_minutes: int = 60

@app.post("/businesses/{business_id}/schedule-template")
def set_schedule_template(business_id: int, payload: ScheduleTemplateRequest):
    for day in payload.days:
        for time_str in payload.times:
            add_schedule_template_entry(business_id, day, time_str, payload.duration_minutes)
    created = generate_slots_from_template(business_id, days_ahead=14)
    return {"created_slots": created}

@app.get("/businesses/{business_id}/schedule-template")
def read_schedule_template(business_id: int):
    template = get_schedule_template(business_id)
    return {"template": [{"weekday": w, "time": t.strftime("%H:%M"), "duration": d} for w, t, d in template]}

# ---------- AI-чат ----------

class ChatRequest(BaseModel):
    business_id: int
    message: str

@app.post("/chat")
async def chat(payload: ChatRequest):
    system_prompt = build_system_prompt(payload.business_id)
    try:
        reply = await asyncio.to_thread(ask_gemini, system_prompt, payload.message)
    except Exception:
        logger.exception("Помилка при зверненні до Gemini (business_id=%s)", payload.business_id)
        reply = "⚠️ Вибачте, зараз не можу відповісти. Спробуйте пізніше."
    return {"reply": reply}

# ---------- Нагадування: підписка через Telegram ----------

class TelegramLinkRequest(BaseModel):
    phone: str

@app.post("/notifications/telegram-link")
def telegram_link(payload: TelegramLinkRequest):
    user = get_user_by_phone(payload.phone)
    if not user:
        raise HTTPException(status_code=404, detail="Спочатку забронюйте візит цим номером")
    token = create_telegram_link_token(user[0])
    bot_username = os.getenv("NOTIFY_BOT_USERNAME")
    return {"link": f"https://t.me/{bot_username}?start={token}"}

class ServiceRequest(BaseModel):
    name: str
    duration_minutes: int
    price: float | None = None

@app.post("/businesses/{business_id}/services")
def create_service(business_id: int, payload: ServiceRequest):
    service_id = add_service(business_id, payload.name, payload.duration_minutes, payload.price)
    return {"service_id": service_id}

@app.get("/businesses/{business_id}/services")
def list_services(business_id: int):
    services = get_services(business_id)
    return {"services": [{"id": s[0], "name": s[1], "duration": s[2], "price": float(s[3]) if s[3] else None} for s in services]}

@app.delete("/services/{service_id}")
def remove_service(service_id: int):
    delete_service(service_id)
    return {"status": "deleted"}

@app.get("/businesses/{business_id}/bookings")
def list_bookings(business_id: int):
    bookings = get_bookings(business_id)
    return {"bookings": [
        {"id": b[0], "time": b[1].strftime("%d.%m %H:%M"), "name": b[3], "phone": b[4], "service": b[5]}
        for b in bookings
    ]}

class BusinessInfoUpdate(BaseModel):
    name: str
    phone: str
    description: str

@app.put("/businesses/{business_id}")
def update_business_info(business_id: int, payload: BusinessInfoUpdate):
    edit_info(business_id, payload.name, payload.phone, payload.description)
    return {"status": "updated"}

class ClientRegisterRequest(BaseModel):
    name: str
    phone: str
    email: str | None = None

@app.post("/clients/register")
def client_register(payload: ClientRegisterRequest):
    client_id = register_client(payload.phone, payload.name, payload.email)
    return {"client_id": client_id}

@app.get("/clients/by-phone/{phone}")
def client_by_phone(phone: str):
    client = get_client_by_phone_full(phone)
    if not client:
        raise HTTPException(status_code=404, detail="Клієнта з таким номером не знайдено")
    return {"user_id": client[0], "name": client[1], "email": client[2]}