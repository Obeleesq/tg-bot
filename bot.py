from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

import os

BOT_TOKEN = os.getenv("8478167193:AAGBizO4W-DYA4UjXkjmCbYtxFzEJGPSrJA")

ADMIN_ID = 1356461035

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================== ХРАНИЛИЩА ==================
active_orders = {}      # user_id -> order_id
paid_requests = {}      # антиспам
support_wait = set()    # ожидание сообщения в поддержку

# ================== ТОВАРЫ ==================
PRODUCTS = {
    "p1": ("Товар 1", 219, False),
    "p2": ("Товар 2", 219, True),
    "p3": ("Товар 3", 399, False),
    "p4": ("Товар 4", 399, True),
    "p5": ("Товар 5", 699, False),
}

# ================== КЛАВИАТУРЫ ==================
def products_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for key, (name, price, discount) in PRODUCTS.items():
        text = f"{name} — {price} ₽"
        if discount:
            text = f"🔥 {text} (скидка)"
        kb.add(InlineKeyboardButton(text=text, callback_data=f"buy:{key}"))
    return kb


def admin_keyboard(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"ok:{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"no:{user_id}")
    )
    return kb


def after_paid_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support"))
    kb.add(InlineKeyboardButton("⬅️ Назад к товарам", callback_data="back"))
    return kb

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "👋 *Добро пожаловать!*\n\n"
        "Выберите товар для покупки 👇",
        parse_mode="Markdown",
        reply_markup=products_keyboard()
    )

# ================== ПОДДЕРЖКА ==================
@dp.callback_query_handler(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    support_wait.add(callback.from_user.id)
    await callback.message.answer(
        "💬 Напишите сообщение для поддержки.\n"
        "Мы передадим его администратору."
    )
    await callback.answer()


@dp.message_handler(lambda m: m.from_user.id in support_wait)
async def support_message(message: types.Message):
    support_wait.remove(message.from_user.id)

    await bot.send_message(
        ADMIN_ID,
        f"💬 *Сообщение в поддержку*\n\n"
        f"👤 @{message.from_user.username or 'без username'}\n"
        f"🆔 {message.from_user.id}\n\n"
        f"{message.text}",
        parse_mode="Markdown"
    )

    await message.answer("✅ Сообщение отправлено. Мы ответим вам.")

# ================== ВЫБОР ТОВАРА ==================
@dp.callback_query_handler(lambda c: c.data.startswith("buy:"))
async def buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id in active_orders:
        await callback.answer(
            "❗ У вас уже есть активная заявка. Дождитесь обработки.",
            show_alert=True
        )
        return

    pid = callback.data.split(":")[1]
    name, price, discount = PRODUCTS[pid]

    order_id = f"ORD-{user_id}-{int(time.time())}"
    active_orders[user_id] = order_id

    discount_text = "🔥 *Товар со скидкой!*\n\n" if discount else ""

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid:{pid}"))
    kb.add(InlineKeyboardButton("⬅️ Назад к товарам", callback_data="back"))

    await callback.message.edit_text(
        discount_text +
        "💳 *Реквизиты для оплаты*\n\n"
        f"📦 Товар: *{name}*\n"
        f"💰 Сумма: *{price} ₽*\n\n"
        "🏦 Ozon Bank\n"
        "💳 `2204 2402 8728 6001`\n"
        "👤 Матвей А.\n\n"
        "✍️ *Комментарий к переводу:*\n"
        f"`{order_id}`\n\n"
        "После оплаты нажмите кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=kb
    )

    await callback.answer()

# ================== Я ОПЛАТИЛ ==================
@dp.callback_query_handler(lambda c: c.data.startswith("paid:"))
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    now = time.time()

    if user_id in paid_requests and now - paid_requests[user_id] < 60:
        await callback.answer("⏳ Запрос уже отправлен", show_alert=True)
        return

    paid_requests[user_id] = now

    pid = callback.data.split(":")[1]
    name, price, _ = PRODUCTS[pid]
    order_id = active_orders[user_id]

    await callback.message.edit_reply_markup()

    await callback.message.answer(
        "⏳ *Спасибо!*\n\n"
        "Ваш запрос принят.\n"
        "⏰ Проверка обычно занимает до 15 минут.",
        parse_mode="Markdown",
        reply_markup=after_paid_keyboard()
    )

    await bot.send_message(
        ADMIN_ID,
        f"💰 *Новая заявка*\n\n"
        f"🆔 {order_id}\n"
        f"👤 @{callback.from_user.username or 'без username'}\n"
        f"📦 {name}\n"
        f"💰 {price} ₽",
        parse_mode="Markdown",
        reply_markup=admin_keyboard(user_id)
    )

    await callback.answer()

# ================== АДМИН ==================
@dp.callback_query_handler(lambda c: c.data.startswith("ok:"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await bot.send_message(user_id, "✅ Оплата подтверждена. Спасибо за покупку!")
    active_orders.pop(user_id, None)
    await callback.message.edit_reply_markup()
    await callback.answer("Подтверждено")


@dp.callback_query_handler(lambda c: c.data.startswith("no:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await bot.send_message(
        user_id,
        "❌ Оплата не найдена.\nПожалуйста, свяжитесь с поддержкой."
    )
    active_orders.pop(user_id, None)
    await callback.message.edit_reply_markup()
    await callback.answer("Отклонено")

# ================== НАЗАД ==================
@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📦 *Каталог товаров*\n\nВыберите товар 👇",
        parse_mode="Markdown",
        reply_markup=products_keyboard()
    )
    await callback.answer()

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    executor.start_polling(dp)

