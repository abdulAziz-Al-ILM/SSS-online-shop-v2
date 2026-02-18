import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_IDS, CARD_NUMBER
from database import *

# Loglarni yoqish
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- STATES ---
class AdminState(StatesGroup):
    photo = State()
    name = State()
    price = State()
    desc = State()
    stock = State()
    edit_stock_qty = State()
    shop_address = State()

class UserState(StatesGroup):
    input_qty = State()
    phone = State()
    location = State()
    check_photo = State()

# --- UTILS ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_kb(user_id):
    rows = [[KeyboardButton(text="🛍 Do'kon"), KeyboardButton(text="🛒 Savat")],
            [KeyboardButton(text="ℹ️ Biz haqimizda")]]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="⚙️ Sozlamalar")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(f"Salom, {m.from_user.full_name}!", reply_markup=main_kb(m.from_user.id))

# ================= ADMIN =================
@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_start(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await state.set_state(AdminState.photo)
    await m.answer("📸 Rasm yuboring (Rasm, Fayl farqi yo'q):", reply_markup=ReplyKeyboardRemove())

# --- UNIVERSAL MEDIA QABUL QILUVCHI ---
@dp.message(StateFilter(AdminState.photo))
async def get_media(m: types.Message, state: FSMContext):
    file_id = None
    if m.photo: file_id = m.photo[-1].file_id
    elif m.document: file_id = m.document.file_id
    
    if file_id:
        await state.update_data(file_id=file_id)
        await m.answer("✅ Rasm olindi! Nomini yozing:")
        await state.set_state(AdminState.name)
    else:
        await m.answer("⚠️ Iltimos, rasm yoki fayl yuboring. Matn emas.")

@dp.message(AdminState.name)
async def get_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("💰 Narxi (raqam):")
    await state.set_state(AdminState.price)

@dp.message(AdminState.price)
async def get_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Raqam yozing!")
    await state.update_data(price=int(m.text))
    await m.answer("📝 Tavsif:")
    await state.set_state(AdminState.desc)

@dp.message(AdminState.desc)
async def get_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("📦 Soni (raqam):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def get_stock(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Raqam yozing!")
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Mahsulot qo'shildi!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# --- SOZLAMALAR ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="Manzil", callback_data="set_addr")
    kb.button(text="Soni tahrirlash", callback_data="edit_st")
    kb.button(text="O'chirish", callback_data="del_prod")
    kb.adjust(1)
    await m.answer("Tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "set_addr")
async def ask_addr(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi manzilni yozing:")
    await state.set_state(AdminState.shop_address)
    await call.answer()

@dp.message(AdminState.shop_address)
async def save_addr(m: types.Message, state: FSMContext):
    await set_shop_info(m.text)
    await m.answer("✅ Manzil saqlandi!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "edit_st")
async def list_edit(call: types.CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']} ({p['stock']})", callback_data=f"est_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("est_"))
async def ask_new_st(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("Yangi sonini yozing:")
    await state.set_state(AdminState.edit_stock_qty)
    await call.answer()

@dp.message(AdminState.edit_stock_qty)
async def save_st(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Raqam yozing!")
    d = await state.get_data()
    await set_product_stock(d['pid'], int(m.text))
    await m.answer("✅ Yangilandi!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_prod")
async def list_del(call: types.CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"❌ {p['name']}", callback_data=f"del_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("O'chirish:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def del_item(call: types.CallbackQuery):
    await delete_product(call.data.split("_")[1])
    await call.answer("O'chirildi!")
    await call.message.delete()

# ================= USER =================
@dp.message(F.text == "ℹ️ Biz haqimizda")
async def about(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Manzil: {i['address']}")

@dp.message(F.text == "🛍 Do'kon")
async def shop(m: types.Message):
    prods = await get_all_products()
    if not prods: return await m.answer("Mahsulot yo'q.")
    kb = InlineKeyboardBuilder()
    for p in prods:
        if p.get('stock', 0) > 0:
            kb.button(text=f"{p['name']} - {p['price']}", callback_data=f"v_{p['_id']}")
    kb.adjust(1)
    await m.answer("Mahsulotlar:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("v_"))
async def view(call: types.CallbackQuery):
    p = await get_product(call.data.split("_")[1])
    if not p: return await call.answer("Topilmadi")
    cap = f"📱 {p['name']}\n💰 {p['price']} so'm\n📝 {p['description']}\n📦 Qolgan: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Savatga qo'shish", callback_data=f"add_{p['_id']}")
    kb.button(text="🔙 Orqaga", callback_data="back")
    try: await call.message.answer_photo(p['file_id'], caption=cap, reply_markup=kb.as_markup())
    except: await call.message.answer_document(p['file_id'], caption=cap, reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data == "back")
async def back(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer("🛍 Do'kon", reply_markup=main_kb(call.from_user.id))

@dp.callback_query(F.data.startswith("add_"))
async def ask_q(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("🔢 Nechta?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.input_qty)
    await call.answer()

@dp.message(UserState.input_qty)
async def save_cart(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Raqam yozing.")
    qty = int(m.text)
    d = await state.get_data()
    p = await get_product(d['pid'])
    
    if qty > p['stock']: return await m.answer(f"Bizda {p['stock']} ta bor xolos.")
    
    u_data = await state.get_data()
    cart = u_data.get("cart", {})
    pid = str(p['_id'])
    
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty}
    
    await state.update_data(cart=cart)
    await m.answer("✅ Savatga qo'shildi!", reply_markup=main_kb(m.from_user.id))
    await state.set_state(None)

@dp.message(F.text == "🛒 Savat")
async def show_cart(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart = d.get("cart", {})
    if not cart: return await m.answer("Savat bo'sh.")
    
    txt = "🛒 Savat:\n"
    tot = 0
    for i in cart.values():
        s = i['price'] * i['qty']
        tot += s
        txt += f"- {i['name']} x {i['qty']} = {s}\n"
    txt += f"\nJami: {tot} so'm"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Buyurtma berish", callback_data="checkout")
    kb.button(text="Tozalash", callback_data="clear")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "clear")
async def clr(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Tozalandi.")

@dp.callback_query(F.data == "checkout")
async def check(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("📞 Raqam yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Raqam", request_contact=True)]], resize_keyboard=True))
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def get_ph(m: types.Message, state: FSMContext):
    p = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=p)
    kb = InlineKeyboardBuilder()
    kb.button(text="O'zim olib ketaman", callback_data="pick")
    kb.button(text="Yetkazib berish (Taxi)", callback_data="taxi")
    kb.adjust(1)
    await m.answer("Turini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.in_({"pick", "taxi"}))
async def del_type(call: types.CallbackQuery, state: FSMContext):
    dtype = call.data
    await state.update_data(dtype=dtype)
    if dtype == "taxi":
        await call.message.answer("Lokatsiya yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Lokatsiya", request_location=True)]], resize_keyboard=True))
        await state.set_state(UserState.location)
    else:
        await finish(call.message, state, "Naqd")
    await call.answer()

@dp.message(UserState.location)
async def get_loc(m: types.Message, state: FSMContext):
    loc = f"geo:{m.location.latitude},{m.location.longitude}" if m.location else m.text
    await state.update_data(loc=loc)
    await m.answer(f"Karta: `{CARD_NUMBER}`\nChekni yuboring:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.check_photo)

@dp.message(UserState.check_photo)
async def get_check(m: types.Message, state: FSMContext):
    fid = None
    if m.photo: fid = m.photo[-1].file_id
    elif m.document: fid = m.document.file_id
    
    if fid: await finish(m, state, "Karta", fid)
    else: await m.answer("Rasm yoki fayl yuboring.")

async def finish(m, state, type, check_id=None):
    d = await state.get_data()
    cart = d.get("cart", {})
    
    txt = f"YANGI BUYURTMA!\n👤 {m.chat.full_name}\n📞 {d.get('phone')}\n"
    if 'loc' in d: txt += f"📍 Loc: {d['loc']}\n"
    
    tot = 0
    for pid, i in cart.items():
        s = i['price'] * i['qty']
        tot += s
        txt += f"{i['name']} x {i['qty']} = {s}\n"
        await decrease_stock(pid, i['qty'])
    txt += f"Jami: {tot} ({type})"

    for admin in ADMIN_IDS:
        try:
            if check_id: await bot.send_document(admin, check_id, caption=txt)
            else: await bot.send_message(admin, txt)
        except: pass
    
    await m.answer("✅ Qabul qilindi!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# --- ZOMBI HIMOYASI ---
@dp.message()
async def zombie(m: types.Message):
    if is_admin(m.from_user.id) and (m.photo or m.document):
        await m.answer("⚠️ Bot yangilandi. Iltimos, 'Mahsulot qo'shish'ni qayta bosing.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
