from aiogram.fsm.state import State, StatesGroup


class AddServerStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_description = State()
    waiting_for_website_url = State()
    waiting_for_ports = State()
    waiting_for_ssl_domain = State()


class EditServerStates(StatesGroup):
    waiting_for_value = State()
