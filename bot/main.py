import logging
import shlex

from telegram import Update
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


def allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in ALLOWED_USER_IDS)


def fmt_result(data: dict) -> str:
    stdout = (data.get("stdout") or "").strip()
    stderr = (data.get("stderr") or "").strip()
    code = data.get("exit_code", "?")

    text = f"Exit code: `{code}`\n"
    if stdout:
        text += f"\n```text\n{stdout}\n```"
    if stderr:
        text += f"\n\nstderr:\n```text\n{stderr}\n```"
    if not stdout and not stderr:
        text += "\n_No output._"
    return text[:3900]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    await update.message.reply_text(
        "📱 *Termux Remote*\\n\\nChoose an action:",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    raw = update.message.text.partition(" ")[2].strip()
    if not raw:
        await update.message.reply_text("Usage: `/run <command> [args...]`", parse_mode="Markdown")
        return

    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        await update.message.reply_text(f"❌ Invalid shell syntax: {exc}")
        return

    command, args = parts[0], parts[1:]
    await update.message.reply_text(f"⏳ Running `{command}`...", parse_mode="Markdown")
    try:
        result = await execute(command, args)
        await update.message.reply_text(fmt_result(result), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"❌ Agent error: `{exc}`", parse_mode="Markdown")


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not allowed(update):
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "home":
        await query.edit_message_text("📱 *Termux Remote*\\n\\nChoose an action:",
                                      parse_mode="Markdown", reply_markup=main_menu())
        return

    if data == "custom":
        await query.edit_message_text(
            "💻 *Custom Command*\\n\\n"
            "Send a message like:\\n"
            "`/run uptime`\\n"
            "`/run ls -lah`\\n"
            "`/run termux-battery-status`",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
        return

    if data == "refresh":
        try:
            result = await discover()
            count = len(result.get("commands", []))
            await query.edit_message_text(
                f"🔄 Discovered `{count}` Termux commands.",
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )
        except Exception as exc:
            await query.edit_message_text(f"❌ Refresh failed: `{exc}`",
                                          parse_mode="Markdown",
                                          reply_markup=main_menu())
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        result = await discover()
        installed = set(result.get("commands", []))
        if category not in CATEGORIES:
            await query.edit_message_text("Unknown category.", reply_markup=main_menu())
            return
        title = CATEGORIES[category][0]
        await query.edit_message_text(
            f"{title}\\n\\nChoose an API:",
            reply_markup=category_menu(category, installed),
        )
        return

    if data.startswith("api:"):
        command = data.split(":", 1)[1]
        await query.edit_message_text(f"⏳ Running `{command}`...", parse_mode="Markdown")
        try:
            result = await execute(command)
            await query.edit_message_text(
                f"🛠 `{command}`\\n\\n{fmt_result(result)}",
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )
        except Exception as exc:
            await query.edit_message_text(
                f"❌ `{command}` failed:\\n`{exc}`",
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    try:
        result = await health()
        await update.message.reply_text(f"🟢 Agent OK: `{result}`", parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"🔴 Agent unreachable: `{exc}`")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    if not ALLOWED_USER_IDS:
        raise RuntimeError("ALLOWED_USER_IDS is empty")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.run_polling()


if __name__ == "__main__":
    main()
