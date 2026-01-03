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

# Database URLs - YOU MUST UPDATE THESE LINKS!
DATABASE_URLS = {
    "دهوک": "https://transfer.it/t/yOjPXctxiZoL/duhok(skidrow).sqlite",
}

# Local file names
DATABASE_FILES = {
    "دهوک": "duhok(skidrow).sqlite",
}

# Dictionary to store user-selected databases
user_databases = {}

# Required Channel
REQUIRED_CHANNEL = "by omou"

async def download_database(url, filename):
    """Download database file if it doesn't exist."""
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        if file_size > 1000:  # If file exists and has data
            logging.info(f"✅ Database already exists: {filename} ({file_size} bytes)")
            return True
    
    logging.info(f"📥 Downloading database: {filename}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Log progress for large files
                            if total_size > 0 and downloaded % (10*1024*1024) == 0:  # Every 10MB
                                percent = (downloaded / total_size) * 100
                                logging.info(f"   Downloading {filename}: {percent:.1f}%")
                    
                    file_size = os.path.getsize(filename)
                    logging.info(f"✅ Downloaded: {filename} ({file_size} bytes)")
                    return True
                else:
                    logging.error(f"❌ Failed to download {filename}: HTTP {response.status}")
                    return False
    except Exception as e:
        logging.error(f"❌ Error downloading {filename}: {e}")
        return False

async def check_and_download_databases():
    """Check and download all databases that don't exist."""
    tasks = []
    for db_name, url in DATABASE_URLS.items():
        filename = DATABASE_FILES[db_name]
        tasks.append(download_database(url, filename))
    
    results = await asyncio.gather(*tasks)
    successful = sum(results)
    logging.info(f"📊 Database download summary: {successful}/{len(results)} successful")
    return all(results)

def log_search(user_id, username, searched_name, database_name):
    log_file = "search_logs.csv"
    file_exists = os.path.isfile(log_file)

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Timestamp", "User ID", "Username", "Searched Name", "Database Name"])

        writer.writerow([current_time, user_id, username, searched_name, database_name])

async def check_user_membership(user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logging.error(f"Error checking membership for {user_id}: {e}")
    return False

# Start command (Database selection)
@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id

    db_list = list(DATABASE_FILES)
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
    user_databases[user_id] = DATABASE_FILES[selected_db]

    await callback.message.edit_text(f"✅ داتابەیسێ '{selected_db}' هاتە هەلبژارتن.\nهیڤییە بکیبورتێ عەرەبی ناڤی بنڤیسە.\n\n🔍 ناڤێ دووانی یان سییانی بهنێڕە.....")
    await callback.answer()

def search_users_by_names(db_path, first_name, father_name, grand_name=None):
    """Search for users in the selected database."""
    if not os.path.exists(db_path):
        logging.error(f"Database file not found: {db_path}")
        return []
    
    if os.path.getsize(db_path) == 0:
        logging.error(f"Database file is empty: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person';")
    if not cursor.fetchone():
        logging.error(f"Table 'person' not found in database: {db_path}")
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

def search_users_by_fam_no(db_path, fam_no):
    """Search for all family members based on fam_no."""
    if not os.path.exists(db_path):
        logging.error(f"Database file not found: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='person';")
    if not cursor.fetchone():
        logging.error(f"Table 'person' not found in database: {db_path}")
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

    if user_id not in user_databases:
        await message.reply("⚠️ هیڤییە هنارتنا راستەوخو `/start` بکاربینە بو دیارکرنا داتابەیسی.")
        return

    search_query = message.text.strip()
    name_parts = search_query.split()
    first_name, father_name = name_parts[0], name_parts[1]
    grand_name = name_parts[2] if len(name_parts) == 3 else None
    
    selected_db = user_databases[user_id]

    # Check if database exists
    if not os.path.exists(selected_db):
        await message.reply(f"❌ داتابەیسی '{selected_db}' نەهاتیە دیتن. هیڤییە دووبارە هەلبژێرە.")
        del user_databases[user_id]  # Clear selection
        return

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

        await message.reply(response_text, reply_mup=keyboard)

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

# Add /link command
@router.message(Command("link"))
async def send_link_command(message: Message):
    transfer_link = "https://transfer.it/t/lSaGvsoTXT6b"
    await message.reply(f"📁 Download your files here:\n{transfer_link}")

# Add /status command
@router.message(Command("status"))
async def status_command(message: Message):
    """Check database status"""
    response = "📊 Database Status:\n\n"
    
    total_count = len(DATABASE_FILES)
    downloaded_count = 0
    
    for db_name, filename in DATABASE_FILES.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            downloaded_count += 1
            response += f"✅ {db_name}: {size:,} bytes\n"
        else:
            response += f"❌ {db_name}: Not downloaded\n"
    
    response += f"\n📈 {downloaded_count}/{total_count} databases available"
    await message.reply(response)

# Main entry point
async def main():
    # Download databases on startup
    logging.info("🔍 Checking database files...")
    await check_and_download_databases()
    
    # Start the bot
    logging.info("🤖 Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

