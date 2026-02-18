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
        rows.append([KeyboardButton(text="📦 Buyurtmalar"), KeyboardButton(text="➕ Mahsulot qo'shish")])
        rows.append([KeyboardButton(text="⚙️ Sozlamalar")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(f"Salom, {m.from_user.full_name}!", reply_markup=main_kb(m.from_user.id))

# ================= ADMIN: MAHSULOT QO'SHISH =================
@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_start(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await state.set_state(AdminState.photo)
    await m.answer("📸 Rasm yuboring (Fayl yoki Rasm):", reply_markup=ReplyKeyboardRemove())

@dp.message(StateFilter(AdminState.photo))
async def get_media(m: types.Message, state: FSMContext):
    fid = None
    if m.photo: fid = m.photo[-1].file_id
    elif m.document: fid = m.document.file_id
    
    if fid:
        await state.update_data(file_id=fid)
        await m.answer("✅ Rasm olindi! Nomini yozing:")
        await state.set_state(AdminState.name)
    else:
        await m.answer("⚠️ Rasm yoki fayl yuboring.")

@dp.message(AdminState.name)
async def get_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("💰 Narxi (faqat raqam):")
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
    await m.answer("📦 Ombordagi soni (raqam):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def get_stock(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Raqam yozing!")
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Mahsulot qo'shildi!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# ================= ADMIN: BUYURTMALARNI BOSHQARISH =================
@dp.message(F.text == "📦 Buyurtmalar")
async def orders_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 Yangi", callback_data="ord_list_new")
    kb.button(text="🔄 Tayyorlanmoqda", callback_data="ord_list_processing")
    kb.button(text="✅ Tayyor/Kutilmoqda", callback_data="ord_list_ready")
    kb.button(text="🚚 Yo'lda", callback_data="ord_list_shipped")
    kb.button(text="🏁 Yopilgan", callback_data="ord_list_delivered")
    kb.adjust(2)
    await m.answer("Status bo'yicha buyurtmalarni tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ord_list_"))
async def show_orders(call: types.CallbackQuery):
    status = call.data.split("_")[2]
    orders = await get_orders_by_status(status)
    if not orders:
        await call.answer("Bu statusda buyurtmalar yo'q", show_alert=True)
        return
    
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"#{o['order_id']} | {o['total_price']} so'm", callback_data=f"open_ord_{o['order_id']}")
    kb.adjust(1)
    kb.button(text="🔙 Orqaga", callback_data="back_ord_menu")
    await call.message.edit_text(f"Status: {status}\nBuyurtmani tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_ord_menu")
async def back_ord(call: types.CallbackQuery):
    await orders_menu(call.message)

@dp.callback_query(F.data.startswith("open_ord_"))
async def open_order(call: types.CallbackQuery):
    oid = call.data.split("_")[2]
    o = await get_order_by_id(oid)
    
    txt = f"🆔 <b>Chek: #{o['order_id']}</b>\n"
    txt += f"👤 Mijoz: {o['user_name']}\n📞 Tel: {o['phone']}\n"
    txt += f"📍 Loc: {o.get('location', 'Yoq')}\n"
    txt += f"💬 Izoh: {o.get('comment', 'Yoq')}\n"
    txt += f"💳 To'lov: {o['pay_method']}\n\n"
    txt += "🛒 <b>Mahsulotlar:</b>\n"
    for pid, item in o['cart'].items():
        txt += f"- {item['name']} x {item['qty']} ta\n"
    txt += f"\n💰 Jami: {o['total_price']} so'm\n"
    txt += f"📊 Hozirgi status: <b>{o['status']}</b>"

    kb = InlineKeyboardBuilder()
    # Status o'zgartirish tugmalari
    kb.button(text="🔄 Tayyorlanmoqda", callback_data=f"setst_{oid}_processing")
    kb.button(text="✅ Tayyor (Kutish)", callback_data=f"setst_{oid}_ready")
    kb.button(text="🚚 Yo'lga chiqdi", callback_data=f"setst_{oid}_shipped")
    kb.button(text="🏁 Yetkazildi (Yopish)", callback_data=f"setst_{oid}_delivered")
    kb.button(text="❌ Rad etish", callback_data=f"setst_{oid}_canceled")
    kb.adjust(2)
    kb.button(text="🔙 Orqaga", callback_data=f"ord_list_{o['status']}")
    
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("setst_"))
async def set_status(call: types.CallbackQuery):
    _, oid, status = call.data.split("_")
    await update_order_status(oid, status)
    
    # Mijozga xabar yuborish (ixtiyoriy, agar bot to'siqqa uchramasa)
    o = await get_order_by_id(oid)
    try:
        status_text = {
            "processing": "🔄 Buyurtmangiz tayyorlanmoqda...",
            "ready": "✅ Buyurtmangiz TAYYOR! Olib ketishingiz mumkin.",
            "shipped": "🚚 Buyurtmangiz yo'lga chiqdi.",
            "delivered": "🏁 Buyurtma yetkazildi. Xaridingiz uchun rahmat!",
            "canceled": "❌ Buyurtmangiz rad etildi."
        }
        msg = f"🆔 <b>Chek: #{oid}</b>\nStatus o'zgardi: {status_text.get(status, status)}"
        await bot.send_message(o['user_id'], msg, parse_mode="HTML")
    except: pass

    await call.answer("Status o'zgardi!")
    await open_order(call) # Oynani yangilash

# ================= USER: DO'KON (PAGINATION) =================
@dp.message(F.text == "🛍 Do'kon")
async def shop(m: types.Message):
    await show_shop_page(m, page=0)

async def show_shop_page(m_or_call, page):
    products, total = await get_products_paginated(page, 6) # 6 ta mahsulot
    
    if not products and page == 0:
        if isinstance(m_or_call, types.CallbackQuery):
             await m_or_call.answer("Mahsulot yo'q")
        else:
             await m_or_call.answer("Mahsulot yo'q.")
        return

    kb = InlineKeyboardBuilder()
    # 2 ta ustun qilib chiqaramiz
    for p in products:
        # stock tekshiruvi
        if p.get('stock', 0) > 0:
            kb.button(text=f"{p['name']} - {p['price']}", callback_data=f"v_{p['_id']}")
    kb.adjust(2) # 2 ta ustun

    # Paginatsiya tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"page_{page-1}"))
    
    if (page + 1) * 6 < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        kb.row(*nav_buttons)

    txt = "📦 Mahsulotlar bo'limi:"
    
    if isinstance(m_or_call, types.Message):
        await m_or_call.answer(txt, reply_markup=kb.as_markup())
    else:
        await m_or_call.message.edit_text(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("page_"))
async def paginate(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    await show_shop_page(call, page)

@dp.callback_query(F.data.startswith("v_"))
async def view(call: types.CallbackQuery):
    p = await get_product(call.data.split("_")[1])
    if not p: return await call.answer("Topilmadi")
    cap = f"📱 {p['name']}\n💰 {p['price']} so'm\n📝 {p['description']}\n📦 Qolgan: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Savatga qo'shish", callback_data=f"add_{p['_id']}")
    kb.button(text="🔙 Orqaga", callback_data="back_shop_0") # 0-sahifaga qaytish
    try: await call.message.answer_photo(p['file_id'], caption=cap, reply_markup=kb.as_markup())
    except: await call.message.answer_document(p['file_id'], caption=cap, reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data == "back_shop_0")
async def back_sh(call: types.CallbackQuery):
    await call.message.delete()
    await show_shop_page(call.message, 0) # Message object yasab yuboramiz

# ================= SAVAT VA BUYURTMA =================
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
        await finish_step(call.message, state, "Naqd")
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
    
    if fid: await finish_step(m, state, "Karta", fid)
    else: await m.answer("Rasm yoki fayl yuboring.")

async def finish_step(m, state, pay_method, check_id=None):
    d = await state.get_data()
    cart = d.get("cart", {})
    
    total = 0
    for pid, i in cart.items():
        total += i['price'] * i['qty']
        await decrease_stock(pid, i['qty'])

    # Buyurtmani bazaga yozamiz
    order_id = await create_order(
        user_id=m.chat.id,
        user_name=m.chat.full_name,
        phone=d.get('phone'),
        cart=cart,
        total_price=total,
        pay_method=pay_method,
        delivery_type=d.get('dtype'),
        location=d.get('loc'),
        comment="Yangi"
    )

    # Mijozga chek raqamini beramiz
    await m.answer(f"✅ Buyurtma qabul qilindi!\n🆔 <b>Chek ID: #{order_id}</b>\n\nIltimos, mahsulotni olishda shu kodni ko'rsating.", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

    # Adminga xabar
    txt = f"🚨 <b>YANGI BUYURTMA #{order_id}</b>\nStatus: 🆕 Yangi\nJami: {total} so'm"
    for admin in ADMIN_IDS:
        try:
            if check_id:
                 try: await bot.send_photo(admin, check_id, caption=txt, parse_mode="HTML")
                 except: await bot.send_document(admin, check_id, caption=txt, parse_mode="HTML")
            else:
                 await bot.send_message(admin, txt, parse_mode="HTML")
        except: pass
    
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

# ... (Manzil, Sonini tahrirlash, O'chirish qismlari avvalgi kod bilan bir xil, ularni o'zgartirish shart emas) ...
# Joyni tejash uchun ularni takrorlamadim, lekin ular ham kodda bo'lishi kerak.
# Agar kerak bo'lsa, ularni ham qo'shib to'liq faylni beraman. 

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

# --- INFO ---
@dp.message(F.text == "ℹ️ Biz haqimizda")
async def about(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Manzil: {i['address']}")

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
