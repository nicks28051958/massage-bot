from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from db import async_session
from models import MassageType, TimeSlot, Booking
from datetime import datetime, timedelta

router = Router()

class BookingFSM(StatesGroup):
    massage_id = State()
    date = State()
    slot = State()

def get_main_menu():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='🟢 Записаться на массаж', callback_data='book')],
        [types.InlineKeyboardButton(text='ℹ️ Информация о массаже', callback_data='info')],
        [types.InlineKeyboardButton(text='❌ Отменить запись', callback_data='cancel')],
        [types.InlineKeyboardButton(text='🕒 Перенести запись', callback_data='reschedule')],
        [types.InlineKeyboardButton(text='🔑 Зайти администратором', callback_data='admin')],
    ])

@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        'Добро пожаловать в массажный салон!\nВыберите действие:',
        reply_markup=get_main_menu()
    )
    await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        'Выберите действие:',
        reply_markup=get_main_menu()
    )
    await callback.answer()
    await state.clear()

# --- Запись на массаж ---
@router.callback_query(F.data == "book")
async def book_start(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(MassageType))
        massages = result.scalars().all()
    if not massages:
        await callback.message.answer("Нет доступных видов массажа.")
        await callback.answer()
        return

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text=m.name, callback_data=f"book_massage_{m.id}"),
                types.InlineKeyboardButton(text="Записаться", callback_data=f"book_choose_{m.id}")
            ] for m in massages
        ]
    )
    await callback.message.answer("Выберите вид массажа:", reply_markup=kb)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("book_choose_"))
async def choose_massage(callback: types.CallbackQuery, state: FSMContext):
    massage_id = int(callback.data.replace("book_choose_", ""))
    async with async_session() as session:
        massage = await session.get(MassageType, massage_id)
    if not massage:
        await callback.message.answer("Массаж не найден.")
        await callback.answer()
        return
    await state.update_data(massage_id=massage_id)
    await show_calendar(callback.message, state)
    await callback.answer()

async def show_calendar(message, state):
    today = datetime.today()
    year = today.year
    month = today.month

    def get_calendar_keyboard(year, month):
        import calendar
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        cal = calendar.Calendar(firstweekday=0)
        kb = [ [types.InlineKeyboardButton(text=wd, callback_data="ignore") for wd in week_days] ]

        month_days = cal.monthdayscalendar(year, month)
        for week in month_days:
            row = []
            for d in week:
                if d == 0 or datetime(year, month, d) < today.replace(hour=0, minute=0, second=0, microsecond=0):
                    row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))
                else:
                    date_str = f"{year}-{month:02d}-{d:02d}"
                    row.append(types.InlineKeyboardButton(text=str(d), callback_data=f"choose_date_{date_str}"))
            kb.append(row)
        nav = [
            types.InlineKeyboardButton(text="<", callback_data=f"calendar_prev_{year}_{month}"),
            types.InlineKeyboardButton(text="Сегодня", callback_data="calendar_today"),
            types.InlineKeyboardButton(text=">", callback_data=f"calendar_next_{year}_{month}")
        ]
        kb.append(nav)
        return types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.answer(
        f"Выберите дату для записи:",
        reply_markup=get_calendar_keyboard(year, month)
    )
    await state.set_state(BookingFSM.date)

@router.callback_query(lambda c: c.data.startswith("calendar_prev_"))
async def calendar_prev_month(callback: types.CallbackQuery, state: FSMContext):
    _, _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month)
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    await show_calendar(callback.message, state)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("calendar_next_"))
async def calendar_next_month(callback: types.CallbackQuery, state: FSMContext):
    _, _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month)
    month += 1
    if month > 12:
        month = 1
        year += 1
    await show_calendar(callback.message, state)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("choose_date_"))
async def choose_date(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("choose_date_", "")
    date = datetime.strptime(date_str, "%Y-%m-%d")
    await state.update_data(date=date_str)
    async with async_session() as session:
        result = await session.execute(
            select(TimeSlot).where(
                TimeSlot.start_time >= date,
                TimeSlot.start_time < date + timedelta(days=1),
                TimeSlot.is_free == True
            )
        )
        slots = result.scalars().all()
    if not slots:
        await callback.message.answer("На эту дату нет свободных слотов. Выберите другую дату.")
        await callback.answer()
        return
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}",
                callback_data=f"choose_slot_{s.id}"
            )] for s in slots
        ]
    )
    await callback.message.answer(f"Свободные слоты на {date.strftime('%d.%m.%Y')}:", reply_markup=kb)
    await state.set_state(BookingFSM.slot)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("choose_slot_"))
async def choose_slot(callback: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.replace("choose_slot_", ""))
    data = await state.get_data()
    massage_id = data.get("massage_id")
    date_str = data.get("date")
    async with async_session() as session:
        slot = await session.get(TimeSlot, slot_id)
        massage = await session.get(MassageType, massage_id)
        if not slot or not slot.is_free or not massage:
            await callback.message.answer("Слот уже занят или не найден.")
            await callback.answer()
            return
        booking = Booking(
            user_id=callback.from_user.id,
            user_name=callback.from_user.full_name,
            massage_type_id=massage_id,
            slot_id=slot_id
        )
        slot.is_free = False
        session.add(booking)
        await session.commit()
    await callback.message.answer(
        f"✅ Вы записаны на <b>{massage.name}</b> "
        f"{slot.start_time.strftime('%d.%m.%Y')} "
        f"в {slot.start_time.strftime('%H:%M')}! "
        f"До встречи!", parse_mode="HTML"
    )
    await callback.message.answer(
        'Возврат в главное меню:',
        reply_markup=get_main_menu()
    )
    await state.clear()
    await callback.answer()

# --- Информация о массаже через инлайн-кнопки ---

@router.callback_query(F.data == "info")
async def info_massages_menu(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(MassageType))
        massages = result.scalars().all()
    if not massages:
        await callback.message.answer("Виды массажа не найдены.")
        await callback.answer()
        return
    # Список кнопок с массажами
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=m.name, callback_data=f"massage_info_{m.id}")]
            for m in massages
        ] + [[types.InlineKeyboardButton(text="Назад", callback_data="back_to_main")]]
    )
    await callback.message.answer(
        "Выберите вид массажа для подробной информации:",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("massage_info_"))
async def show_massage_description(callback: types.CallbackQuery, state: FSMContext):
    massage_id = int(callback.data.replace("massage_info_", ""))
    async with async_session() as session:
        massage = await session.get(MassageType, massage_id)
    if not massage:
        await callback.message.answer("Информация не найдена.")
        await callback.answer()
        return
    text = (
        f"<b>{massage.name}</b> — {massage.duration} мин, {massage.price} руб.\n\n"
        f"{massage.description or 'Нет описания.'}"
    )
    # Кнопка "Назад к списку массажей"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Назад", callback_data="info")]
        ]
    )
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb)
    await callback.answer()

# --- Отменить запись ---
@router.callback_query(F.data == "cancel")
async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(Booking.user_id == callback.from_user.id)
        )
        booking = result.scalars().first()
        if not booking:
            await callback.message.answer("У вас нет активных записей.")
            await callback.answer()
            return
        massage = await session.get(MassageType, booking.massage_type_id)
        slot = await session.get(TimeSlot, booking.slot_id)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Удалить запись", callback_data=f"delete_booking_{booking.id}")],
            [types.InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer(
        f"Ваша запись:\n"
        f"<b>{massage.name}</b>\n"
        f"{slot.start_time.strftime('%d.%m.%Y %H:%M')} - {slot.end_time.strftime('%H:%M')}\n\n"
        f"Вы можете отменить запись:",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_booking_"))
async def delete_booking(callback: types.CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.replace("delete_booking_", ""))
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.message.answer("Запись не найдена.")
            await callback.answer()
            return
        slot = await session.get(TimeSlot, booking.slot_id)
        if slot:
            slot.is_free = True
        await session.delete(booking)
        await session.commit()
    await callback.message.answer(
        "Ваша запись успешно отменена.",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# --- Перенести запись ---
@router.callback_query(F.data == "reschedule")
async def reschedule_booking(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(Booking.user_id == callback.from_user.id)
        )
        booking = result.scalars().first()
        if not booking:
            await callback.message.answer("У вас нет активных записей.")
            await callback.answer()
            return
        massage = await session.get(MassageType, booking.massage_type_id)
        slot = await session.get(TimeSlot, booking.slot_id)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Выбрать новую дату и время", callback_data=f"reschedule_booking_{booking.id}")],
            [types.InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer(
        f"Ваша запись:\n"
        f"<b>{massage.name}</b>\n"
        f"{slot.start_time.strftime('%d.%m.%Y %H:%M')} - {slot.end_time.strftime('%H:%M')}\n\n"
        f"Вы можете выбрать новое время:",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("reschedule_booking_"))
async def reschedule_booking_choose(callback: types.CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.replace("reschedule_booking_", ""))
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.message.answer("Запись не найдена.")
            await callback.answer()
            return
        await state.update_data(massage_id=booking.massage_type_id)
        slot = await session.get(TimeSlot, booking.slot_id)
        if slot:
            slot.is_free = True
        await session.delete(booking)
        await session.commit()
    await callback.message.answer("Выберите новую дату для записи:")
    await show_calendar(callback.message, state)
    await callback.answer()

def register_client_handlers(dp):
    dp.include_router(router)
