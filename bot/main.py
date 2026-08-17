import logging
import shlex

from telegram import Update
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from bot.keyboards import main_menu, category_menu, available_menu, CATEGORIES
from bot.termux_client import discover, execute, health

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

WELCOME_TEXT = (
    "📱 *Termux Remote*\n\n"
    "Pilih aksi yang ingin dijalankan"
)


def allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in ALLOWED_USER_IDS)


def mdv2(text: object) -> str:
    return escape_markdown(str(text), version=2)


def inline_code(text: object) -> str:
    escaped = escape_markdown(str(text), version=2, entity_type="code")
    return f"`{escaped}`"


def pre_block(text: object) -> str:
    escaped = escape_markdown(str(text), version=2, entity_type="pre")
    return f"```\n{escaped}\n```"


def fmt_result(data: dict) -> str:
    stdout = (data.get("stdout") or "").strip()
    stderr = (data.get("stderr") or "").strip()
    code = data.get("exit_code", "?")

    text = f"Exit code: {inline_code(code)}"
    if stdout:
        text += f"\n\nstdout:\n{pre_block(stdout)}"
    if stderr:
        text += f"\n\nstderr:\n{pre_block(stderr)}"
    if not stdout and not stderr:
        text += "\n\nNo output"
    return text[:3900]


def user_label(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "unknown"
    return f"{user.id} ({user.username or user.full_name})"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        log.warning("Unauthorized /start from %s", user_label(update))
        await update.message.reply_text("⛔ Unauthorized", parse_mode=ParseMode.MARKDOWN_V2)
        return

    log.info("/start by %s", user_label(update))

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu(),
    )


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        log.warning("Unauthorized /run from %s", user_label(update))
        await update.message.reply_text("⛔ Unauthorized", parse_mode=ParseMode.MARKDOWN_V2)
        return

    raw = update.message.text.partition(" ")[2].strip()
    if not raw:
        await update.message.reply_text(
            "Format perintah belum lengkap\n"
            "Gunakan: `/run <command> [args...]`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        log.info("Invalid shell syntax from %s: %s", user_label(update), exc)
        await update.message.reply_text(
            f"❌ Invalid shell syntax: {inline_code(exc)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    command, args = parts[0], parts[1:]
    log.info("/run requested by %s: %s args=%s", user_label(update), command, args)
    await update.message.reply_text(
        f"⏳ Menjalankan {inline_code(command)}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    try:
        result = await execute(command, args)
        log.info(
            "Command result for %s: %s exit_code=%s",
            user_label(update),
            command,
            result.get("exit_code"),
        )
        await update.message.reply_text(fmt_result(result), parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as exc:
        log.exception("Agent error while /run %s by %s", command, user_label(update))
        await update.message.reply_text(
            f"❌ Agent error: {inline_code(exc)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not allowed(update):
        log.warning("Unauthorized callback from %s", user_label(update))
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer()
    data = query.data
    log.info("Callback by %s: %s", user_label(update), data)

    if data == "home":
        await query.edit_message_text(WELCOME_TEXT,
                                      parse_mode=ParseMode.MARKDOWN_V2, reply_markup=main_menu())
        return

    if data == "custom":
        await query.edit_message_text(
            "💻 *Custom Command*\n\n"
            "Kirim perintah dengan format:\n"
            "`/run uptime`\n"
            "`/run ls -lah`\n"
            "`/run termux-battery-status`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu(),
        )
        return

    if data == "refresh":
        try:
            result = await discover()
            count = len(result.get("commands", []))
            await query.edit_message_text(
                f"🔄 Berhasil memuat {inline_code(count)} command Termux",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=main_menu(),
            )
            log.info("Refresh commands by %s count=%s", user_label(update), count)
        except Exception as exc:
            log.exception("Refresh failed for %s", user_label(update))
            await query.edit_message_text(f"❌ Refresh failed: {inline_code(exc)}",
                                          parse_mode=ParseMode.MARKDOWN_V2,
                                          reply_markup=main_menu())
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        result = await discover()
        installed = set(result.get("commands", []))
        if category not in CATEGORIES:
            log.warning("Unknown category '%s' from %s", category, user_label(update))
            await query.edit_message_text("Kategori tidak dikenal", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=main_menu())
            return
        title = CATEGORIES[category][0]
        await query.edit_message_text(
            f"{mdv2(title)}\n\nPilih API yang ingin dijalankan:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=category_menu(category, installed),
        )
        return

    if data.startswith("api:"):
        command = data.split(":", 1)[1]
        log.info("API command by %s: %s", user_label(update), command)
        await query.edit_message_text(
            f"⏳ Menjalankan {inline_code(command)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        try:
            result = await execute(command)
            await query.edit_message_text(
                f"🛠 {inline_code(command)}\n\n{fmt_result(result)}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=main_menu(),
            )
            log.info("API command result for %s: %s exit_code=%s", user_label(update), command, result.get("exit_code"))
        except Exception as exc:
            log.exception("API command failed for %s: %s", user_label(update), command)
            await query.edit_message_text(
                f"❌ {inline_code(command)} failed:\n{inline_code(exc)}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=main_menu(),
            )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        log.warning("Unauthorized /status from %s", user_label(update))
        await update.message.reply_text("⛔ Unauthorized", parse_mode=ParseMode.MARKDOWN_V2)
        return
    try:
        result = await health()
        log.info("/status OK for %s: %s", user_label(update), result)
        await update.message.reply_text(
            f"🟢 Agent terhubung: {inline_code(result)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as exc:
        log.exception("/status failed for %s", user_label(update))
        await update.message.reply_text(
            f"🔴 Agent tidak terjangkau: {inline_code(exc)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    if not ALLOWED_USER_IDS:
        raise RuntimeError("ALLOWED_USER_IDS is empty")

    log.info("Starting bot with %s allowed user(s)", len(ALLOWED_USER_IDS))

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.run_polling()


if __name__ == "__main__":
    main()
