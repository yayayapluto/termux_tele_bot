import os
from dotenv import load_dotenv

load_dotenv("bot/.env")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if x.strip()
}
AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:8787").rstrip("/")
AGENT_TOKEN = os.environ["AGENT_TOKEN"]
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "12000"))
