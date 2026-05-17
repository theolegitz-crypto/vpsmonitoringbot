from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


STATUS_BUTTON = "📊 Статус"
SERVERS_BUTTON = "🖥 Серверы"
ALERTS_BUTTON = "🚨 Алерты"
HELP_BUTTON = "❓ Помощь"
EXAMPLES_BUTTON = "📚 Примеры"


main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=STATUS_BUTTON), KeyboardButton(text=SERVERS_BUTTON)],
        [KeyboardButton(text=ALERTS_BUTTON), KeyboardButton(text=HELP_BUTTON)],
        [KeyboardButton(text=EXAMPLES_BUTTON)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери кнопку или введи, например: /server vps1",
)
