#@cantarellabots
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", 29245477))
API_HASH = os.environ.get("API_HASH", "0abc83883262245c90ca337b7a0375c4")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8886986383:AAGcV93SOFSJQsaMwst3MQykyGxPuFdL9rs")

SET_INTERVAL = int(os.environ.get("SET_INTERVAL", 60))  # in seconds, default 1 hour
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID", "-1004384586427")
MAIN_CHANNEL = os.environ.get("MAIN_CHANNEL", "-1003705304493") # Change as needed
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-1003928914916")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://kayaxrobot:yzSgHQLteJCTXUqK@cluster0.ltk8k8h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_NAME = os.environ.get("MONGO_NAME", "cluster0")
OWNER_ID = int(os.environ.get("OWNER_ID", "8876236699"))
ADMIN_URL = os.environ.get("ADMIN_URL", "https://t.me/EternalsHelplineBot")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "ToukaXRobot")
FSUB_PIC = os.environ.get("FSUB_PIC", "https://files.catbox.moe/bli70r.jpg")
FSUB_LINK_EXPIRY = int(os.environ.get("FSUB_LINK_EXPIRY", 600))
START_PIC =os.environ.get("START_PIC", "https://files.catbox.moe/4b8jvw.jpg")

# ─── Filename & Caption Formats ───
FORMAT = os.environ.get("FORMAT", "[E{episode}] {title} [{quality}] [{audio}]")
CAPTION = os.environ.get("CAPTION", "{FORMAT}")

# ─── Progress Bar Settings ───
PROGRESS_BAR = os.environ.get("PROGRESS_BAR", """
<blockquote> {bar} </blockquote>
<blockquote>📁 <b>{title}</b>
⚡ Speed: {speed}
📦 {current} / {total}</blockquote>
""")

# ─── Response Images ───
# Rotating anime images sent with every bot reply. Add as many as you like.
RESPONSE_IMAGES = [
    "https://files.catbox.moe/5oonsm.jpg",
    "https://files.catbox.moe/9ufgme.jpg",
    "https://files.catbox.moe/4b8jvw.jpg",
    "https://files.catbox.moe/bli70r.jpg",
    "https://files.catbox.moe/uce0lw.jpg",
    "https://files.catbox.moe/is7q4q.jpg"
]
