from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, time
from db import async_session
from models import TimeSlot
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("bot_errors.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

router = Router()

class CalendarFSM(StatesGroup):
    waiting_for_day_action = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()

def get_month_keyboard(year=None, month=None):
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    today = datetime.today()
    year = year or today.year
    month = month or today.month
    first_day = datetime(year, month, 1)
    first_weekday = (first_day.weekday() + 1) % 7  # Пн=0, Вс=6
    days_in_month = (first_day.replace(month=month % 12 + 1, day=1) - timedelta(days=1)).day

    kb = []
    kb.append([types.InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])

    row = []
    for _ in range((first_weekday - 0) % 7):
        row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))

    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        row.append(types.InlineKeyboardButton(
            text=str(day),
            callback_data=f"calendar_day_{date_str}"
        ))
        if len(row) == 7:
            kb.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))
        kb.append(row)
    prev_month = (month - 2) % 12 + 1
    prev_year = year if month > 1 else year - 1
    next_month = month % 12 + 1
    next_year = year if month < 12 else year + 1
    nav = [
        types.InlineKeyboardButton(text="<", callback_data=f"calendar_month_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton(text="Сегодня", callback_data="calendar_today"),
        types.InlineKeyboardButton(text=">", callback_data=f"calendar_month_{next_year}_{next_month}")
    ]
    kb.append(nav)
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "set_schedule")
async def open_calendar(callback: types.CallbackQuery, state: FSMContext):
    try:
        today = datetime.today()
        await callback.message.answer(
            f"Выберите день для настройки графика работы ({today.strftime('%B %Y')}):",
            reply_markup=get_month_keyboard(today.year, today.month)
        )
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка в open_calendar")
        await callback.message.answer("Произошла ошибка при открытии календаря. Сообщите администратору.")

@router.callback_query(lambda c: c.data.startswith("calendar_month_"))
async def calendar_switch_month(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, _, year, month = callback.data.split("_")
        await callback.message.edit_reply_markup(
            reply_markup=get_month_keyboard(int(year), int(month))
        )
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка при смене месяца в календаре")
        await callback.message.answer("Ошибка при смене месяца. Сообщите администратору.")

@router.callback_query(F.data == "calendar_today")
async def calendar_today(callback: types.CallbackQuery, state: FSMContext):
    try:
        today = datetime.today()
        await callback.message.edit_reply_markup(
            reply_markup=get_month_keyboard(today.year, today.month)
        )
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка при выборе сегодня в календаре")
        await callback.message.answer("Ошибка при возврате к текущему месяцу. Сообщите администратору.")

@router.callback_query(lambda c: c.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("calendar_day_"))
async def calendar_day_action(callback: types.CallbackQuery, state: FSMContext):
    try:
        date_str = callback.data.replace("calendar_day_", "")
        await state.update_data(selected_date=date_str)
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Установить график работы", callback_data="calendar_set_work")],
            [types.InlineKeyboardButton(text="Сделать нерабочим днем", callback_data="calendar_set_dayoff")],
            [types.InlineKeyboardButton(text="Вернуться в меню администратора", callback_data="back_to_admin")],
            [types.InlineKeyboardButton(text="Назад к календарю", callback_data="set_schedule")]
        ])
        await callback.message.answer(f"Выбран день: {date_str}\nЧто сделать с этим днем?", reply_markup=kb)
        await state.set_state(CalendarFSM.waiting_for_day_action)
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка при выборе дня календаря")
        await callback.message.answer("Ошибка при выборе дня. Сообщите администратору.")

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_from_calendar(callback: types.CallbackQuery, state: FSMContext):
    from handlers.admin import get_admin_keyboard
    await callback.message.answer("Админ-панель (выберите действие):", reply_markup=get_admin_keyboard())
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "calendar_set_dayoff")
async def calendar_set_dayoff(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        date_str = data.get("selected_date")
        if not date_str:
            await callback.message.answer("Ошибка: дата не выбрана.")
            await callback.answer()
            return
        start = datetime.strptime(date_str, "%Y-%m-%d")
        end = start + timedelta(days=1)
        async with async_session() as session:
            await session.execute(
                TimeSlot.__table__.delete().where(
                    TimeSlot.start_time >= start,
                    TimeSlot.start_time < end
                )
            )
            await session.commit()
        await callback.message.answer(f"День {date_str} сделан нерабочим (все слоты удалены).")
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в меню администратора", callback_data="back_to_admin")],
            [types.InlineKeyboardButton(text="Вернуться к календарю", callback_data="set_schedule")]
        ])
        await callback.message.answer(
            f"Календарь ({start.strftime('%B %Y')}):",
            reply_markup=kb
        )
        await state.clear()
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка при установке нерабочего дня")
        await callback.message.answer("Ошибка при установке нерабочего дня. Сообщите администратору.")

@router.callback_query(F.data == "calendar_set_work")
async def calendar_set_work(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.answer("Введите время начала рабочего дня в формате ЧЧ:ММ (например, 09:00):")
        await state.set_state(CalendarFSM.waiting_for_start_time)
        await callback.answer()
    except Exception as e:
        logging.exception("Ошибка при запуске FSM графика работы")
        await callback.message.answer("Ошибка при запуске настройки графика. Сообщите администратору.")

@router.message(CalendarFSM.waiting_for_start_time)
async def calendar_start_time(message: types.Message, state: FSMContext):
    try:
        text = message.text.strip()
        t = datetime.strptime(text, "%H:%M").time()
        await state.update_data(start_time=text)
        await message.answer("Введите время окончания рабочего дня в формате ЧЧ:ММ (например, 18:00):")
        await state.set_state(CalendarFSM.waiting_for_end_time)
    except Exception as e:
        logging.exception("Ошибка при вводе времени начала")
        await message.answer("Ошибка! Введите время в формате ЧЧ:ММ (например, 09:00):")

@router.message(CalendarFSM.waiting_for_end_time)
async def calendar_end_time(message: types.Message, state: FSMContext):
    try:
        text = message.text.strip()
        end_time = datetime.strptime(text, "%H:%M").time()
        data = await state.get_data()
        start_time = datetime.strptime(data['start_time'], "%H:%M").time()
        date_str = data['selected_date']
        date_base = datetime.strptime(date_str, "%Y-%m-%d")
        if end_time <= start_time:
            await message.answer("Время окончания должно быть больше начала.")
            return
        slots = []
        current = datetime.combine(date_base, start_time)
        end_dt = datetime.combine(date_base, end_time)
        while current < end_dt:
            slot_end = current + timedelta(hours=1)
            if slot_end > end_dt:
                slot_end = end_dt
            slots.append(TimeSlot(
                start_time=current,
                end_time=slot_end,
                is_free=True
            ))
            current = slot_end
        async with async_session() as session:
            await session.execute(
                TimeSlot.__table__.delete().where(
                    TimeSlot.start_time >= datetime.combine(date_base, time(0, 0)),
                    TimeSlot.start_time < datetime.combine(date_base + timedelta(days=1), time(0, 0))
                )
            )
            session.add_all(slots)
            await session.commit()
        await message.answer(
            f"График на {date_str} установлен: с {start_time.strftime('%H:%M')} до {end_time.strftime('%H:%M')} (создано {len(slots)} слотов по 1 часу)."
        )
        await message.answer(
            f"Календарь ({date_base.strftime('%B %Y')}):",
            reply_markup=get_month_keyboard(date_base.year, date_base.month)
        )
        await state.clear()
    except Exception as e:
        logging.exception("Ошибка при вводе времени окончания")
        await message.answer("Ошибка! Введите время в формате ЧЧ:ММ (например, 18:00):")

def register_calendar_handlers(dp):
    dp.include_router(router)
