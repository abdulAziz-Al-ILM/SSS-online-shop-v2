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
    InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_IDS, CARD_NUMBER
from database import *

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================================================================
# 1. STATES (HOLATLAR) - BARCHA BOSQICHLAR UCHUN
# =====================================================================

class AdminState(StatesGroup):
    # Mahsulot boshqaruvi
    photo = State()
    name = State()
    price = State()
    desc = State()
    stock = State()
    edit_stock_qty = State()
    
    # Sayt: Xizmatlar
    srv_name = State()
    srv_desc = State()
    
    # Sayt: Lokatsiyalar
    loc_name = State()
    loc_address = State()
    loc_geo = State()
    
    # Sayt: Aksiyalar
    ad_title = State()
    ad_text = State()
    ad_discount = State()
    
    # Sayt: Sozlamalar
    info_phone = State()
    info_address = State()
    info_about = State()
    soc_ch = State()
    soc_ig = State()
    soc_wa = State()
    logo_photo = State()
    trailer_video = State()

class UserState(StatesGroup):
    input_qty = State()
    phone = State()
    location = State()
    check_photo = State()

# =====================================================================
# 2. UTILS (YORDAMCHI FUNKSIYALAR)
# =====================================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_kb(user_id):
    """Asosiy menyu (Admin va Mijoz uchun alohida)"""
    rows = [
        [KeyboardButton(text="🛍 Дўкон"), KeyboardButton(text="🛒 Сават")],
        [KeyboardButton(text="ℹ️ Биз ҳақимизда")]
    ]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="📦 Буюртмалар"), KeyboardButton(text="➕ Маҳсулот")])
        rows.append([KeyboardButton(text="🛠 Хизмат"), KeyboardButton(text="📍 Филиал")])
        rows.append([KeyboardButton(text="🔥 Аксия"), KeyboardButton(text="🖼 Логотип")])
        rows.append([KeyboardButton(text="📹 Трейлер юклаш"), KeyboardButton(text="⚙️ Тармоқлар ва инфо")])
        rows.append([KeyboardButton(text="⚙️ Созламалар"), KeyboardButton(text="🗑 Маълумот ўчириш")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# =====================================================================
# 3. START & DEEP LINKING (WEBSITE INTEGRATION)
# =====================================================================

@dp.message(Command("start"))
async def start_handler(m: types.Message, state: FSMContext):
    await state.clear()
    
    # Saytdagi "Buyurtma berish" tugmasidan kelgan bo'lsa (start=order_ID)
    if len(m.text.split()) > 1 and m.text.split()[1].startswith("order_"):
        pid = m.text.split()[1].replace("order_", "")
        p = await get_product(pid)
        if p:
            await state.update_data(pid=pid)
            await m.answer(f"📦 <b>{p['name']}</b> танланди.\nСониni киритинг:", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserState.input_qty)
            return

    await m.answer(f"Салом, {m.from_user.full_name}! SSS Online Shop ботига хуш келибсиз.", reply_markup=main_kb(m.from_user.id))

# =====================================================================
# 4. ADMIN: SAYT ELEMENTLARINI BOSHQARISH (QO'SHISH)
# =====================================================================

# Xizmat qo'shish
@dp.message(F.text == "🛠 Хизмат")
async def add_srv_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Хизмат номи (мас: Сантехника):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.srv_name)

@dp.message(AdminState.srv_name)
async def srv_name_step(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Бу хизмат ҳақида маълумот:")
    await state.set_state(AdminState.srv_desc)

@dp.message(AdminState.srv_desc)
async def srv_desc_step(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_service(d['name'], m.text)
    await m.answer("✅ Хизмат сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# Lokatsiya (Filial) qo'shish
@dp.message(F.text == "📍 Филиал")
async def add_loc_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Филиал номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.loc_name)

@dp.message(AdminState.loc_name)
async def loc_name_step(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Манзилни ёзма равишда ёзинг:")
    await state.set_state(AdminState.loc_address)

@dp.message(AdminState.loc_address)
async def loc_addr_step(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Геолокация юбориш", request_location=True)]], resize_keyboard=True)
    await m.answer("Энди Telegram орқали нуқтани юборинг:", reply_markup=kb)
    await state.set_state(AdminState.loc_geo)

@dp.message(AdminState.loc_geo, F.location)
async def loc_geo_step(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_location(d['name'], d['address'], m.location.latitude, m.location.longitude)
    await m.answer("✅ Филиал ва харита сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# Aksiya qo'shish
@dp.message(F.text == "🔥 Аксия")
async def add_ad_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Аксия сарлавҳаси:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.ad_title)

@dp.message(AdminState.ad_title)
async def ad_title_step(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text)
    await m.answer("Маълумот:")
    await state.set_state(AdminState.ad_text)

@dp.message(AdminState.ad_text)
async def ad_text_step(m: types.Message, state: FSMContext):
    await state.update_data(text=m.text)
    await m.answer("Чегирма фоизи (фақат рақам):")
    await state.set_state(AdminState.ad_discount)

@dp.message(AdminState.ad_discount)
async def ad_final_step(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_ad(d['title'], d['text'], int(m.text) if m.text.isdigit() else 0)
    await m.answer("✅ Аксия сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# 5. ADMIN: MULTIMEDIA (LOGO & TRAILER)
# =====================================================================

@dp.message(F.text == "🖼 Логотип")
async def logo_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Янги логотип учун расм юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.logo_photo)

@dp.message(AdminState.logo_photo, F.photo)
async def logo_save_step(m: types.Message, state: FSMContext):
    await set_logo(m.photo[-1].file_id)
    await m.answer("✅ Логотип янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "📹 Трейлер юклаш")
async def trailer_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📹 Сайт учун видео-трейлер (MP4) юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.trailer_video)

@dp.message(AdminState.trailer_video, F.video)
async def trailer_save_step(m: types.Message, state: FSMContext):
    await set_trailer(m.video.file_id)
    await m.answer("✅ Видео-трейлер янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# 6. ADMIN: TARMOQLAR VA INFO (RAQAM CHEKLOVISIZ)
# =====================================================================

@dp.message(F.text == "⚙️ Тармоқлар ва инфо")
async def info_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Сайтдаги телефон рақамни ёзинг (хоҳлаган форматда):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.info_phone)

@dp.message(AdminState.info_phone)
async def info_phone_step(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    await m.answer("Асосий манзилни ёзинг:")
    await state.set_state(AdminState.info_address)

@dp.message(AdminState.info_address)
async def info_addr_step(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    await m.answer("Фирма ҳақида қисқача таъриф:")
    await state.set_state(AdminState.info_about)

@dp.message(AdminState.info_about)
async def info_about_step(m: types.Message, state: FSMContext):
    await state.update_data(about=m.text)
    await m.answer("Telegram канал ҳаволасини юборинг:")
    await state.set_state(AdminState.soc_ch)

@dp.message(AdminState.soc_ch)
async def info_ch_step(m: types.Message, state: FSMContext):
    await state.update_data(ch=m.text)
    await m.answer("Instagram ҳаволасини юборинг:")
    await state.set_state(AdminState.soc_ig)

@dp.message(AdminState.soc_ig)
async def info_ig_step(m: types.Message, state: FSMContext):
    await state.update_data(ig=m.text)
    await m.answer("WhatsApp ҳаволасини юборинг:")
    await state.set_state(AdminState.soc_wa)

@dp.message(AdminState.soc_wa)
async def info_final_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    bot_info = await bot.get_me()
    await set_shop_info(d['address'], d['phone'], d['about'])
    await set_social_links(f"https://t.me/{bot_info.username}", d['ig'], m.text, d['ch'])
    await m.answer("✅ Маълумотлар янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# 7. ADMIN: MAHSULOT QO'SHISH (TO'LIQ)
# =====================================================================

@dp.message(F.text == "➕ Маҳсулот")
async def add_p_cmd(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Маҳсулот расмини юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.photo)

@dp.message(AdminState.photo, F.photo)
async def add_p_photo(m: types.Message, state: FSMContext):
    await state.update_data(file_id=m.photo[-1].file_id)
    await m.answer("Номи:")
    await state.set_state(AdminState.name)

@dp.message(AdminState.name)
async def add_p_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Нархи (рақам):")
    await state.set_state(AdminState.price)

@dp.message(AdminState.price)
async def add_p_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Фақат рақам ёзинг!")
    await state.update_data(price=int(m.text))
    await m.answer("Тавсифи:")
    await state.set_state(AdminState.desc)

@dp.message(AdminState.desc)
async def add_p_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("Омборда (сони):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def add_p_final(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Фақат рақам ёзинг!")
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Маҳсулот базага қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# 8. ADMIN: O'CHIRISH TIZIMI (DELETE SYSTEM)
# =====================================================================

@dp.message(F.text == "🗑 Маълумот ўчириш")
async def delete_main_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="🛠 Хизматни ўчириш", callback_data="del_list_srv")
    kb.button(text="📍 Филиални ўчириш", callback_data="del_list_loc")
    kb.button(text="🔥 Аксияни ўчириш", callback_data="del_list_ad")
    kb.adjust(1)
    await m.answer("Нимани ўчирмоқчисиз?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_list_"))
async def delete_list_handler(call: CallbackQuery):
    target = call.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    
    if target == "srv":
        items = await get_all_services()
        for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"exec_dsrv_{i['_id']}")
    elif target == "loc":
        items = await get_all_locations()
        for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"exec_dloc_{i['_id']}")
    elif target == "ad":
        items = await get_all_ads()
        for i in items: kb.button(text=f"❌ {i['title']}", callback_data=f"exec_dad_{i['_id']}")
    
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган элементни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("exec_d"))
async def delete_execution_handler(call: CallbackQuery):
    action = call.data.split("exec_")[1]
    prefix = action[:3] # dsrv, dloc, dad
    oid = action[4:]
    
    if prefix == "srv": await delete_service(oid)
    elif prefix == "loc": await delete_location(oid)
    elif prefix == "ad": await delete_ad(oid)
    
    await call.answer("Муваффақиятли ўчирилди!")
    await call.message.delete()

# =====================================================================
# 9. ADMIN: BUYURTMALAR (ORDERS)
# =====================================================================

@dp.message(F.text == "📦 Буюртмалар")
async def admin_orders_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    for label, code in [("🆕 Янги", "new"), ("🔄 Ишда", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпилган", "delivered")]:
        kb.button(text=label, callback_data=f"ord_list_{code}")
    kb.adjust(2)
    await m.answer("Буюртмалар ҳолати:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ord_list_"))
async def admin_orders_list(call: CallbackQuery):
    st = call.data.split("_")[2]
    orders = await get_orders_by_status(st)
    if not orders: return await call.answer("Ҳозирча бўш", show_alert=True)
    kb = InlineKeyboardBuilder()
    for o in orders: kb.button(text=f"#{o['order_id']} | {o['total_price']}", callback_data=f"open_ord_{o['order_id']}")
    kb.adjust(1)
    kb.button(text="🔙 Орқага", callback_data="back_to_ord_menu")
    await call.message.edit_text(f"Ҳолат: {st}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_to_ord_menu")
async def back_to_orders(call: CallbackQuery): await admin_orders_menu(call.message)

@dp.callback_query(F.data.startswith("open_ord_"))
async def admin_order_detail(call: CallbackQuery):
    o = await get_order_by_id(call.data.split("_")[2])
    txt = f"🆔 <b>Буюртма: #{o['order_id']}</b>\n👤 {o['user_name']}\n📞 {o['phone']}\n💰 {o['total_price']} сўм\n📊 Ҳолати: {o['status']}"
    kb = InlineKeyboardBuilder()
    for label, st in [("🔄 Ишда", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпиш", "delivered"), ("❌ Рад этиш", "canceled")]:
        kb.button(text=label, callback_data=f"setst_{o['order_id']}_{st}")
    kb.adjust(2)
    kb.button(text="🔙 Орқага", callback_data=f"ord_list_{o['status']}")
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("setst_"))
async def admin_order_set_status(call: CallbackQuery):
    _, oid, st = call.data.split("_")
    await update_order_status(oid, st)
    await call.answer("Ҳолат янгиланди!")
    await admin_order_detail(call)

# =====================================================================
# 10. USER: DO'KON, SAVAT VA BUYURTMA (TO'LIQ)
# =====================================================================

@dp.message(F.text == "🛍 Дўкон")
async def user_shop_handler(m: types.Message): await shop_page_loader(m, 0)

async def shop_page_loader(m_or_call, page):
    prods, total = await get_products_paginated(page, 6)
    if not prods: return await (m_or_call.answer("Маҳсулот йўқ") if isinstance(m_or_call, types.Message) else m_or_call.answer("Бўш"))
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']}", callback_data=f"view_{p['_id']}")
    kb.adjust(2)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"pg_{page-1}"))
    if (page + 1) * 6 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"pg_{page+1}"))
    if nav: kb.row(*nav)
    if isinstance(m_or_call, types.Message): await m_or_call.answer("Маҳсулотлар:", reply_markup=kb.as_markup())
    else: await m_or_call.message.edit_text("Маҳсулотлар:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("pg_"))
async def user_shop_pagination(call: CallbackQuery): await shop_page_loader(call, int(call.data.split("_")[1]))

@dp.callback_query(F.data.startswith("view_"))
async def user_product_view(call: CallbackQuery):
    p = await get_product(call.data.split("_")[1])
    cap = f"📱 <b>{p['name']}</b>\n💰 {p['price']} сўм\n📝 {p['description']}\n📦 Омборда: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Саватга қўшиш", callback_data=f"cartadd_{p['_id']}")
    kb.button(text="🔙 Орқага", callback_data="pg_0")
    try: await call.message.answer_photo(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    except: await call.message.answer_document(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data.startswith("cartadd_"))
async def user_cart_add_qty(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("🔢 Нечта керак?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.input_qty)

@dp.message(UserState.input_qty)
async def user_cart_save(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам киритинг!")
    qty = int(m.text)
    d = await state.get_data()
    p = await get_product(d['pid'])
    if qty > p['stock']: return await m.answer(f"Омборда фақат {p['stock']} та қолган.")
    
    cart = d.get("cart", {})
    pid = str(p['_id'])
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty}
    
    await state.update_data(cart=cart)
    await m.answer("✅ Саватга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.set_state(None)

@dp.message(F.text == "🛒 Сават")
async def user_cart_view_handler(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart = d.get("cart", {})
    if not cart: return await m.answer("Сават бўш.")
    txt = "🛒 Саватдагилар:\n"
    total = sum(i['price'] * i['qty'] for i in cart.values())
    for i in cart.values(): txt += f"- {i['name']} x {i['qty']} = {i['price']*i['qty']} сўм\n"
    txt += f"\n💰 Жами: {total} сўм"
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Буюртма бериш", callback_data="user_checkout")
    kb.button(text="🗑 Тозалаш", callback_data="user_clear_cart")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "user_clear_cart")
async def user_cart_clear(call: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Сават тозаланди.")

@dp.callback_query(F.data == "user_checkout")
async def user_checkout_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📞 Телефон рақамингизни юборинг:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Юбориш", request_contact=True)]], resize_keyboard=True))
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def user_phone_capture(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number if m.contact else m.text)
    d = await state.get_data()
    cart = d.get("cart", {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    oid = await create_order(m.from_user.id, m.from_user.full_name, d['phone'], cart, total, "Нақд", "Етказиб бериш", "Йўқ", "Янги")
    for pid, i in cart.items(): await decrease_stock(pid, i['qty'])
    await m.answer(f"✅ Буюртма қабул қилинди! Чек ID: #{oid}", reply_markup=main_kb(m.from_user.id))
    for admin in ADMIN_IDS: await bot.send_message(admin, f"🚨 Янги буюртма: #{oid}")
    await state.update_data(cart={})
    await state.set_state(None)

# =====================================================================
# 11. ADMIN: SOZLAMALAR (OMBORNI TAHRIRLASH VA O'CHIRISH)
# =====================================================================

@dp.message(F.text == "⚙️ Созламалар")
async def admin_extra_settings(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Омборни таҳрирлаш", callback_data="edit_stock_list")
    kb.button(text="❌ Маҳсулотни ўчириш", callback_data="del_prod_list")
    kb.adjust(1)
    await m.answer("Созламалар:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "edit_stock_list")
async def admin_edit_stock_list(call: CallbackQuery):
    items = await get_all_products()
    kb = InlineKeyboardBuilder()
    for i in items: kb.button(text=f"{i['name']} ({i['stock']})", callback_data=f"est_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Миқдорни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("est_"))
async def admin_edit_stock_qty(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[1])
    await call.message.answer("Янги сонини ёзинг:")
    await state.set_state(AdminState.edit_stock_qty)

@dp.message(AdminState.edit_stock_qty)
async def admin_save_stock_qty(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    d = await state.get_data()
    await set_product_stock(d['pid'], int(m.text))
    await m.answer("✅ Янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "del_prod_list")
async def admin_del_prod_list(call: CallbackQuery):
    items = await get_all_products()
    kb = InlineKeyboardBuilder()
    for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"dprod_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган маҳсулот:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dprod_"))
async def admin_del_prod_exec(call: CallbackQuery):
    await delete_product(call.data.split("_")[1])
    await call.answer("Маҳсулот ўчирилди!")
    await admin_del_prod_list(call)

# =====================================================================
# 12. INFO & RUN
# =====================================================================

@dp.message(F.text == "ℹ️ Биз ҳақимизда")
async def about_handler(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Манзил: {i['address']}\n📞 Тел: {i['phone']}\nℹ️ {i['about']}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
