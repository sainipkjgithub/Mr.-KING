from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,Message, ReplyKeyboardRemove , ForceReply
import requests
import json
import threading
import time
from flask import Flask
import requests
import time
import json
import os
import uuid
from FUNCTIONS.functions import sendAi_message,clear_history
from dotenv import load_dotenv
import os

load_dotenv()  # .env फ़ाइल को लोड करें

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
API_BASE = os.getenv("API_BASE")
ADMINS = list(map(int, os.getenv("ADMINS").split(',')))
channel_id = CHANNEL_ID 
user_status = {}
bot = Client("mvp2028_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Mr. King in Working..."
# Cache for user history
folder_cache = {"tree": None, "timestamp": 0}
user_history = {}  # user_id: [folder_id_stack]
awaiting_upload = {}  # user_id: folder_id waiting for upload
file_id_map = {}  # short_id: original_file_id
def load_cached_tree(force_refresh=False):
    current_time = time.time()
    if not force_refresh and folder_cache["tree"] and (current_time - folder_cache["timestamp"]) < 300:
        return folder_cache["tree"]

    res = requests.get(f"{API_BASE}/data.json")
    if res.status_code == 200:
        folder_cache["tree"] = res.json()
        folder_cache["timestamp"] = current_time
    return folder_cache["tree"]

def find_folder_by_id(tree, folder_id):
    if isinstance(tree, dict):
        for name, node in tree.items():
            if isinstance(node, dict) and node.get("id") == folder_id:
                return node
            if "folders" in node:
                result = find_folder_by_id(node["folders"], folder_id)
                if result:
                    return result
    elif isinstance(tree, list):
        for node in tree:
            if isinstance(node, dict) and node.get("id") == folder_id:
                return node
            if "folders" in node:
                result = find_folder_by_id(node["folders"], folder_id)
                if result:
                    return result
    return None
def get_folder_name_by_id(tree, folder_id):
    for name, node in tree.items():
        if isinstance(node, dict) and node.get("id") == folder_id:
            return name
        if isinstance(node, dict) and "folders" in node:
            result = get_folder_name_by_id(node["folders"], folder_id)
            if result:
                return result
    return None
home_keyboard = InlineKeyboardMarkup([
         [InlineKeyboardButton("💬 Chat With Upsc Assistant", callback_data="chat_with_assistant")],
         [InlineKeyboardButton("Study Materials", callback_data="open:root")],
        [InlineKeyboardButton("ℹ️ About Us", callback_data="about_us")]
    ])
    
@bot.on_message(filters.command("start") & ~filters.me)
async def start(client, message):
    user_history[message.from_user.id] = []
    await message.reply("Welcome, Hello 👋 ♤ I am Mr. King Your Study Helper. Choose an Option Below", reply_markup=home_keyboard)
    #await send_folder_list(client, message.chat.id, "abc123")  # root id

@bot.on_callback_query(filters.regex("about_us") & ~filters.me)
async def About_us(client, callback_query):
  await callback_query.message.edit_text("""
I am Mr. King, an intelligent assistant developed with passion and purpose by Mr. Singodiya.
I'm not just a bot — I'm your personal UPSC companion, guiding you every step of the way.

Whether it's syllabus tracking, smart study planning, notes management, daily targets, or motivational support — I’ve got you covered.

Our mission is clear:
To build a focused, disciplined, and smart community of aspirants who are determined to crack the UPSC, no matter what it takes.

Let’s eliminate distractions, maximize productivity, and make your UPSC journey strategic and stress-free.
Together, we don’t just prepare — we conquer.

""",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔒CLOSE", callback_data="home")]]))
  
  
def generate_short_id():
    return uuid.uuid4().hex[:8]  # 8-character unique ID

@bot.on_callback_query(filters.regex("chat_with_assistant") & ~filters.me)
async def Ai_Assistant(client, callback_query):
        query = callback_query
        user_id = callback_query.from_user.id  # Get user ID
        user_name = callback_query.from_user.first_name 
        await callback_query.message.edit_text("We are Connecting You to UPSC Ai Assistent...")
        time.sleep(2)
        await query.message.delete()
        chat_with_assistant = ReplyKeyboardMarkup(
    [[KeyboardButton("🚫CANCEL")]],
    resize_keyboard=True
)
        a=await query.message.reply_text(f"Hello {user_name}, How can I assist you today..?",reply_markup=chat_with_assistant)
        user_history[user_id] = {}
        user_history[user_id]["state"] = "ai_chat"

@bot.on_message(filters.text & ~filters.me & ~filters.group & ~filters.command("start") & filters.regex(r"^🚫CANCEL$"))
def canclemsg(client: Client, message: Message):
    user_id = message.from_user.id
    user_msg = message.text
    user_name = message.from_user.first_name
    if user_history[user_id]["state"] == "ai_chat":
      clear_history
      del user_history[user_id]
      msg12 = message.reply_text("Session Canceled!", reply_markup=ReplyKeyboardRemove())
      time.sleep(0.7)
      msg12.delete()
      message.reply_text(
        "Welcome, Hello 👋 ♤ I am Mr. King Your Study Helper. Choose an Option Below",
        reply_markup=home_keyboard)

@bot.on_callback_query(filters.regex("^home") & ~filters.me)
async def home(client, callback_query):   
  await callback_query.message.edit_text("Welcome, Hello 👋 ♤ I am Mr. King Your Study Helper. Choose an Option Below",reply_markup=home_keyboard)

@bot.on_callback_query(filters.regex("^file:(.+)") & ~filters.me)
async def send_file(client, callback_query):
    short_id = callback_query.data.split(":")[1]
    file_id = file_id_map.get(short_id)
    if file_id:
        await client.send_document(callback_query.message.chat.id, file_id)
    else:
        await callback_query.answer("File not found.", show_alert=True)


async def send_folder_list(client, user_id, folder_id, msg=None):
    tree = load_cached_tree()
    folder = find_folder_by_id(tree, folder_id)

    if not folder:
        await client.send_message(user_id, "Folder not found.")
        return

    folders = folder.get("folders", {})
    files = folder.get("files", [])
    description = folder.get("description", "Choose an option:")

    if not isinstance(folders, dict):
        folders = {}

    keyboard = []

    for name, data in folders.items():
        keyboard.append([InlineKeyboardButton(f"📂 {name}", callback_data=f"open:{data['id']}")])

    for file in files:
        fname = file.get("File Name", "Unnamed")
        file_id = file["file_id"]

        for k, v in file_id_map.items():
            if v == file_id:
                short_id = k
                break
        else:
            short_id = generate_short_id()
            file_id_map[short_id] = file_id

        keyboard.append([InlineKeyboardButton(f"🗄 {fname}", callback_data=f"file:{short_id}")])

    if user_id in ADMINS:
        keyboard.append([
            InlineKeyboardButton("➕️ Add New Folder", callback_data=f"add:{folder_id}"),
            InlineKeyboardButton("➕️ Upload File", callback_data=f"upload:{folder_id}")
        ])
    if folder_id == "root": 
        keyboard.append([
            InlineKeyboardButton("⚜️HOME", callback_data=f"home")
        ])
    if folder_id != "root":
        keyboard.append([
            InlineKeyboardButton("🔙 Back", callback_data=f"back:{folder_id}"),
            InlineKeyboardButton("⚜️HOME", callback_data=f"home")
        ])

    if msg:
        await msg.edit_text(description, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await client.send_message(user_id, description, reply_markup=InlineKeyboardMarkup(keyboard))


@bot.on_callback_query(filters.regex("^open:(.+)") & ~filters.me)
async def open_folder(client, callback_query):
    folder_id = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    user_history.setdefault(user_id, []).append(folder_id)
    await send_folder_list(client, user_id, folder_id, callback_query.message)

@bot.on_callback_query(filters.regex("^back:(.+)") & ~filters.me)
async def go_back(client, callback_query):
    current_folder_id = callback_query.data.split(":")[1]
    tree = load_cached_tree()

    def find_parent_id(tree, target_id, parent_id=None):
        if isinstance(tree, dict):
            for name, node in tree.items():
                if isinstance(node, dict) and node.get("id") == target_id:
                    return parent_id
                if isinstance(node, dict) and "folders" in node:
                    result = find_parent_id(node["folders"], target_id, node.get("id"))
                    if result:
                        return result
        elif isinstance(tree, list):
            for node in tree:
                if isinstance(node, dict) and node.get("id") == target_id:
                    return parent_id
                if "folders" in node:
                    result = find_parent_id(node["folders"], target_id, node.get("id"))
                    if result:
                        return result
        return None

    parent_id = find_parent_id(tree, current_folder_id)

    if parent_id:
        await send_folder_list(client, callback_query.message.chat.id, parent_id, callback_query.message)
    else:
        await client.send_message(callback_query.message.chat.id, "No parent folder found.")


@bot.on_callback_query(filters.regex("^add:(.+)") & ~filters.me)
async def ask_new_folder_name(client, callback_query):
    folder_id = callback_query.data.split(":")[1]
    user_history[callback_query.from_user.id] = {
        "state": "awaiting_folder_name",
        "parent_id": folder_id
    }
    await client.send_message(callback_query.message.chat.id, "Send the *name* of the new folder.")

@bot.on_callback_query(filters.regex("^upload:(.+)") & ~filters.me)
async def request_file_upload(client, callback_query):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("You are not allowed to upload files.", show_alert=True)
        return

    folder_id = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    awaiting_upload[user_id] = {
        "folder_id": folder_id,
        "pending_files": []
    }
    await client.send_message(user_id, "Please upload file(s) now.")
@bot.on_message(filters.text & ~filters.command("start") & ~filters.me)
async def receive_folder_details(client, message):
    user_id = message.from_user.id

    if user_id not in user_history:
        return

    state_data = user_history[user_id]

    if state_data.get("state") == "awaiting_folder_name":
        user_history[user_id]["folder_name"] = message.text.strip()
        user_history[user_id]["state"] = "awaiting_folder_description"
        await message.reply("Send the *description* of the new folder.")

    elif state_data.get("state") == "awaiting_folder_description":
        folder_name = state_data["folder_name"]
        folder_description = message.text.strip()
        parent_id = state_data["parent_id"]

        response = requests.post(f"{API_BASE}/add_folder.php", json={
            "parent_id": parent_id,
            "folder_name": folder_name,
            "description": folder_description
        })

        if response.status_code == 200:
            folder_cache["timestamp"] = 0
            await message.reply(f"Folder '{folder_name}' added with description.")
        else:
            await message.reply("Error adding folder.")

        del user_history[user_id]
        await send_folder_list(client, message.chat.id, parent_id)

    elif state_data.get("state") == "awaiting_file_rename":
        short_id = state_data["short_id"]
        new_name_raw = message.text.strip()

        user_data = awaiting_upload.get(user_id)
        if not user_data:
            await message.reply("No upload session found.")
            return

        file_entry = next((f for f in user_data["pending_files"] if f["short_id"] == short_id), None)
        if not file_entry:
            await message.reply("File not found.")
            return

        old_name = file_entry["file_name"]
        ext = os.path.splitext(old_name)[1]
        if not new_name_raw.lower().endswith(ext):
            new_name = new_name_raw + ext
            file_entry["file_name"] = new_name
        else:
            new_name = new_name_raw 
            file_entry["file_name"] = new_name

        del user_history[user_id]

        full_path = build_full_path(user_data["folder_id"]) + "/" + new_name
        caption = f"**{new_name}**\n`{full_path}`"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Upload Confirm", callback_data=f"confirm:{short_id}"),
                InlineKeyboardButton("✏️ Rename", callback_data=f"rename:{short_id}")
            ]
        ])

        await client.send_document(
            chat_id=user_id,
            document=file_entry["file_id"],
            caption=caption,
            reply_markup=buttons
        )

    elif state_data.get("state") == "ai_chat":
        user_msg = message.text
        user_name = message.from_user.first_name
        answer = sendAi_message(user_id, user_name, user_msg)
        await message.reply_text(answer)

@bot.on_callback_query(filters.regex("^confirm:(.+)"))
async def confirm_upload(client, callback_query):
    user_id = callback_query.from_user.id
    short_id = callback_query.data.split(":")[1]

    user_data = awaiting_upload.get(user_id)
    if not user_data:
        await callback_query.answer("No pending uploads found.", show_alert=True)
        return

    file_entry = next((f for f in user_data["pending_files"] if f["short_id"] == short_id), None)
    if not file_entry:
        await callback_query.answer("File not found.", show_alert=True)
        return

    # API call to save file
    response = requests.post(f"{API_BASE}/add_file.php", json={
        "parent_id": user_data["folder_id"],
        "file_name": file_entry["file_name"],
        "file_id": file_entry["file_id"]
    })

    if response.status_code == 200:
        folder_cache["timestamp"] = 0
        await callback_query.message.edit_caption(
            caption=f"✅ File '{file_entry['file_name']}' uploaded successfully.",
            reply_markup=None
        )
        user_data["pending_files"].remove(file_entry)

        # अगर सब फाइल्स हो गईं, तो यूज़र को folder दिखा दो
        if not user_data["pending_files"]:
            del awaiting_upload[user_id]
            await send_folder_list(client, user_id, user_data["folder_id"])
    else:
        await callback_query.answer("Failed to upload file.", show_alert=True)
@bot.on_callback_query(filters.regex("^rename:(.+)"))
async def ask_new_file_name(client, callback_query):
    user_id = callback_query.from_user.id
    short_id = callback_query.data.split(":")[1]

    user_data = awaiting_upload.get(user_id)
    if not user_data:
        await callback_query.answer("No pending uploads found.", show_alert=True)
        return

    file_entry = next((f for f in user_data["pending_files"] if f["short_id"] == short_id), None)
    if not file_entry:
        await callback_query.answer("File not found.", show_alert=True)
        return
    
    user_history[user_id] = {
        "state": "awaiting_file_rename",
        "short_id": short_id
    }
    file_id = file_entry["file_id"]
    await callback_query.message.delete()
    await client.send_document(
        chat_id=user_id,
        document=file_id,
        caption=f"✏️ Rename File Name :\n ** Current File Name :**\n `{file_entry['file_name']}`\n Please Provide a New File Name.")
    

@bot.on_message(filters.document & ~filters.me)
async def handle_uploaded_file(client, message):
    user_id = message.from_user.id
    if user_id not in ADMINS or user_id not in awaiting_upload:
        return

    folder_id = awaiting_upload[user_id]["folder_id"]

    # Forward to channel to get permanent file_id
    fwd = await message.forward(channel_id)
    file_id = fwd.document.file_id
    file_name = fwd.document.file_name
    short_id = generate_short_id()

    # Cache file
    awaiting_upload[user_id]["pending_files"].append({
        "short_id": short_id,
        "file_name": file_name,
        "file_id": file_id
    })

    # Path बनाओ
    full_path = build_full_path(folder_id)

    await client.send_document(
        chat_id=user_id,
        document=file_id,
        caption=f"**File:** {file_name}\n**Path:** {full_path}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Upload Confirm", callback_data=f"confirm:{short_id}"),
                InlineKeyboardButton("✏️ Rename", callback_data=f"rename:{short_id}")
            ]
        ])
    )
def build_full_path(folder_id):
    data = load_cached_tree()
    path = []

    def dfs(node, target, current_path):
        if isinstance(node, dict):
            for name, info in node.items():
                if isinstance(info, dict) and "id" in info and info["id"] == target:
                    path.extend(current_path + [name])
                    return True
                if "folders" in info and dfs(info["folders"], target, current_path + [name]):
                    return True

        elif isinstance(node, list):
            for item in node:
                if "id" in item and item["id"] == target:
                    path.extend(current_path + [item.get("name", "Unnamed")])
                    return True
                if "folders" in item and dfs(item["folders"], target, current_path + [item.get("name", "Unnamed")]):
                    return True

        return False

    dfs(data, folder_id, ["Root"])
    return "/".join(path)

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

# Function to run Pyrogram bot
def run_bot():
    print("Bot is running...")
    bot.run()

if __name__ == "__main__":
    print("Bot is running...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run()
    print("Stopped Successfully")