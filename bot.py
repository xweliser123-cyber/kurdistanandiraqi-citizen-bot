import csv
import sqlite3
import logging
import asyncio
import os
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.enums import ParseMode

# Bot Token from environment variable
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8484241315:AAECnYYIhFaJ04ZaXr4e3Zv3JhFyZ0h6-0A")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Logging setup
logging.basicConfig(level=logging.INFO)

# ONLY DUHOK DATABASE
DUHOK_DB_FILE = "duhok(skidrow).sqlite"
DUHOK_DB_URL = "https://transfer.it/t/2QsMbBkRmJBJ"

# Required Channel
REQUIRED_CHANNEL = "by omou"

async def download_database():
    """Download Duhok database if it doesn't exist."""
    if os.path.exists(DUHOK_DB_FILE):
        file_size = os.path.getsize(DUHOK_DB_FILE)
        if file_size > 1000:  # If file exists and has data
            logging.info(f"✅ Database already exists: {DUHOK_DB_FILE} ({file_size} bytes)")
            return True
    
    logging.info(f"📥 Downloading database: {DUHOK_DB_FILE}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DUHOK_DB_URL) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(DUHOK_DB_FILE, 'wb') as f:
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Log progress
                            if total_size > 0 and downloaded % (5*1024*1024) == 0:  # Every 5MB
                                percent = (downloaded / total_size) * 100
                                logging.info(f"   Progress: {percent:.1f}%")
                    
                    file_size = os.path.getsize(DUHOK_DB_FILE)
                    logging.info(f"✅ Downloaded: {DUHOK_DB_FILE} ({file_size} bytes)")
                    return True
                else:
                    logging.error(f"❌ Failed to download: HTTP {response.status}")
                    return False
    except Exception as e:
        logging.error(f"❌ Error downloading: {e}")
        return False

def log_search(user_id, username, searched_name):
    log_file = "search_logs.csv"
    file_exists = os.path.isfile(log_file)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Timestamp", "User ID", "Username", "Searched Name", "Database"])

        writer.writerow([current_time, user_id, username, searched_name, "Duhok"])

async def check_user_membership(user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logging.error(f"Error checking membership for {user_id}: {e}")
    return False

# Start command
@router.message(Command("start"))
async def start_command(message: Message):
    # Check if database exists
    if not os.path.exists(DUHOK_DB_FILE):
        await message.reply("⏳ داتابەیسی نەهاتیە دیتن. هیڤییە چەندێ خوەکێ بوێرە...")
        return
    
    # Check database size
    db_size = os.path.getsize(DUHOK_DB_FILE)
    if db_size < 1000:
        await message.reply("❌ داتابەیسی بەتاڵە. هیڤییە دووبارە هەوڵبدە.")
        return
    
    await message.reply("✅ داتابەیسی دهوک هاتە هەلبژارتن.\n\n🔍 ناڤێ دووانی یان سییانی بهنێڕە.....")

def search_users_by_names(first_name, father_name, grand_name=None):
    """Search for users in Duhok database."""
    if not os.path.exists(DUHOK_DB_FILE):
        logging.error(f"Database file not found: {DUHOK_DB_FILE}")
        return []
    
    if os.path.getsize(DUHOK_DB_FILE) == 0:
        logging.error(f"Database file is empty: {DUHOK_DB_FILE}")
        return []
    
    conn = sqlite3.connect(DUHOK_DB_FILE)
    cursor = conn.cursor()

    # Check if 'person' table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person';")
    if not cursor.fetchone():
        logging.error(f"Table 'person' not found in database")
        conn.close()
        return []

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

def search_users_by_fam_no(fam_no):
    """Search for all family members based on fam_no."""
    if not os.path.exists(DUHOK_DB_FILE):
        logging.error(f"Database file not found: {DUHOK_DB_FILE}")
        return []
    
    conn = sqlite3.connect(DUHOK_DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person';")
    if not cursor.fetchone():
        logging.error(f"Table 'person' not found in database")
        conn.close()
        return []

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

    # Check if database exists
    if not os.path.exists(DUHOK_DB_FILE):
        await message.reply("❌ داتابەیسی نەهاتیە دیتن. هیڤییە دووبارە هەوڵبدە.")
        return
    
    if os.path.getsize(DUHOK_DB_FILE) < 1000:
        await message.reply("❌ داتابەیسی بەتاڵە.")
        return

    search_query = message.text.strip()
    name_parts = search_query.split()
    first_name, father_name = name_parts[0], name_parts[1]
    grand_name = name_parts[2] if len(name_parts) == 3 else None

    # Log the search
    log_search(user_id, username, search_query)

    results = search_users_by_names(first_name, father_name, grand_name)

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
    fam_no = callback.data.split("_")[1]
    results = search_users_by_fam_no(fam_no)

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

# Add /link command
@router.message(Command("link"))
async def send_link_command(message: Message):
    transfer_link = "https://transfer.it/t/lSaGvsoTXT6b"
    await message.reply(f"📁 Download your files here:\n{transfer_link}")

# Add /status command
@router.message(Command("status"))
async def status_command(message: Message):
    """Check database status"""
    if os.path.exists(DUHOK_DB_FILE):
        size = os.path.getsize(DUHOK_DB_FILE)
        await message.reply(f"✅ داتابەیسی دهوک:\n{size:,} بایت\n\n📊 ئامادەیە بۆ گەرێ.")
    else:
        await message.reply("❌ داتابەیسی نەهاتیە دیتن.")

# Main entry point
async def main():
    # Download database on startup
    logging.info("🔍 Checking Duhok database...")
    await download_database()
    
    # Start the bot
    logging.info("🤖 Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

