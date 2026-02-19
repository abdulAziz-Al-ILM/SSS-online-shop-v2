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
    rows = [[KeyboardButton(text="🛍 Дўкон"), KeyboardButton(text="🛒 Сават")],
            [KeyboardButton(text="ℹ️ Биз ҳақимизда")]]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="📦 Буюртмалар"), KeyboardButton(text="➕ Маҳсулот қўшиш")])
        rows.append([KeyboardButton(text="⚙️ Созламалар")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(f"Салом, {m.from_user.full_name}!", reply_markup=main_kb(m.from_user.id))

# ================= ADMIN: MAHSULOT QO'SHISH =================
@dp.message(F.text == "➕ Маҳсулот қўшиш")
async def add_start(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await state.set_state(AdminState.photo)
    await m.answer("📸 Расм юборинг (Файл ёки Расм):", reply_markup=ReplyKeyboardRemove())

@dp.message(StateFilter(AdminState.photo))
async def get_media(m: types.Message, state: FSMContext):
    fid = None
    if m.photo: fid = m.photo[-1].file_id
    elif m.document: fid = m.document.file_id
    
    if fid:
        await state.update_data(file_id=fid)
        await m.answer("✅ Расм олинди! Номини ёзинг:")
        await state.set_state(AdminState.name)
    else:
        await m.answer("⚠️ Расм ёки файл юборинг.")

@dp.message(AdminState.name)
async def get_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("💰 Нархи (фақат рақам):")
    await state.set_state(AdminState.price)

@dp.message(AdminState.price)
async def get_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    await state.update_data(price=int(m.text))
    await m.answer("📝 Тавсиф:")
    await state.set_state(AdminState.desc)

@dp.message(AdminState.desc)
async def get_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("📦 Омбордаги сони (рақам):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def get_stock(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Маҳсулот қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# ================= ADMIN: BUYURTMALARNI BOSHQARISH =================
@dp.message(F.text == "📦 Буюртмалар")
async def orders_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 Янги", callback_data="ord_list_new")
    kb.button(text="🔄 Тайёрланмоқда", callback_data="ord_list_processing")
    kb.button(text="✅ Тайёр/Кутилмоқда", callback_data="ord_list_ready")
    kb.button(text="🚚 Йўлда", callback_data="ord_list_shipped")
    kb.button(text="🏁 Ёпилган", callback_data="ord_list_delivered")
    kb.adjust(2)
    await m.answer("Статус бўйича буюртмаларни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ord_list_"))
async def show_orders(call: types.CallbackQuery):
    status = call.data.split("_")[2]
    orders = await get_orders_by_status(status)
    if not orders:
        await call.answer("Бу статусда буюртмалар йўқ", show_alert=True)
        return
    
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"#{o['order_id']} | {o['total_price']} сўм", callback_data=f"open_ord_{o['order_id']}")
    kb.adjust(1)
    kb.button(text="🔙 Орқага", callback_data="back_ord_menu")
    await call.message.edit_text(f"Статус: {status}\nБуюртмани танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_ord_menu")
async def back_ord(call: types.CallbackQuery):
    await orders_menu(call.message)

@dp.callback_query(F.data.startswith("open_ord_"))
async def open_order(call: types.CallbackQuery):
    oid = call.data.split("_")[2]
    o = await get_order_by_id(oid)
    
    txt = f"🆔 <b>Чек: #{o['order_id']}</b>\n"
    txt += f"👤 Мижоз: {o['user_name']}\n📞 Тел: {o['phone']}\n"
    txt += f"📍 Локация: {o.get('location', 'Йўқ')}\n"
    txt += f"💬 Изоҳ: {o.get('comment', 'Йўқ')}\n"
    txt += f"💳 Тўлов: {o['pay_method']}\n\n"
    txt += "🛒 <b>Маҳсулотлар:</b>\n"
    for pid, item in o['cart'].items():
        txt += f"- {item['name']} x {item['qty']} та\n"
    txt += f"\n💰 Жами: {o['total_price']} сўм\n"
    txt += f"📊 Ҳозирги статус: <b>{o['status']}</b>"

    kb = InlineKeyboardBuilder()
    # Status o'zgartirish tugmalari
    kb.button(text="🔄 Тайёрланмоқда", callback_data=f"setst_{oid}_processing")
    kb.button(text="✅ Тайёр (Кутиш)", callback_data=f"setst_{oid}_ready")
    kb.button(text="🚚 Йўлга чиқди", callback_data=f"setst_{oid}_shipped")
    kb.button(text="🏁 Етказилди (Ёпиш)", callback_data=f"setst_{oid}_delivered")
    kb.button(text="❌ Рад этиш", callback_data=f"setst_{oid}_canceled")
    kb.adjust(2)
    kb.button(text="🔙 Орқага", callback_data=f"ord_list_{o['status']}")
    
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("setst_"))
async def set_status(call: types.CallbackQuery):
    _, oid, status = call.data.split("_")
    await update_order_status(oid, status)
    
    # Mijozga xabar yuborish (ixtiyoriy, agar bot to'siqqa uchramasa)
    o = await get_order_by_id(oid)
    try:
        status_text = {
            "processing": "🔄 Буюртмангиз тайёрланмоқда...",
            "ready": "✅ Буюртмангиз ТАЙЁР! Олиб кетишингиз мумкин.",
            "shipped": "🚚 Буюртмангиз йўлга чиқди.",
            "delivered": "🏁 Буюртма етказилди. Харидингиз учун раҳмат!",
            "canceled": "❌ Буюртмангиз рад этилди."
        }
        msg = f"🆔 <b>Чек: #{oid}</b>\nСтатус ўзгарди: {status_text.get(status, status)}"
        await bot.send_message(o['user_id'], msg, parse_mode="HTML")
    except: pass

    await call.answer("Статус ўзгарди!")
    await open_order(call) # Oynani yangilash

# ================= USER: DO'KON (PAGINATION) =================
@dp.message(F.text == "🛍 Дўкон")
async def shop(m: types.Message):
    await show_shop_page(m, page=0)

async def show_shop_page(m_or_call, page):
    products, total = await get_products_paginated(page, 6) # 6 ta mahsulot
    
    if not products and page == 0:
        if isinstance(m_or_call, types.CallbackQuery):
             await m_or_call.answer("Маҳсулот йўқ")
        else:
             await m_or_call.answer("Маҳсулот йўқ.")
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
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"page_{page-1}"))
    
    if (page + 1) * 6 < total:
        nav_buttons.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        kb.row(*nav_buttons)

    txt = "📦 Маҳсулотлар бўлими:"
    
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
    if not p: return await call.answer("Топилмади")
    cap = f"📱 {p['name']}\n💰 {p['price']} сўм\n📝 {p['description']}\n📦 Қолган: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Саватга қўшиш", callback_data=f"add_{p['_id']}")
    kb.button(text="🔙 Орқага", callback_data="back_shop_0") # 0-sahifaga qaytish
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
    await call.message.answer("🔢 Нечта?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.input_qty)
    await call.answer()

@dp.message(UserState.input_qty)
async def save_cart(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг.")
    qty = int(m.text)
    d = await state.get_data()
    p = await get_product(d['pid'])
    
    if qty > p['stock']: return await m.answer(f"Бизда {p['stock']} та бор холос.")
    
    u_data = await state.get_data()
    cart = u_data.get("cart", {})
    pid = str(p['_id'])
    
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty}
    
    await state.update_data(cart=cart)
    await m.answer("✅ Саватга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.set_state(None)

@dp.message(F.text == "🛒 Сават")
async def show_cart(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart = d.get("cart", {})
    if not cart: return await m.answer("Сават бўш.")
    
    txt = "🛒 Сават:\n"
    tot = 0
    for i in cart.values():
        s = i['price'] * i['qty']
        tot += s
        txt += f"- {i['name']} x {i['qty']} = {s}\n"
    txt += f"\nЖами: {tot} сўм"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Буюртма бериш", callback_data="checkout")
    kb.button(text="Тозалаш", callback_data="clear")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "clear")
async def clr(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Тозаланди.")

@dp.callback_query(F.data == "checkout")
async def check(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("📞 Рақам юборинг:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Рақам", request_contact=True)]], resize_keyboard=True))
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def get_ph(m: types.Message, state: FSMContext):
    p = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=p)
    kb = InlineKeyboardBuilder()
    kb.button(text="Ўзим олиб кетаман", callback_data="pick")
    kb.button(text="Етказиб бериш (Такси)", callback_data="taxi")
    kb.adjust(1)
    await m.answer("Турини танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.in_({"pick", "taxi"}))
async def del_type(call: types.CallbackQuery, state: FSMContext):
    dtype = call.data
    await state.update_data(dtype=dtype)
    if dtype == "taxi":
        await call.message.answer("Локация юборинг:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Локация", request_location=True)]], resize_keyboard=True))
        await state.set_state(UserState.location)
    else:
        await finish_step(call.message, state, "Нақд")
    await call.answer()

@dp.message(UserState.location)
async def get_loc(m: types.Message, state: FSMContext):
    loc = f"geo:{m.location.latitude},{m.location.longitude}" if m.location else m.text
    await state.update_data(loc=loc)
    await m.answer(f"Карта: `{CARD_NUMBER}`\nЧекни юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.check_photo)

@dp.message(UserState.check_photo)
async def get_check(m: types.Message, state: FSMContext):
    fid = None
    if m.photo: fid = m.photo[-1].file_id
    elif m.document: fid = m.document.file_id
    
    if fid: await finish_step(m, state, "Карта", fid)
    else: await m.answer("Расм ёки файл юборинг.")

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
        comment="Янги"
    )

    # Mijozga chek raqamini beramiz
    await m.answer(f"✅ Буюртма қабул қилинди!\n🆔 <b>Чек ID: #{order_id}</b>\n\nИлтимос, маҳсулотни олишда шу кодни кўрсатинг.", parse_mode="HTML", reply_markup=main_kb(m.from_user.id))

    # Adminga xabar
    txt = f"🚨 <b>ЯНГИ БУЮРТМА #{order_id}</b>\nСтатус: 🆕 Янги\nЖами: {total} сўм"
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
@dp.message(F.text == "⚙️ Созламалар")
async def settings(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="Манзил", callback_data="set_addr")
    kb.button(text="Сони таҳрирлаш", callback_data="edit_st")
    kb.button(text="Ўчириш", callback_data="del_prod")
    kb.adjust(1)
    await m.answer("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "set_addr")
async def ask_addr(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Янги манзилни ёзинг:")
    await state.set_state(AdminState.shop_address)
    await call.answer()

@dp.message(AdminState.shop_address)
async def save_addr(m: types.Message, state: FSMContext):
    await set_shop_info(m.text)
    await m.answer("✅ Манзил сақланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "edit_st")
async def list_edit(call: types.CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']} ({p['stock']})", callback_data=f"est_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("est_"))
async def ask_new_st(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("Янги сонини ёзинг:")
    await state.set_state(AdminState.edit_stock_qty)
    await call.answer()

@dp.message(AdminState.edit_stock_qty)
async def save_st(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    d = await state.get_data()
    await set_product_stock(d['pid'], int(m.text))
    await m.answer("✅ Янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_prod")
async def list_del(call: types.CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"❌ {p['name']}", callback_data=f"del_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def del_item(call: types.CallbackQuery):
    await delete_product(call.data.split("_")[1])
    await call.answer("Ўчирилди!")
    await call.message.delete()

# --- INFO ---
@dp.message(F.text == "ℹ️ Биз ҳақимизда")
async def about(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Манзил: {i['address']}")

# --- ZOMBI HIMOYASI ---
@dp.message()
async def zombie(m: types.Message):
    if is_admin(m.from_user.id) and (m.photo or m.document):
        await m.answer("⚠️ Бот янгиланди. Илтимос, 'Маҳсулот қўшиш'ни қайта босинг.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
