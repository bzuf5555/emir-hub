import logging

from telegram.ext import Application, CommandHandler

from bot.handlers import cmd_start, cmd_status, cmd_check, cmd_coins, cmd_set_group
from config import config

logger = logging.getLogger("bot")


def create_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("coins", cmd_coins))
    app.add_handler(CommandHandler("setgroup", cmd_set_group))

    logger.info("Telegram bot sozlandi")
    return app
