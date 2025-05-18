from aiogram.fsm.state import State, StatesGroup

class RouteStates(StatesGroup):
    # Состояния для создания маршрута
    waiting_for_route_name = State()
    waiting_for_route_description = State()
    waiting_for_route_photo = State()
    waiting_for_route_points = State()
    waiting_for_point_order = State()
    waiting_for_point_action = State()

    # Состояния для создания точки
    waiting_for_point_name = State()
    waiting_for_point_description = State()
    waiting_for_point_location = State()
    waiting_for_point_text = State()
    waiting_for_point_photo = State()
    waiting_for_point_audio = State()
    waiting_for_point_video = State()

    # Состояния для редактирования точки
    editing_point = State()
    editing_point_name = State()
    editing_point_description = State()
    editing_point_location = State()
    editing_point_text = State()
    editing_point_photo = State()
    editing_point_audio = State()
    editing_point_video = State()

    # Состояния для редактирования маршрута
    editing_route = State() 