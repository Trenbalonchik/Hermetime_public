from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import get_all_business_ids, generate_slots_from_template, get_due_reminders, mark_reminder_sent
from notifications import send_email, send_telegram_message

scheduler = AsyncIOScheduler()

async def generate_all_slots():
    for business_id in get_all_business_ids():
        generate_slots_from_template(business_id, days_ahead=14)

async def send_due_reminders():
    for slot_id, slot_time, business_name, email, telegram_chat_id in get_due_reminders():
        text = f"⏰ Нагадування: у вас запис у {business_name} сьогодні о {slot_time.strftime('%H:%M')}"
        if telegram_chat_id:
            send_telegram_message(telegram_chat_id, text)
        if email:
            send_email(email, "Нагадування про запис", text)
        mark_reminder_sent(slot_id)

def start_scheduler():
    scheduler.add_job(generate_all_slots, 'interval', hours=24)
    scheduler.add_job(send_due_reminders, 'interval', minutes=15)
    scheduler.start()