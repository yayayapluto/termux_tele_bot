from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CATEGORIES = {
    "device": ("📱 Device", {
        "termux-battery-status": "🔋 Battery",
        "termux-clipboard-get": "📋 Clipboard",
        "termux-clipboard-set": "📋 Set Clipboard",
        "termux-torch": "🔦 Torch",
        "termux-vibrate": "📳 Vibrate",
    }),
    "network": ("📡 Network", {
        "termux-wifi-connectioninfo": "📶 WiFi Info",
        "termux-wifi-scaninfo": "📡 WiFi Scan",
        "termux-telephony-cellinfo": "📱 Cell Info",
    }),
    "location": ("📍 Location", {
        "termux-location": "📍 Location",
    }),
    "camera": ("📷 Camera", {
        "termux-camera-info": "📷 Camera Info",
    }),
    "audio": ("🔊 Audio", {
        "termux-volume": "🔊 Volume",
        "termux-media-player": "🎵 Media Player",
    }),
    "notification": ("💬 Notification", {
        "termux-notification": "🔔 Notification",
        "termux-toast": "🍞 Toast",
    }),
    "utilities": ("🛠 Utilities", {
        "termux-speech-to-text": "🎙 Speech to Text",
        "termux-fingerprint": "👆 Fingerprint",
        "termux-dialog": "📝 Dialog",
        "termux-share": "↗️ Share",
    }),
}


def main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📱 Device", callback_data="cat:device"),
         InlineKeyboardButton("📡 Network", callback_data="cat:network")],
        [InlineKeyboardButton("📍 Location", callback_data="cat:location"),
         InlineKeyboardButton("📷 Camera", callback_data="cat:camera")],
        [InlineKeyboardButton("🔊 Audio", callback_data="cat:audio"),
         InlineKeyboardButton("💬 Notification", callback_data="cat:notification")],
        [InlineKeyboardButton("🛠 Utilities", callback_data="cat:utilities"),
         InlineKeyboardButton("💻 Custom Command", callback_data="custom")],
        [InlineKeyboardButton("🔄 Refresh APIs", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(buttons)


def category_menu(category: str, installed: set[str]) -> InlineKeyboardMarkup:
    title, commands = CATEGORIES[category]
    rows = []
    for command, label in commands.items():
        if command in installed:
            rows.append([InlineKeyboardButton(label, callback_data=f"api:{command}")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def available_menu(installed: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for command in installed[:40]:
        rows.append([InlineKeyboardButton(command, callback_data=f"api:{command}")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)
