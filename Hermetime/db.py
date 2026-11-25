import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()
import secrets
from datetime import datetime, timedelta

def get_connection():
    return psycopg2.connect(
        host="localhost", port=5432, dbname="saasdb",
        user="postgres", password=os.getenv("DB_PASSWORD")
    )

# ---------- Users ----------

def add_user(name: str, phone: str, email: str = None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, phone, email) VALUES (%s, %s, %s) RETURNING id",
        (name, phone, email)
    )
    user_id = cursor.fetchone()[0]
    conn.commit(); cursor.close(); conn.close()
    return user_id

def get_user_by_phone(phone: str):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE phone = %s", (phone,))
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result

def get_client_by_phone_full(phone: str):
    """Повертає (user_id, name, email) якщо цей телефон вже належить клієнту
    (тобто для нього існує запис у clients), інакше None."""
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT u.id, u.name, u.email
           FROM users u
           JOIN clients c ON c.user_id = u.id
           WHERE u.phone = %s""",
        (phone,)
    )
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result

def update_user_email(user_id: int, email: str):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))
    conn.commit(); cursor.close(); conn.close()

# ---------- Businesses ----------

def add_business(user_id: int, name: str, phone: str, description: str):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO businesses (user_id, name, phone, description) VALUES (%s, %s, %s, %s) RETURNING id",
        (user_id, name, phone, description)
    )
    business_id = cursor.fetchone()[0]
    conn.commit(); cursor.close(); conn.close()
    return business_id

def get_business_by_user(user_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM businesses WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result[0] if result else None

def get_business_by_owner_phone(phone: str):
    """Повертає (business_id, business_name) якщо власник із таким ОСОБИСТИМ
    телефоном (не телефоном салону!) вже має зареєстрований салон."""
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT b.id, b.name
           FROM users u
           JOIN businesses b ON b.user_id = u.id
           WHERE u.phone = %s
           ORDER BY b.id
           LIMIT 1""",
        (phone,)
    )
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result

def get_info(business_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT name, phone, description FROM businesses WHERE id = %s", (business_id,))
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result

def edit_info(business_id: int, name: str, phone: str, description: str):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "UPDATE businesses SET name = %s, phone = %s, description = %s WHERE id = %s",
        (name, phone, description, business_id)
    )
    conn.commit(); cursor.close(); conn.close()
    return True

def register_business(phone: str, owner_name: str, business_name: str, business_phone: str, description: str):
    existing = get_user_by_phone(phone)
    user_id = existing[0] if existing else add_user(owner_name, phone)
    return add_business(user_id, business_name, business_phone, description)

def get_all_business_ids():
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM businesses")
    result = [row[0] for row in cursor.fetchall()]
    cursor.close(); conn.close()
    return result

# ---------- Clients ----------

def add_client(user_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO clients (user_id) VALUES (%s) RETURNING id", (user_id,))
    client_id = cursor.fetchone()[0]
    conn.commit(); cursor.close(); conn.close()
    return client_id

def get_client_by_user(user_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result[0] if result else None

def register_client(phone: str, name: str, email: str = None):
    existing = get_user_by_phone(phone)
    if existing:
        user_id = existing[0]
        if email:
            update_user_email(user_id, email)
    else:
        user_id = add_user(name, phone, email)

    client_id = get_client_by_user(user_id)
    if not client_id:
        client_id = add_client(user_id)
    return client_id

# ---------- Slots ----------

def add_slot(business_id, start_dt, end_dt):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO slots (business_id, slot_time, end_time) VALUES (%s, %s, %s)",
        (business_id, start_dt, end_dt)
    )
    conn.commit(); cursor.close(); conn.close()
    return True

def get_slot(business_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "SELECT id, slot_time, end_time FROM slots WHERE business_id = %s AND is_booked = FALSE",
        (business_id,)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def get_available_dates(business_id, year, month):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT DISTINCT slot_time::date FROM slots
           WHERE business_id = %s AND is_booked = FALSE
             AND EXTRACT(YEAR FROM slot_time) = %s
             AND EXTRACT(MONTH FROM slot_time) = %s""",
        (business_id, year, month)
    )
    result = {row[0] for row in cursor.fetchall()}
    cursor.close(); conn.close()
    return result

def get_next_available_date(business_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT MIN(slot_time::date) FROM slots
           WHERE business_id = %s AND is_booked = FALSE AND slot_time >= NOW()""",
        (business_id,)
    )
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result[0] if result else None

def get_slots_by_date(business_id, target_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT id, slot_time, end_time FROM slots
           WHERE business_id = %s AND is_booked = FALSE
             AND slot_time::date = %s AND slot_time >= NOW()
           ORDER BY slot_time""",
        (business_id, target_date)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def slot_exists(business_id, start_dt):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM slots WHERE business_id = %s AND slot_time = %s", (business_id, start_dt))
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result is not None

def book_slot(business_id, slot_id, client_id, client_name=None, client_phone=None, service_id=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """UPDATE slots
           SET is_booked = TRUE, client_id = %s, status = 'active',
               client_name = %s, client_phone = %s, service_id = %s
           WHERE id = %s AND business_id = %s AND is_booked = FALSE""",
        (client_id, client_name, client_phone, service_id, slot_id, business_id)
    )
    updated = cursor.rowcount > 0
    conn.commit(); cursor.close(); conn.close()
    return updated

def get_bookings(business_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT s.id, s.slot_time, s.end_time, s.client_name, s.client_phone, sv.name
           FROM slots s
           LEFT JOIN services sv ON sv.id = s.service_id
           WHERE s.business_id = %s AND s.is_booked = TRUE AND s.status = 'active'
           ORDER BY s.slot_time""",
        (business_id,)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def get_booking(business_id, slot_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """SELECT id, slot_time, end_time, client_id, status, client_name, client_phone
           FROM slots WHERE id = %s AND business_id = %s""",
        (slot_id, business_id)
    )
    result = cursor.fetchone()
    cursor.close(); conn.close()
    return result

def complete_booking(business_id, slot_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """UPDATE slots SET status = 'completed'
           WHERE id = %s AND business_id = %s AND is_booked = TRUE AND status = 'active'""",
        (slot_id, business_id)
    )
    updated = cursor.rowcount > 0
    conn.commit(); cursor.close(); conn.close()
    return updated

def cancel_booking(business_id, slot_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        """UPDATE slots SET is_booked = FALSE, client_id = NULL, status = 'free'
           WHERE id = %s AND business_id = %s AND is_booked = TRUE AND status = 'active'""",
        (slot_id, business_id)
    )
    updated = cursor.rowcount > 0
    conn.commit(); cursor.close(); conn.close()
    return updated

# ---------- Schedule template ----------

def add_schedule_template_entry(business_id, weekday, time_str, duration_minutes=60):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schedule_template (business_id, weekday, time, duration_minutes) VALUES (%s, %s, %s, %s)",
        (business_id, weekday, time_str, duration_minutes)
    )
    conn.commit(); cursor.close(); conn.close()
    return True

def get_schedule_template(business_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "SELECT weekday, time, duration_minutes FROM schedule_template WHERE business_id = %s",
        (business_id,)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def generate_slots_from_template(business_id, days_ahead=14):
    template = get_schedule_template(business_id)
    if not template:
        return 0

    created = 0
    today = datetime.now().date()

    for offset in range(days_ahead):
        target_date = today + timedelta(days=offset)
        weekday = target_date.weekday()

        for tpl_weekday, tpl_time, duration in template:
            if tpl_weekday != weekday:
                continue
            start_dt = datetime.combine(target_date, tpl_time)
            if start_dt < datetime.now() or slot_exists(business_id, start_dt):
                continue
            end_dt = start_dt + timedelta(minutes=duration)
            add_slot(business_id, start_dt, end_dt)
            created += 1

    return created

# ---------- Telegram linking (тільки для нагадувань) ----------

def create_telegram_link_token(user_id: int) -> str:
    token = secrets.token_urlsafe(16)
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO telegram_link_tokens (token, user_id) VALUES (%s, %s)", (token, user_id))
    conn.commit(); cursor.close(); conn.close()
    return token

def link_telegram_chat(token: str, chat_id: int) -> bool:
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM telegram_link_tokens WHERE token = %s", (token,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); conn.close()
        return False
    cursor.execute("UPDATE users SET telegram_chat_id = %s WHERE id = %s", (chat_id, row[0]))
    cursor.execute("DELETE FROM telegram_link_tokens WHERE token = %s", (token,))
    conn.commit(); cursor.close(); conn.close()
    return True

# ---------- Reminders ----------

def get_due_reminders():
    conn = get_connection(); cursor = conn.cursor()
    now = datetime.now()
    soon = now + timedelta(hours=1)
    cursor.execute(
        """SELECT s.id, s.slot_time, b.name, u.email, u.telegram_chat_id
           FROM slots s
           JOIN businesses b ON b.id = s.business_id
           LEFT JOIN clients c ON c.id = s.client_id
           LEFT JOIN users u ON u.id = c.user_id
           WHERE s.is_booked = TRUE AND s.status = 'active'
             AND s.slot_time BETWEEN %s AND %s AND s.reminder_sent = FALSE""",
        (now, soon)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def mark_reminder_sent(slot_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE slots SET reminder_sent = TRUE WHERE id = %s", (slot_id,))
    conn.commit(); cursor.close(); conn.close()

def add_service(business_id: int, name: str, duration_minutes: int, price: float = None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO services (business_id, name, duration_minutes, price) VALUES (%s, %s, %s, %s) RETURNING id",
        (business_id, name, duration_minutes, price)
    )
    service_id = cursor.fetchone()[0]
    conn.commit(); cursor.close(); conn.close()
    return service_id

def get_services(business_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, duration_minutes, price FROM services WHERE business_id = %s ORDER BY id",
        (business_id,)
    )
    result = cursor.fetchall()
    cursor.close(); conn.close()
    return result

def delete_service(service_id: int):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
    conn.commit(); cursor.close(); conn.close()
    return True