import csv
import sqlite3
import logging
import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import Command
from aiogram import F  # instead of filters
from aiogram.enums import ParseMode

async def send_link():
    bot = Bot(token="8484241315:AAECnYYIhFaJ04ZaXr4e3Zv3JhFyZ0h6-0A")
    transfer_link = "https://transfer.it/t/lSaGvsoTXT6b"
    await bot.send_message(
        chat_id=USER_CHAT_ID,
        text=f"📁 Download your files here:\n{https://transfer.it/t/lSaGvsoTXT6b}"
    )

asyncio.run(send_link())


# Bot Token
BOT_TOKEN = "8484241315:AAECnYYIhFaJ04ZaXr4e3Zv3JhFyZ0h6-0A"

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Available Databases
DATABASES = {
    "دهوک": "duhok(skidrow).sqlite",
    "ئەنبار": "al-anbar(skidrow).sqlite",
    "کەرکوک": "kirkuk(skidrow).sqlite",
    "بابل": "babylon(skidrow).sqlite",
    "میسان": "mesan(skidrow).sqlite",
    "بەلەد": "balad(skidrow).sqlite",
    "موسەنا": "muthana(skidrow).sqlite",
    "نەجەف": "najaf(skidrow).sqlite",
    "زیقار": "dhiqar(skidrow).sqlite",
    "دیالا": "diyala(skidrow).sqlite",
    "قادسییە": "qadisiya(skidrow).sqlite",
    "هەولێر": "erbil(skidrow).sqlite",
    "سەلاحەدین": "salah-aldeen(skidrow).sqlite",
    "سێلمانی": "sulaymaniyah(skidrow).sqlite",
    "واست": "wasit(skidrow).sqlite",
    "نەینەوا (میسل)": "nineveh(skidrow).sqlite",
    "بەصرا": "basra(skidrow).sqlite",
    "": ""
}

# Dictionary to store user-selected databases
user_databases = {}

# Required Channel
REQUIRED_CHANNEL = "by omou"

def log_search(user_id, username, searched_name, database_name):
    log_file = "search_logs.csv"
    file_exists = os.path.isfile(log_file)

    # Get the current date and time in "YYYY-MM-DD HH:MM:SS" format
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        # Write header if file is newly created
        if not file_exists:
            writer.writerow(["Timestamp", "User ID", "Username", "Searched Name", "Database Name"])

        # Write log entry with timestamp
        writer.writerow([current_time, user_id, username, searched_name, database_name])

async def check_user_membership(user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logging.error(f"Error checking membership for {user_id}: {e}")
    return False

# Create the join channel button

# Start command (Database selection)
@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id

    db_list = list(DATABASES)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=db_name, callback_data=f"db_{db_name}")
             for db_name in db_list[i:i+3]]
            for i in range(0, len(db_list), 3)
        ]
    )

    await message.reply("📌 هیڤییە بنکەیێ داتابەیسی بهەلبژێرە:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("db_"))
async def select_database(callback: CallbackQuery):
    """Store the selected database and notify the user."""
    user_id = callback.from_user.id
    selected_db = callback.data.split("_")[1]
    user_databases[user_id] = DATABASES[selected_db]

    await callback.message.edit_text(f"✅ داتابەیسێ '{selected_db}' هاتە هەلبژارتن.\nهیڤییە بکیبورتێ عەرەبی ناڤی بنڤیسە.\n\n🔍 ناڤێ دووانی یان سییانی بهنێڕە.....")
    await callback.answer()


    if user_id not in user_databases:
        await message.reply("⚠️ هیڤییە هنارتنا راستەوخو `/start` بکاربینە بو دیارکرنا داتابەیسی.")
        return

    await message.reply("🔍 ناڤێ دووانی یان سییانی بهنێڕە.....")

def search_users_by_names(db_path, first_name, father_name, grand_name=None):
    """Search for users in the selected database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """SELECT rc_no, fam_no, seq_no, p_first, p_father, p_grand, p_birth, ss_lg_no, ss_pg_no, p_case, p_job, p_mother, gr_mother, ss_br_nm
               FROM person
               WHERE p_first LIKE ? AND p_father LIKE ?"""

    params = [f"{first_name}%", f"{father_name}%"]

    if grand_name:
        query += " AND p_grand LIKE ?"
        params.append(f"{grand_name}%")

    query += " LIMIT 500"

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return results

def search_users_by_fam_no(db_path, fam_no):
    """Search for all family members based on fam_no."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """SELECT rc_no, fam_no, seq_no, p_first, p_father, p_grand, p_birth, ss_lg_no, ss_pg_no, p_case, p_job, p_mother, gr_mother, ss_br_nm
               FROM person WHERE fam_no = ?"""
    
    cursor.execute(query, (fam_no,))
    results = cursor.fetchall()
    conn.close()

    return results

@router.message(lambda message: len(message.text.split()) >= 2 and len(message.text.split()) <= 3)
async def member_search(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "No Username"


    if user_id not in user_databases:
        await message.reply("⚠️ هیڤییە هنارتنا راستەوخو `/start` بکاربینە بو دیارکرنا داتابەیسی.")
        return

    search_query = message.text.strip()
    name_parts = search_query.split()
    first_name, father_name = name_parts[0], name_parts[1]
    grand_name = name_parts[2] if len(name_parts) == 3 else None
    
    selected_db = user_databases[user_id]

    # Log the search
    log_search(user_id, username, search_query, selected_db)

    results = search_users_by_names(selected_db, first_name, father_name, grand_name)

    if not results:
        await message.reply("❌ چ زانیاری نەهاتنە دیتن بو ڤی ناڤی.")
        return


    for row in results:
        rc_no, fam_no, seq_no, p_first, p_father, p_grand, p_birth, ss_lg_no, ss_pg_no, p_case, p_job, p_mother, gr_mother, ss_br_nm = row
        if isinstance(p_birth, (int, float)) and p_birth > 0:
            birth_year = int(str(int(p_birth))[:4])
            age = 2025 - birth_year
            age_text = f"ژی: {age}\n"
        else:
            age_text = "- ژی: UNKNOWN"
        response_text = (
            f"هەر کارەکێ بێ ئەخلاق تو بکەی ئەم نە بەرپرسن. by omou\n"
            f"\n"
            f"- کەسێ {seq_no} یێ خێزانێ:\n"
            f"- ناڤ: {p_first}\n"
            f"- باب: {p_father}\n"
            f"- باپیر: {p_grand}\n"
            f"- دەیک: {p_mother}\n"
            f"- بابێ دەیکێ: {gr_mother}\n"
            f"- ژدایکبوون: {str(p_birth)[:4]}\n"
            f"- {age_text}"
            f"- دوخێ یاسای: {p_case}\n"
            f"- دەڤەر: {ss_br_nm}\n"
            f"- گەڕەک: {rc_no}\n"
            f"- کولان: {ss_lg_no}\n"
            f"- خانی: {ss_pg_no}\n"
            f"- کار: {p_job}\n"
            f"\n"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📂 ڤێ خێزانێ ببینە", callback_data=f"family_{fam_no}")]]
        )

        await message.reply(response_text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("family_"))
async def family_search_callback(callback: CallbackQuery):
    """Search and send all family members when the button is clicked."""
    user_id = callback.from_user.id
    if user_id not in user_databases:
        await callback.answer("⚠️ هیڤییە هنارتنا راستەوخو `/start` بکاربینە بو دیارکرنا داتابەیسی.")
        return

    fam_no = callback.data.split("_")[1]
    results = search_users_by_fam_no(user_databases[user_id], fam_no)

    if not results:
        await callback.answer("❌ چ زانیاری نەهاتنە دیتن بو ڤی ژمارا خێزانێ.")
        return

    response_text = f"خێزانا ژمارە : {fam_no}\n\n"

    for row in results:
        rc_no, fam_no, seq_no, p_first, p_father, p_grand, p_birth, ss_lg_no, ss_pg_no, p_case, p_job, p_mother, gr_mother, ss_br_nm = row
        if isinstance(p_birth, (int, float)) and p_birth > 0:
            birth_year = int(str(int(p_birth))[:4])
            age = 2025 - birth_year
            age_text = f"ژی: {age}\n"
        else:
            age_text = "- ژی: UNKNOWN"
        response_text += (
            f"هەر کارەکێ بێ ئەخلاق تو بکەی ئەم نە بەرپرسن. by omou\n"
            f"\n"
            f"- کەسێ {seq_no} یێ خێزانێ:\n"
            f"- ناڤ: {p_first}\n"
            f"- باب: {p_father}\n"
            f"- باپیر: {p_grand}\n"
            f"- دەیک: {p_mother}\n"
            f"- بابێ دەیکێ: {gr_mother}\n"
            f"- ژدایکبوون: {str(p_birth)[:4]}\n"
            f"- {age_text}"
            f"- دوخێ یاسای: {p_case}\n"
            f"- دەڤەر: {ss_br_nm}\n"
            f"- گەڕەک: {rc_no}\n"
            f"- کولان: {ss_lg_no}\n"
            f"- خانی: {ss_pg_no}\n"
            f"- کار: {p_job}\n"
            f"\n"
        )

    await callback.message.reply(response_text)
    await callback.answer()

# Main entry point
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())




