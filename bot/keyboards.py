from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/status"), KeyboardButton(text="/servers")],
        [KeyboardButton(text="/alerts"), KeyboardButton(text="/help")],
        [KeyboardButton(text="Examples")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Use buttons or type /server vps1",
)

