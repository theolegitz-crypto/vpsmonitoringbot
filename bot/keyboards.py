from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from backend.app.models.enums import ServerStatus


STATUS_BUTTON = "📊 Статус"
SERVERS_BUTTON = "🖥 Серверы"
ALERTS_BUTTON = "🚨 Алерты"
HELP_BUTTON = "❓ Помощь"
EXAMPLES_BUTTON = "📚 Примеры"
ADD_SERVER_BUTTON = "➕ Добавить сервер"
CANCEL_BUTTON = "❌ Отмена"

PICKER_PAGE_SIZE = 8


main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=STATUS_BUTTON), KeyboardButton(text=SERVERS_BUTTON)],
        [KeyboardButton(text=ALERTS_BUTTON), KeyboardButton(text=ADD_SERVER_BUTTON)],
        [KeyboardButton(text=HELP_BUTTON), KeyboardButton(text=EXAMPLES_BUTTON)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери кнопку или введи команду",
)


main_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=STATUS_BUTTON, callback_data="action:status"),
            InlineKeyboardButton(text=SERVERS_BUTTON, callback_data="action:servers"),
        ],
        [
            InlineKeyboardButton(text=ALERTS_BUTTON, callback_data="action:alerts"),
            InlineKeyboardButton(text=ADD_SERVER_BUTTON, callback_data="action:addserver"),
        ],
        [
            InlineKeyboardButton(text=HELP_BUTTON, callback_data="action:help"),
            InlineKeyboardButton(text=EXAMPLES_BUTTON, callback_data="action:examples"),
        ],
    ]
)


cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL_BUTTON)]],
    resize_keyboard=True,
    input_field_placeholder="Заполни шаг или нажми Отмена",
)


cancel_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=CANCEL_BUTTON, callback_data="action:cancel")]]
)


def _status_icon(status: ServerStatus) -> str:
    if status == ServerStatus.ONLINE:
        return "🟢"
    if status == ServerStatus.DEGRADED:
        return "🟡"
    if status == ServerStatus.OFFLINE:
        return "🔴"
    return "⚪"


def server_picker_keyboard(servers: list, action: str, page: int = 0) -> InlineKeyboardMarkup:
    total_pages = max(1, ceil(len(servers) / PICKER_PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PICKER_PAGE_SIZE
    current_slice = servers[start : start + PICKER_PAGE_SIZE]

    rows: list[list[InlineKeyboardButton]] = []
    for server in current_slice:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{_status_icon(server.status)} {server.name}",
                    callback_data=f"server:{action}:{server.id}",
                )
            ]
        )

    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"picker:{action}:{page - 1}"))
    if total_pages > 1:
        navigation.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"picker:{action}:{page + 1}"))
    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(text=STATUS_BUTTON, callback_data="action:status"),
            InlineKeyboardButton(text=ALERTS_BUTTON, callback_data="action:alerts"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def server_actions_keyboard(server_id: int, is_muted: bool) -> InlineKeyboardMarkup:
    mute_button = (
        InlineKeyboardButton(text="🔔 Включить уведомления", callback_data=f"server:unmute:{server_id}")
        if is_muted
        else InlineKeyboardButton(text="🔕 Приглушить", callback_data=f"server:muteprompt:{server_id}")
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📡 Ping", callback_data=f"server:ping:{server_id}"),
                InlineKeyboardButton(text="🕓 История", callback_data=f"server:history:{server_id}"),
            ],
            [
                InlineKeyboardButton(text="🔌 Порты", callback_data=f"server:ports:{server_id}"),
                InlineKeyboardButton(text="⚡ Speed", callback_data=f"server:speed:{server_id}"),
            ],
            [
                InlineKeyboardButton(text="🧠 Метрики", callback_data=f"server:metrics:{server_id}"),
                InlineKeyboardButton(text="🐳 Контейнеры", callback_data=f"server:containers:{server_id}"),
            ],
            [
                InlineKeyboardButton(text="📶 Последний speed", callback_data=f"server:speedlast:{server_id}"),
                InlineKeyboardButton(text="📈 История speed", callback_data=f"server:speedhistory:{server_id}"),
            ],
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"server:editprompt:{server_id}"),
                mute_button,
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"server:deleteprompt:{server_id}"),
            ],
            [
                InlineKeyboardButton(text="🖥 К списку серверов", callback_data="picker:detail:0"),
            ],
        ]
    )


def server_edit_field_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Имя", callback_data=f"editfield:{server_id}:name"),
                InlineKeyboardButton(text="Адрес", callback_data=f"editfield:{server_id}:address"),
            ],
            [
                InlineKeyboardButton(text="Описание", callback_data=f"editfield:{server_id}:description"),
                InlineKeyboardButton(text="Интервал", callback_data=f"editfield:{server_id}:check_interval_seconds"),
            ],
            [
                InlineKeyboardButton(
                    text="Порог алерта",
                    callback_data=f"editfield:{server_id}:consecutive_alert_threshold",
                ),
                InlineKeyboardButton(
                    text="Latency warn",
                    callback_data=f"editfield:{server_id}:latency_warning_ms",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Latency crit",
                    callback_data=f"editfield:{server_id}:latency_critical_ms",
                ),
                InlineKeyboardButton(
                    text="Loss warn",
                    callback_data=f"editfield:{server_id}:packet_loss_warning",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Loss crit",
                    callback_data=f"editfield:{server_id}:packet_loss_critical",
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к серверу", callback_data=f"server:detail:{server_id}"),
            ],
        ]
    )


def server_delete_confirm_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"deleteconfirm:{server_id}"),
                InlineKeyboardButton(text="Отмена", callback_data=f"server:detail:{server_id}"),
            ]
        ]
    )


def mute_duration_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="30m", callback_data=f"mute:{server_id}:30m"),
                InlineKeyboardButton(text="2h", callback_data=f"mute:{server_id}:2h"),
                InlineKeyboardButton(text="12h", callback_data=f"mute:{server_id}:12h"),
            ],
            [
                InlineKeyboardButton(text="1d", callback_data=f"mute:{server_id}:1d"),
                InlineKeyboardButton(text="1w", callback_data=f"mute:{server_id}:1w"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к серверу", callback_data=f"server:detail:{server_id}"),
            ],
        ]
    )
