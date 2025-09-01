import os
import asyncio
from aiohttp import web

from firebase_store import (
    save_file_id,
    get_file_id_by_key,
    has_seen_prompt,
    mark_prompt_seen,
    get_all_file_keys,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", "8443"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g. https://yourapp.up.railway.app
WEBHOOK_PATH = f"/{BOT_TOKEN}"  # webhook path

DELETE_AFTER = 7200
PAGE_SIZE = 10

CHANNEL_ID = -1002888196431
OWNER_IDS = {7529896616,1280031820,8430053584}
ADMIN_USERNAME = "KAAL_IG"

CHANNEL_INVITE_LINK = "https://t.me/+kFX8hQ1Lzls5ZWE1"

WELCOME_STICKER_ID = "CAACAgIAAxkBAAPJaHiL1vLtBmTcit_SlOCHqMKKTHUAAh0AAztxHyKpgppgMFfRGTYE"
WELCOME_PHOTO_URL = "https://img.freepik.com/free-vector/chatbot-conversation-vectorart_78370-4107.jpg"


async def prompt_to_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_INVITE_LINK)],
            [
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("📬 Contact", url=f"https://t.me/{ADMIN_USERNAME}"),
                InlineKeyboardButton("📋 Menu", callback_data="menu"),
            ],
        ]
    )

    await update.message.reply_text(
        "🚫 *Access Denied*\n\n"
        "You must *send a join request* to our backup channel to continue using this bot.\n\n"
        "Click the button below to join and then use the bot freely 👇",
        reply_markup=join_buttons,
        parse_mode="Markdown",
    )


async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if update.message:
        reply_func = update.message.reply_text
        sticker_func = update.message.reply_sticker
    elif update.callback_query:
        reply_func = update.callback_query.message.reply_text
        sticker_func = update.callback_query.message.reply_sticker
    else:
        return

    await sticker_func(WELCOME_STICKER_ID)

    button_rows = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("📬 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
        [
            InlineKeyboardButton("🚀 Start", callback_data="start_fake"),
            InlineKeyboardButton("📖 Help", callback_data="help"),
        ],
    ]

    if user_id in OWNER_IDS:
        button_rows.append([InlineKeyboardButton("🧹 Clear Chat", callback_data="clear_chat")])

    menu_markup = InlineKeyboardMarkup(button_rows)

    welcome_text = (
        f"👋 Hello, *{user.first_name}*!\n\n"
        "Welcome to the bot. Use the buttons below to get started.\nAnd Join Channel First Then use BOT."
    )

    await reply_func(welcome_text, reply_markup=menu_markup, parse_mode=ParseMode.MARKDOWN)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await welcome_user(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not has_seen_prompt(user_id) and user_id not in OWNER_IDS:
        await prompt_to_join(update, context)
        mark_prompt_seen(user_id)
        return

    args = context.args
    if not args:
        await welcome_user(update, context)
        return

    key = args[0]
    file_id = get_file_id_by_key(key)
    if not file_id:
        await update.message.reply_text("❌ File not found for this key.")
        return

    sent_msg = await update.message.reply_video(video=file_id)
    info_msg = await update.message.reply_text("⏳ This video will auto-delete in 2 hours.\n (FOR BUYING DIRECT VIDEO GROUPS @senpai_hwajin✅)")

    async def delete_later():
        await asyncio.sleep(DELETE_AFTER)
        try:
            await context.bot.delete_message(chat_id=sent_msg.chat.id, message_id=sent_msg.message_id)
            await context.bot.delete_message(chat_id=info_msg.chat.id, message_id=info_msg.message_id)
            await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
        except Exception as e:
            print(f"[Delete Error] {e}")

    asyncio.create_task(delete_later())


async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user_id = update.effective_user.id

    if user_id not in OWNER_IDS and not has_seen_prompt(user_id):
        await prompt_to_join(update, context)
        mark_prompt_seen(user_id)
        return

    if user_id not in OWNER_IDS:
        await update.message.reply_text("❌ Sorry, only the bot admin can save files.")
        return

    file_id = None
    media_type = None

    if message.video:
        file_id = message.video.file_id
        media_type = "Video"
    elif message.document:
        file_id = message.document.file_id
        media_type = "Document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        media_type = "Photo"
    else:
        await update.message.reply_text("❌ Unsupported media type.")
        return

    key = save_file_id(file_id)
    reply_link = "https://t.me/heaven_userZ_bot?start=" + key

    reply_text = f"✅ {media_type} saved!\n\nUse this link to retrieve it:\n{reply_link}"

    if user_id in OWNER_IDS:
        markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🧹 Clear Chat", callback_data="clear_chat")]
            ]
        )
        await update.message.reply_text(reply_text, reply_markup=markup)
    else:
        await update.message.reply_text(reply_text)

    print(f"[Saved] {key}:{file_id}")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private":
        await update.message.reply_text("⚠️ /clear only works in private chats.")
        return

    tasks = []
    for msg_id in range(update.message.message_id - 1, update.message.message_id - 50, -1):
        tasks.append(context.bot.delete_message(chat_id=chat.id, message_id=msg_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    deleted = sum(1 for r in results if not isinstance(r, Exception))
    await update.message.reply_text(f"✅ Cleared {deleted} messages.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 *Bot Commands Guide*\n\n"
        "🔹 `/start <key>` — Retrieve saved media using a key.\n"
        "🔹 Forward a photo, video, or document to save it.\n"
        "🔹 `/clear` — Clear recent messages from this chat.\n"
        "🔹 `/contact` — Get help or report issues.\n\n"
        "📝 This bot temporarily stores media and gives you private links to access them.\n"
        "Files auto-delete after a short time. Use wisely!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📬 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")]]
    )

    await update.message.reply_text(
        "👨‍💻 Need help? Contact the admin for support.", reply_markup=contact_button
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "clear_chat":
        if user_id in OWNER_IDS:
            chat_id = query.message.chat.id
            msg_id = query.message.message_id

            tasks = []
            for mid in range(msg_id - 1, msg_id - 50, -1):
                tasks.append(context.bot.delete_message(chat_id=chat_id, message_id=mid))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            deleted = sum(1 for r in results if not isinstance(r, Exception))
            await query.message.reply_text(f"✅ Cleared {deleted} recent messages.")
        else:
            await query.message.reply_text("❌ You are not allowed to use this button.")

    elif query.data == "help":
        help_text = (
            "🤖 *Bot Help*\n\n"
            "🔹 Forward a photo, video, or document to save it.\n"
            "🔹 Get a private link to retrieve it using `/start <key>`\n"
            "🔹 Files auto-delete after a short time.\n"
            "🔹 Use `/clear` to delete recent messages.\n"
            "🔹 Use `/contact` to message the admin.\n"
        )
        await query.message.reply_text(help_text, parse_mode="Markdown")

    elif query.data == "menu":
        if user_id not in OWNER_IDS and not has_seen_prompt(user_id):
            await prompt_to_join(update, context)
            mark_prompt_seen(user_id)
            return
        await welcome_user(update, context)

    elif query.data == "start_fake":
        await welcome_user(update, context)

    elif query.data.startswith("allvid_page_"):
        page = int(query.data.split("_")[-1])
        keys = get_all_file_keys()
        await send_allvid_page(query, context, keys, page=page)


async def allvid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in OWNER_IDS:
        await update.message.reply_text("❌ Only the bot admin can view all saved videos.")
        return

    keys = get_all_file_keys()
    if not keys:
        await update.message.reply_text("📂 No videos have been saved yet.")
        return

    await send_allvid_page(update, context, keys, page=0)


async def send_allvid_page(update_or_query, context, keys, page=0):
    total_pages = (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))

    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    page_keys = keys[start_index:end_index]

    text_lines = [f"🎞 *Saved Videos* (Page {page + 1}/{total_pages})\n"]

    for key in page_keys:
        text_lines.append(f"🔗 [`/start {key}`](https://t.me/heaven_userZ_bot?start={key})")

    text = "\n".join(text_lines)

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⏮ Prev", callback_data=f"allvid_page_{page - 1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("⏭ Next", callback_data=f"allvid_page_{page + 1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True
        )
    else:
        await update_or_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True
        )


# Webhook handler to receive Telegram updates
async def handle_webhook(request):
    data = await request.json()
    bot = request.app['app_bot'].bot  # get the Bot instance from Application
    update = Update.de_json(data, bot)
    await request.app['app_bot'].process_update(update)
    return web.Response(text="OK")


async def on_startup(app: web.Application):
    print("Setting webhook...")
    await app['bot'].set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    print(f"Webhook set to {WEBHOOK_URL}{WEBHOOK_PATH}")


async def on_shutdown(app: web.Application):
    print("Deleting webhook...")
    await app['bot'].delete_webhook()

# Add a simple GET route to respond to health checks
async def health_check(request):
    return web.Response(text="Bot is alive")

async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("menu", menu_command))
    app_bot.add_handler(CommandHandler("clear", clear_chat))
    app_bot.add_handler(CommandHandler("allvid", allvid_command))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(CommandHandler("contact", contact_admin))
    app_bot.add_handler(CallbackQueryHandler(handle_callback))

    media_filter = filters.FORWARDED & (filters.VIDEO | filters.PHOTO | filters.Document.ALL)
    app_bot.add_handler(MessageHandler(media_filter, handle_forwarded))

    await app_bot.initialize()

    # Do NOT call start() here — webhook mode doesn't need polling
    # await app_bot.start()  <-- REMOVE THIS

    aio_app = web.Application()
    aio_app['bot'] = app_bot.bot
    aio_app['app_bot'] = app_bot  # for shutdown

    aio_app.router.add_post(WEBHOOK_PATH, handle_webhook)
    aio_app.on_startup.append(on_startup)
    aio_app.on_shutdown.append(on_shutdown)
    aio_app.router.add_get("/ping", health_check)

    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"✅ Webhook server started on port {PORT}")
    print("🌐 Listening on", f"{WEBHOOK_URL}{WEBHOOK_PATH}")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app_bot.shutdown()
        await app_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
