import logging

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)

from bot.handlers import (
    cmd_start, cmd_coins, cmd_set_group,
    on_group_selected, on_action_message, on_action_check,
    on_back_start, receive_message, WAITING_MESSAGE,
    on_task_confirm,
)
from config import config

logger = logging.getLogger("bot")


def create_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Xabar yuborish: guruh tanlash → matn yozish
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_action_message, pattern=r"^action:msg:")],
        states={
            WAITING_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message),
            ],
        },
        fallbacks=[CommandHandler("bekor", receive_message)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("coins", cmd_coins))
    app.add_handler(CommandHandler("setgroup", cmd_set_group))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(on_group_selected,  pattern=r"^group:"))
    app.add_handler(CallbackQueryHandler(on_action_check,    pattern=r"^action:check:"))
    app.add_handler(CallbackQueryHandler(on_back_start,      pattern=r"^back:start$"))
    app.add_handler(CallbackQueryHandler(on_task_confirm,    pattern=r"^task:(yes|no):"))

    logger.info("Telegram bot sozlandi")
    return app
