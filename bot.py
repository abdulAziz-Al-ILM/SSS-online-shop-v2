import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, 
    InlineKeyboardButton, CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_IDS, CARD_NUMBER
from database import *

# Tizim loglari
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= STATES (Hamma bosqichlar) =================

class AdminState(StatesGroup):
    # Mahsulot qo'shish va tahrirlash
    photo = State()
    name = State()
    price = State()
    desc = State()
    stock = State()
    edit_stock_qty = State()
    
    # Sayt: Xizmatlar (Qo'shish/O'chirish)
    srv_name = State()
    srv_desc = State()
    
    # Sayt: Lokatsiyalar (Qo'shish/O'chirish)
    loc_name = State()
    loc_address = State()
    loc_geo = State()
    
    # Sayt: Aksiyalar
    ad_title = State()
    ad_text = State()
    ad_discount = State()
    
    # Sayt: Logotip
    logo_photo = State()
    
    # Sayt: Sozlamalar va Tarmoqlar
    info_phone = State()
    info_address = State()
    info_about = State()
    soc_ch = State()
    soc_ig = State()
    soc_wa = State()

class UserState(StatesGroup):
    input_qty = State()
    phone = State()
    location = State()
    check_photo = State()

# ================= UTILS (Yordamchi mantiq) =================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_kb(user_id):
    # Mijozlar uchun asosiy tugmalar
    rows = [
        [KeyboardButton(text="🛍 Дўкон"), KeyboardButton(text="🛒 Сават")],
        [KeyboardButton(text="ℹ️ Биз ҳақимизда")]
    ]
    # Admin (Dada) uchun to'liq boshqaruv paneli
    if is_admin(user_id):
        rows.append([KeyboardButton(text="📦 Буюртмалар"), KeyboardButton(text="➕ Маҳсулот")])
        rows.append([KeyboardButton(text="🛠 Хизмат"), KeyboardButton(text="📍 Филиал")])
        rows.append([KeyboardButton(text="🔥 Аксия"), KeyboardButton(text="🖼 Логотип")])
        rows.append([KeyboardButton(text="⚙️ Тармоқлар ва инфо"), KeyboardButton(text="⚙️ Созламалар")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# ================= START & DEEP LINK =================

@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    # Saytdagi "Buyurtma" tugmasidan kelsa
    if len(m.text.split()) > 1 and m.text.split()[1].startswith("order_"):
        pid = m.text.split()[1].replace("order_", "")
        p = await get_product(pid)
        if p:
            await state.update_data(pid=pid)
            await m.answer(f"📦 <b>{p['name']}</b> танланди.\nСонини киритинг:", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserState.input_qty)
            return
            
    await m.answer(f"Салом, {m.from_user.full_name}! Хуш келибсиз.", reply_markup=main_kb(m.from_user.id))

# ================= ADMIN: XIZMATLARNI BOSHQARISH =================

@dp.message(F.text == "🛠 Хизмат")
async def services_manage(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Янги хизмат", callback_data="add_srv")
    kb.button(text="❌ Ўчириш", callback_data="del_srv_list")
    kb.adjust(1)
    await m.answer("Хизматлар бўлими:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "add_srv")
async def add_srv_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Хизмат номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.srv_name)
    await call.answer()

@dp.message(AdminState.srv_name)
async def srv_name_get(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Тавсифи:")
    await state.set_state(AdminState.srv_desc)

@dp.message(AdminState.srv_desc)
async def srv_desc_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_service(d['name'], m.text)
    await m.answer("✅ Хизмат қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_srv_list")
async def srv_del_list(call: CallbackQuery):
    srvs = await get_all_services()
    kb = InlineKeyboardBuilder()
    for s in srvs: kb.button(text=f"❌ {s['name']}", callback_data=f"dsrv_{s['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиганни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dsrv_"))
async def srv_del_exec(call: CallbackQuery):
    await delete_service(call.data.split("_")[1])
    await call.answer("Ўчирилди!")
    await srv_del_list(call)

# ================= ADMIN: LOKATSIYALARNI BOSHQARISH =================

@dp.message(F.text == "📍 Филиал")
async def loc_manage(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Янги филиал", callback_data="add_loc")
    kb.button(text="❌ Ўчириш", callback_data="del_loc_list")
    kb.adjust(1)
    await m.answer("Филиаллар бошқаруви:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "add_loc")
async def add_loc_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Филиал номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.loc_name)
    await call.answer()

@dp.message(AdminState.loc_name)
async def loc_name_get(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Манзилни ёзинг:")
    await state.set_state(AdminState.loc_address)

@dp.message(AdminState.loc_address)
async def loc_addr_get(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Локация юбориш", request_location=True)]], resize_keyboard=True)
    await m.answer("Харитадан нуқтани юборинг:", reply_markup=kb)
    await state.set_state(AdminState.loc_geo)

@dp.message(AdminState.loc_geo, F.location)
async def loc_geo_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_location(d['name'], d['address'], m.location.latitude, m.location.longitude)
    await m.answer("✅ Филиал сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_loc_list")
async def loc_del_list(call: CallbackQuery):
    locs = await get_all_locations()
    kb = InlineKeyboardBuilder()
    for l in locs: kb.button(text=f"❌ {l['name']}", callback_data=f"dloc_{l['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган филиал:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dloc_"))
async def loc_del_exec(call: CallbackQuery):
    await delete_location(call.data.split("_")[1])
    await call.answer("Ўчирилди!")
    await loc_del_list(call)

# ================= ADMIN: AKSIYALARNI BOSHQARISH =================

@dp.message(F.text == "🔥 Аксия")
async def ads_manage(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Янги аксия", callback_data="add_ad")
    kb.button(text="❌ Ўчириш", callback_data="del_ad_list")
    kb.adjust(1)
    await m.answer("Аксиялар бошқаруви:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "add_ad")
async def add_ad_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Аксия сарлавҳаси:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.ad_title)
    await call.answer()

@dp.message(AdminState.ad_title)
async def ad_title_get(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text)
    await m.answer("Тавсифи:")
    await state.set_state(AdminState.ad_text)

@dp.message(AdminState.ad_text)
async def ad_text_get(m: types.Message, state: FSMContext):
    await state.update_data(text=m.text)
    await m.answer("Чегирма фоизи (фақат рақам):")
    await state.set_state(AdminState.ad_discount)

@dp.message(AdminState.ad_discount)
async def ad_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_ad(d['title'], d['text'], int(m.text) if m.text.isdigit() else 0)
    await m.answer("✅ Аксия сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_ad_list")
async def ad_del_list(call: CallbackQuery):
    ads = await get_all_ads()
    kb = InlineKeyboardBuilder()
    for a in ads: kb.button(text=f"❌ {a['title']}", callback_data=f"dad_{a['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган аксия:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dad_"))
async def ad_del_exec(call: CallbackQuery):
    await delete_ad(call.data.split("_")[1])
    await call.answer("Ўчирилди!")
    await ad_del_list(call)

# ================= ADMIN: TARMOQLAR VA INFO =================

@dp.message(F.text == "⚙️ Тармоқлар ва инфо")
async def settings_info_manage(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Сайтдаги телефон рақам (хоҳлаган форматда):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.info_phone)

@dp.message(AdminState.info_phone)
async def set_info_ph(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    await m.answer("Асосий манзил:")
    await state.set_state(AdminState.info_address)

@dp.message(AdminState.info_address)
async def set_info_addr(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    await m.answer("Фирма ҳақида қисқача:")
    await state.set_state(AdminState.info_about)

@dp.message(AdminState.info_about)
async def set_info_ab(m: types.Message, state: FSMContext):
    await state.update_data(about=m.text)
    await m.answer("Telegram канал ҳаволаси:")
    await state.set_state(AdminState.soc_ch)

@dp.message(AdminState.soc_ch)
async def set_soc_ch(m: types.Message, state: FSMContext):
    await state.update_data(ch=m.text)
    await m.answer("Instagram ҳаволаси:")
    await state.set_state(AdminState.soc_ig)

@dp.message(AdminState.soc_ig)
async def set_soc_ig(m: types.Message, state: FSMContext):
    await state.update_data(ig=m.text)
    await m.answer("WhatsApp ҳаволаси:")
    await state.set_state(AdminState.soc_wa)

@dp.message(AdminState.soc_wa)
async def set_soc_wa_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    bot_me = await bot.get_me()
    await set_shop_info(d['address'], d['phone'], d['about'])
    await set_social_links(f"https://t.me/{bot_me.username}", d['ig'], m.text, d['ch'])
    await m.answer("✅ Барча маълумотлар янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# ================= ADMIN: LOGOTIP VA MAHSULOT =================

@dp.message(F.text == "🖼 Логотип")
async def logo_manage(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Янги логотип учун расм юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.logo_photo)

@dp.message(AdminState.logo_photo, F.photo)
async def logo_save(m: types.Message, state: FSMContext):
    await set_logo(m.photo[-1].file_id)
    await m.answer("✅ Логотип янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "➕ Маҳсулот")
async def add_product_start(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Маҳсулот расми:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.photo)

@dp.message(AdminState.photo, F.photo)
async def add_p_photo(m: types.Message, state: FSMContext):
    await state.update_data(file_id=m.photo[-1].file_id)
    await m.answer("Номи:")
    await state.set_state(AdminState.name)

@dp.message(AdminState.name)
async def add_p_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Нархи:")
    await state.set_state(AdminState.price)

@dp.message(AdminState.price)
async def add_p_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам киритинг!")
    await state.update_data(price=int(m.text))
    await m.answer("Тавсифи:")
    await state.set_state(AdminState.desc)

@dp.message(AdminState.desc)
async def add_p_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("Омборда (сони):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def add_p_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Маҳсулот қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# ================= BUYURTMALAR BOSHQARUVI =================

@dp.message(F.text == "📦 Буюртмалар")
async def orders_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    statuses = [("🆕 Янги", "new"), ("🔄 Тайёрланмоқда", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпилган", "delivered")]
    for label, code in statuses:
        kb.button(text=label, callback_data=f"ord_list_{code}")
    kb.adjust(2)
    await m.answer("Статус бўйича буюртмалар:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ord_list_"))
async def orders_list_show(call: CallbackQuery):
    status = call.data.split("_")[2]
    orders = await get_orders_by_status(status)
    if not orders: return await call.answer("Йўқ", show_alert=True)
    kb = InlineKeyboardBuilder()
    for o in orders: kb.button(text=f"#{o['order_id']} | {o['total_price']}", callback_data=f"open_ord_{o['order_id']}")
    kb.adjust(1)
    kb.button(text="🔙 Орқага", callback_data="back_ord_menu")
    await call.message.edit_text(f"Статус: {status}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_ord_menu")
async def back_ord(call: CallbackQuery): await orders_menu(call.message)

@dp.callback_query(F.data.startswith("open_ord_"))
async def order_open(call: CallbackQuery):
    o = await get_order_by_id(call.data.split("_")[2])
    txt = f"🆔 <b>Буюртма: #{o['order_id']}</b>\n👤 {o['user_name']}\n📞 {o['phone']}\n💰 {o['total_price']} сўм\n📊 Status: {o['status']}"
    kb = InlineKeyboardBuilder()
    btns = [("🔄 Ишлаш", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпиш", "delivered"), ("❌ Рад этиш", "canceled")]
    for label, st in btns: kb.button(text=label, callback_data=f"setst_{o['order_id']}_{st}")
    kb.adjust(2)
    kb.button(text="🔙 Орқага", callback_data=f"ord_list_{o['status']}")
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("setst_"))
async def order_status_set(call: CallbackQuery):
    _, oid, st = call.data.split("_")
    await update_order_status(oid, st)
    await call.answer("Янгиланди!")
    await order_open(call)

# ================= MIJOZ: DO'KON VA SAVATCHA =================

@dp.message(F.text == "🛍 Дўкон")
async def user_shop(m: types.Message): await shop_show(m, 0)

async def shop_show(m_or_call, page):
    prods, total = await get_products_paginated(page, 6)
    if not prods: 
        msg = "Маҳсулот йўқ."
        return await m_or_call.answer(msg) if isinstance(m_or_call, types.Message) else m_or_call.answer(msg)
    
    kb = InlineKeyboardBuilder()
    for p in prods:
        if p.get('stock', 0) > 0: kb.button(text=f"{p['name']}", callback_data=f"v_{p['_id']}")
    kb.adjust(2)
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}"))
    if (page + 1) * 6 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}"))
    if nav: kb.row(*nav)
    
    txt = "📦 Маҳсулотларимиз:"
    if isinstance(m_or_call, types.Message): await m_or_call.answer(txt, reply_markup=kb.as_markup())
    else: await m_or_call.message.edit_text(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("page_"))
async def user_paginate(call: CallbackQuery): await shop_show(call, int(call.data.split("_")[1]))

@dp.callback_query(F.data.startswith("v_"))
async def user_view(call: CallbackQuery):
    p = await get_product(call.data.split("_")[1])
    cap = f"📱 <b>{p['name']}</b>\n💰 {p['price']} сўм\n📝 {p['description']}\n📦 Омборда: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Саватга", callback_data=f"add_{p['_id']}")
    kb.button(text="🔙 Орқага", callback_data="page_0")
    try: await call.message.answer_photo(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    except: await call.message.answer_document(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data.startswith("add_"))
async def user_add_qty(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("Нечта керак?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.input_qty)

@dp.message(UserState.input_qty)
async def user_save_cart(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам!")
    qty = int(m.text)
    d = await state.get_data()
    p = await get_product(d['pid'])
    if qty > p['stock']: return await m.answer(f"Фақат {p['stock']} та бор.")
    
    cart = d.get("cart", {})
    pid = str(p['_id'])
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty}
    
    await state.update_data(cart=cart)
    await m.answer("✅ Саватга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.set_state(None)

@dp.message(F.text == "🛒 Сават")
async def user_cart_view(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart = d.get("cart", {})
    if not cart: return await m.answer("Сават бўш.")
    txt = "🛒 Сават:\n"
    total = 0
    for i in cart.values():
        total += i['price'] * i['qty']
        txt += f"- {i['name']} x {i['qty']} = {i['price']*i['qty']} сўм\n"
    txt += f"\n💰 Жами: {total} сўм"
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Буюртма", callback_data="checkout")
    kb.button(text="🗑 Тозалаш", callback_data="clear_c")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "clear_c")
async def user_clear_cart(call: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Сават тозаланди.")

@dp.callback_query(F.data == "checkout")
async def user_checkout_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Тел рақамни юборинг:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Юбориш", request_contact=True)]], resize_keyboard=True))
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def user_phone_get(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number if m.contact else m.text)
    d = await state.get_data()
    cart = d.get("cart", {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    oid = await create_order(m.from_user.id, m.from_user.full_name, d['phone'], cart, total, "Нақд", "Етказиб", "Йўқ", "Янги")
    for pid, i in cart.items(): await decrease_stock(pid, i['qty'])
    await m.answer(f"✅ Қабул қилинди! ID: #{oid}", reply_markup=main_kb(m.from_user.id))
    for a in ADMIN_IDS: await bot.send_message(a, f"🚨 Янги буюртма #{oid}")
    await state.update_data(cart={})
    await state.set_state(None)

# ================= ADMIN: QO'SHIMCHA SOZLAMALAR =================

@dp.message(F.text == "⚙️ Созламалар")
async def admin_extra_settings(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Омборни таҳрирлаш", callback_data="e_st_l")
    kb.button(text="❌ Маҳсулотни ўчириш", callback_data="d_p_l")
    kb.adjust(1)
    await m.answer("Нимани ўзгартирамиз?", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "e_st_l")
async def admin_edit_stock_list(call: CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']} ({p['stock']})", callback_data=f"est_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("est_"))
async def admin_ask_new_stock(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("Янги сонини ёзинг:")
    await state.set_state(AdminState.edit_stock_qty)

@dp.message(AdminState.edit_stock_qty)
async def admin_save_new_stock(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам!")
    d = await state.get_data()
    await set_product_stock(d['pid'], int(m.text))
    await m.answer("✅ Янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "d_p_l")
async def admin_del_prod_list(call: CallbackQuery):
    prods = await get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"❌ {p['name']}", callback_data=f"dp_{p['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган маҳсулот:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dp_"))
async def admin_del_prod_exec(call: CallbackQuery):
    await delete_product(call.data.split("_")[1])
    await call.answer("Ўчирилди!")
    await admin_del_prod_list(call)

# ================= INFO =================

@dp.message(F.text == "ℹ️ Биз ҳақимизда")
async def about_view(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Манзил: {i['address']}\n📞 Тел: {i['phone']}\nℹ️ {i['about']}")

# ================= RUN =================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
