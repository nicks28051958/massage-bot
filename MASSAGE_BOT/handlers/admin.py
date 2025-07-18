from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from db import async_session
from models import MassageType

router = Router()

class AddMassageFSM(StatesGroup):
    name = State()
    duration = State()
    price = State()
    description = State()

class EditMassageFSM(StatesGroup):
    field = State()
    name = State()
    duration = State()
    price = State()
    description = State()
    image = State()

def get_admin_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Добавить массаж", callback_data="add_massage")],
        [types.InlineKeyboardButton(text="Редактировать массаж", callback_data="edit_massage")],
        [types.InlineKeyboardButton(text="Удалить массаж", callback_data="delete_massage")],
        [types.InlineKeyboardButton(text="Установить график работы", callback_data="set_schedule")],
        [types.InlineKeyboardButton(text="Выход в основное меню", callback_data="back_to_main")],
        [types.InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
    ])

@router.callback_query(F.data == "admin")
async def admin_panel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Админ-панель (выберите действие):", reply_markup=get_admin_keyboard())
    await callback.answer()
    await state.clear()

# --------------------- ДОБАВЛЕНИЕ МАССАЖА ---------------------
@router.callback_query(F.data == "add_massage")
async def add_massage(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название нового массажа:")
    await state.set_state(AddMassageFSM.name)
    await callback.answer()

@router.message(AddMassageFSM.name)
async def massage_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите длительность массажа в минутах:")
    await state.set_state(AddMassageFSM.duration)

@router.message(AddMassageFSM.duration)
async def massage_duration(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Пожалуйста, введите положительное число (минуты):")
        return
    await state.update_data(duration=int(message.text))
    await message.answer("Введите стоимость массажа (только число, в рублях):")
    await state.set_state(AddMassageFSM.price)

@router.message(AddMassageFSM.price)
async def massage_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную стоимость (только число, больше нуля):")
        return
    await state.update_data(price=price)
    await message.answer("Введите краткое описание массажа (или '-' если не требуется):")
    await state.set_state(AddMassageFSM.description)

@router.message(AddMassageFSM.description)
async def massage_description(message: types.Message, state: FSMContext):
    desc = message.text if message.text.strip() != '-' else ''
    data = await state.get_data()
    async with async_session() as session:
        new_massage = MassageType(
            name=data['name'],
            duration=data['duration'],
            price=data['price'],
            description=desc
        )
        session.add(new_massage)
        await session.commit()
    await message.answer(f"✅ Новый массаж добавлен:\n"
                        f"<b>{data['name']}</b>\n"
                        f"Длительность: {data['duration']} мин\n"
                        f"Цена: {data['price']} руб.\n"
                        f"Описание: {desc if desc else '—'}", parse_mode='HTML')
    await message.answer("Админ-панель (выберите действие):", reply_markup=get_admin_keyboard())
    await state.clear()

# --------------------- РЕДАКТИРОВАНИЕ МАССАЖА ---------------------
@router.callback_query(F.data == "edit_massage")
async def edit_massage_start(callback: types.CallbackQuery, state: FSMContext):
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
                types.InlineKeyboardButton(text=m.name, callback_data=f"edit_massage_{m.id}"),
                types.InlineKeyboardButton(text="Редактировать", callback_data=f"edit_massage_go_{m.id}")
            ] for m in massages
        ]
    )
    await callback.message.answer("Выберите массаж для редактирования:", reply_markup=kb)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("edit_massage_go_"))
async def edit_massage_choose(callback: types.CallbackQuery, state: FSMContext):
    massage_id = int(callback.data.replace("edit_massage_go_", ""))
    async with async_session() as session:
        massage = await session.get(MassageType, massage_id)
    await state.update_data(edit_id=massage_id)
    await state.update_data(edit_name=massage.name)
    await state.update_data(edit_duration=massage.duration)
    await state.update_data(edit_price=massage.price)
    await state.update_data(edit_description=massage.description or "")
    await state.update_data(edit_image=getattr(massage, "image", ""))

    text = f"<b>Название массажа:</b>\n{massage.name}"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Оставить", callback_data="edit_next_duration"),
                types.InlineKeyboardButton(text="Редактировать", callback_data="edit_field_name")
            ],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await state.set_state(EditMassageFSM.field)
    await callback.answer()

@router.callback_query(F.data == "edit_next_duration")
async def edit_massage_duration(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = f"<b>Длительность (мин):</b>\n{data['edit_duration']}"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Оставить", callback_data="edit_next_price"),
                types.InlineKeyboardButton(text="Редактировать", callback_data="edit_field_duration")
            ],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "edit_field_name")
async def ask_new_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое название массажа:")
    await state.set_state(EditMassageFSM.name)
    await callback.answer()

@router.message(EditMassageFSM.name)
async def save_new_name(message: types.Message, state: FSMContext):
    await state.update_data(edit_name=message.text)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Перейти к длительности", callback_data="edit_next_duration")],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await message.answer("Название обновлено.", reply_markup=kb)

@router.callback_query(F.data == "edit_field_duration")
async def ask_new_duration(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новую длительность (в минутах):")
    await state.set_state(EditMassageFSM.duration)
    await callback.answer()

@router.message(EditMassageFSM.duration)
async def save_new_duration(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Введите положительное число.")
        return
    await state.update_data(edit_duration=int(message.text))
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Перейти к цене", callback_data="edit_next_price")],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await message.answer("Длительность обновлена.", reply_markup=kb)

@router.callback_query(F.data == "edit_next_price")
async def edit_massage_price(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = f"<b>Цена (руб):</b>\n{data['edit_price']}"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Оставить", callback_data="edit_next_description"),
                types.InlineKeyboardButton(text="Редактировать", callback_data="edit_field_price")
            ],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "edit_field_price")
async def ask_new_price(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новую цену (в рублях):")
    await state.set_state(EditMassageFSM.price)
    await callback.answer()

@router.message(EditMassageFSM.price)
async def save_new_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную цену (больше 0).")
        return
    await state.update_data(edit_price=price)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Перейти к описанию", callback_data="edit_next_description")],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await message.answer("Цена обновлена.", reply_markup=kb)

@router.callback_query(F.data == "edit_next_description")
async def edit_massage_description(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = f"<b>Описание:</b>\n{data['edit_description'] or '-'}"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Оставить", callback_data="edit_next_image"),
                types.InlineKeyboardButton(text="Редактировать", callback_data="edit_field_description")
            ],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "edit_field_description")
async def ask_new_description(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое описание:")
    await state.set_state(EditMassageFSM.description)
    await callback.answer()

@router.message(EditMassageFSM.description)
async def save_new_description(message: types.Message, state: FSMContext):
    await state.update_data(edit_description=message.text)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Перейти к картинке", callback_data="edit_next_image")],
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await message.answer("Описание обновлено.", reply_markup=kb)

@router.callback_query(F.data == "edit_next_image")
async def edit_massage_image(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    img = data.get('edit_image', '')
    msg = "Медицинская картинка:" + ("\n(уже прикреплена)" if img else "\n(не прикреплена)")
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")],
            [types.InlineKeyboardButton(text="Прикрепить/заменить", callback_data="edit_field_image")]
        ]
    )
    await callback.message.answer(msg, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "edit_field_image")
async def ask_new_image(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Пришлите картинку медицинского назначения для этого массажа:")
    await state.set_state(EditMassageFSM.image)
    await callback.answer()

@router.message(EditMassageFSM.image)
async def save_new_image(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, пришлите изображение (фото).")
        return
    file_id = message.photo[-1].file_id
    await state.update_data(edit_image=file_id)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Сохранить изменения", callback_data="edit_save")]
        ]
    )
    await message.answer("Картинка обновлена. Готово к сохранению!", reply_markup=kb)

@router.callback_query(F.data == "edit_save")
async def save_all_edited_massage_callback(callback: types.CallbackQuery, state: FSMContext):
    await _do_save_edited_massage(callback.message, state)
    await callback.answer()

async def _do_save_edited_massage(message, state: FSMContext):
    data = await state.get_data()
    massage_id = data['edit_id']
    async with async_session() as session:
        massage = await session.get(MassageType, massage_id)
        massage.name = data['edit_name']
        massage.duration = data['edit_duration']
        massage.price = data['edit_price']
        massage.description = data['edit_description']
        if hasattr(massage, "image"):
            massage.image = data.get('edit_image', None)
        await session.commit()
    await message.answer("Изменения сохранены!", reply_markup=get_admin_keyboard())
    await state.clear()

# --------------------- ОСТАЛЬНЫЕ КНОПКИ АДМИНКИ ---------------------
@router.callback_query(F.data == "delete_massage")
async def delete_massage(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление массажа — в разработке.")
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='🟢 Записаться на массаж', callback_data='book')],
        [types.InlineKeyboardButton(text='ℹ️ Информация о массаже', callback_data='info')],
        [types.InlineKeyboardButton(text='❌ Отменить запись', callback_data='cancel')],
        [types.InlineKeyboardButton(text='🕒 Перенести запись', callback_data='reschedule')],
        [types.InlineKeyboardButton(text='🔑 Зайти администратором', callback_data='admin')],
    ])
    await callback.message.answer('Выберите действие:', reply_markup=kb)
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Вы уже в админ-панели.")
    await callback.answer()

def register_admin_handlers(dp):
    dp.include_router(router)
