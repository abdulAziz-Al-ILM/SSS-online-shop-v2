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

# =====================================================================
# TIZIMNI SOZLASH
# =====================================================================
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================================================================
# STATES (HOLATLAR)
# =====================================================================

class AdminState(StatesGroup):
    photo = State()
    name = State()
    price = State()
    desc = State()
    stock = State()
    srv_name = State()
    srv_desc = State()
    loc_name = State()
    loc_address = State()
    loc_geo = State()
    ad_title = State()
    ad_text = State()
    ad_discount = State()
    info_phone = State()
    info_address = State()
    info_about = State()
    soc_ch = State()
    soc_ig = State()
    soc_wa = State()
    logo_photo = State()
    trailer_video = State()
    edit_stock_qty = State()

class UserState(StatesGroup):
    input_qty = State()
    phone = State()
    location = State()
    check_photo = State()

# =====================================================================
# KEYBOARDS (TUGMALAR)
# =====================================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_kb(user_id):
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
# ASOSIY HANDLERLAR
# =====================================================================

@dp.message(Command("start"))
async def start_handler(m: types.Message, state: FSMContext):
    await state.clear()
    if len(m.text.split()) > 1 and m.text.split()[1].startswith("order_"):
        pid = m.text.split()[1].replace("order_", "")
        p = await get_product(pid)
        if p:
            await state.update_data(pid=pid)
            await m.answer(f"📦 <b>{p['name']}</b> танланди.\nНечта керак? Рақам билан ёзинг:", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            await state.set_state(UserState.input_qty)
            return
    await m.answer(f"Салом, {m.from_user.full_name}! SSS Online Shop ботига хуш келибсиз.", reply_markup=main_kb(m.from_user.id))

# =====================================================================
# ADMIN: SAYT BOSHQARUVI (QO'SHISH)
# =====================================================================

@dp.message(F.text == "🛠 Хизмат")
async def admin_add_srv(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Янги хизмат номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.srv_name)

@dp.message(AdminState.srv_name)
async def admin_srv_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Хизмат ҳақида қисқача маълумот ёзинг:")
    await state.set_state(AdminState.srv_desc)

@dp.message(AdminState.srv_desc)
async def admin_srv_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_service(d['name'], m.text)
    await m.answer("✅ Хизмат сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "📍 Филиал")
async def admin_add_loc(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Филиал номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.loc_name)

@dp.message(AdminState.loc_name)
async def admin_loc_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Манзилни ёзинг:")
    await state.set_state(AdminState.loc_address)

@dp.message(AdminState.loc_address)
async def admin_loc_addr(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Локация юбориш", request_location=True)]], resize_keyboard=True)
    await m.answer("Энди пастдаги тугма орқали харитадан нуқтани юборинг:", reply_markup=kb)
    await state.set_state(AdminState.loc_geo)

@dp.message(AdminState.loc_geo, F.location)
async def admin_loc_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_location(d['name'], d['address'], m.location.latitude, m.location.longitude)
    await m.answer("✅ Филиал сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "🔥 Аксия")
async def admin_ad_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Қўшиш", callback_data="ad_add")
    kb.button(text="❌ Ўчириш", callback_data="dl_ad")
    kb.adjust(2)
    await m.answer("Аксияни бошқариш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "ad_add")
async def admin_add_ad_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Аксия сарлавҳаси:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.ad_title)
    await call.message.delete()

@dp.message(AdminState.ad_title)
async def admin_ad_title(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text)
    await m.answer("Аксия ҳақиda маълумот:")
    await state.set_state(AdminState.ad_text)

@dp.message(AdminState.ad_text)
async def admin_ad_text(m: types.Message, state: FSMContext):
    await state.update_data(text=m.text)
    await m.answer("Чегирма фоизи (фақат рақам):")
    await state.set_state(AdminState.ad_discount)

@dp.message(AdminState.ad_discount)
async def admin_ad_save(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    d = await state.get_data()
    await add_ad(d['title'], d['text'], m.text)
    await m.answer("✅ Аксия сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# MULTIMEDIA (LOGO & TRAILER)
# =====================================================================

@dp.message(F.text == "🖼 Логотип")
async def admin_logo(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Янги логотип учун расm юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.logo_photo)

@dp.message(AdminState.logo_photo, F.photo)
async def admin_logo_save(m: types.Message, state: FSMContext):
    await set_logo(m.photo[-1].file_id)
    await m.answer("✅ Логотип янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "📹 Трейлер юклаш")
async def admin_trailer(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📹 Видео-трейлер юборинг (MP4 ёки файл):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.trailer_video)

@dp.message(AdminState.trailer_video, (F.video | F.document))
async def admin_trailer_save(m: types.Message, state: FSMContext):
    fid = m.video.file_id if m.video else m.document.file_id
    await set_trailer(fid)
    await m.answer("✅ Видео-трейлер янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# INFO & TARMOQLAR
# =====================================================================

@dp.message(F.text == "⚙️ Тармоқлар ва инфо")
async def admin_info_manage(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("Сайтда чиқадиган телефон рақам:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.info_phone)

@dp.message(AdminState.info_phone)
async def admin_info_ph(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    await m.answer("Асосий манзилни ёзинг:")
    await state.set_state(AdminState.info_address)

@dp.message(AdminState.info_address)
async def admin_info_addr(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    await m.answer("Фирма ҳақида қисқача таъриф:")
    await state.set_state(AdminState.info_about)

@dp.message(AdminState.info_about)
async def admin_info_ab(m: types.Message, state: FSMContext):
    await state.update_data(about=m.text)
    await m.answer("Telegram канал ҳаволаси:")
    await state.set_state(AdminState.soc_ch)

@dp.message(AdminState.soc_ch)
async def admin_soc_ch(m: types.Message, state: FSMContext):
    await state.update_data(ch=m.text)
    await m.answer("Instagram ҳаволаси:")
    await state.set_state(AdminState.soc_ig)

@dp.message(AdminState.soc_ig)
async def admin_soc_ig(m: types.Message, state: FSMContext):
    await state.update_data(ig=m.text)
    await m.answer("WhatsApp ҳаволаси:")
    await state.set_state(AdminState.soc_wa)

@dp.message(AdminState.soc_wa)
async def admin_info_final(m: types.Message, state: FSMContext):
    d = await state.get_data()
    bot_info = await bot.get_me()
    await set_shop_info(d['address'], d['phone'], d['about'])
    await set_social_links(f"https://t.me/{bot_info.username}", d['ig'], m.text, d['ch'])
    await m.answer("✅ Барча маълумотлар янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# MAHSULOT QO'SHISH, BUYURTMA, DO'KON... (QOLGAN HAMMASI)
# =====================================================================

@dp.message(F.text == "➕ Маҳсулот")
async def admin_add_p(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Маҳсулот расмини юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.photo)

@dp.message(AdminState.photo, F.photo)
async def admin_p_photo(m: types.Message, state: FSMContext):
    await state.update_data(file_id=m.photo[-1].file_id)
    await m.answer("Маҳсулот номи:")
    await state.set_state(AdminState.name)

@dp.message(AdminState.name)
async def admin_p_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Нархи (фақат рақам):")
    await state.set_state(AdminState.price)

@dp.message(AdminState.price)
async def admin_p_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    await state.update_data(price=int(m.text))
    await m.answer("Тавсифи:")
    await state.set_state(AdminState.desc)

@dp.message(AdminState.desc)
async def admin_p_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("Омбордаги сони (рақам):")
    await state.set_state(AdminState.stock)

@dp.message(AdminState.stock)
async def admin_p_save(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам ёзинг!")
    d = await state.get_data()
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'])
    await m.answer("✅ Маҳсулот қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "📦 Буюртмалар")
async def admin_orders(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    for label, code in [("🆕 Янги", "new"), ("🔄 Ишда", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпилган", "delivered")]:
        kb.button(text=label, callback_data=f"adm_ord_{code}")
    kb.adjust(2)
    await m.answer("Буюртмалар ҳолати:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("adm_ord_"))
async def admin_ord_list(call: CallbackQuery):
    st = call.data.split("_")[2]
    orders = await get_orders_by_status(st)
    if not orders: return await call.answer("Бўш", show_alert=True)
    kb = InlineKeyboardBuilder()
    for o in orders: kb.button(text=f"#{o['order_id']} | {o['total_price']}", callback_data=f"dt_ord_{o['order_id']}")
    kb.adjust(1)
    kb.button(text="🔙 Орқага", callback_data="back_adm_orders")
    await call.message.edit_text(f"Ҳолат: {st}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "back_adm_orders")
async def admin_ord_back(call: CallbackQuery): await admin_orders(call.message)

@dp.callback_query(F.data.startswith("dt_ord_"))
async def admin_ord_detail(call: CallbackQuery):
    o = await get_order_by_id(call.data.split("_")[2])
    txt = f"🆔 <b>Чек: #{o['order_id']}</b>\n👤 {o['user_name']}\n📞 {o['phone']}\n💰 {o['total_price']} сўм\n📊 Ҳолати: {o['status']}"
    kb = InlineKeyboardBuilder()
    for label, st in [("🔄 Ишда", "processing"), ("✅ Тайёр", "ready"), ("🚚 Йўлда", "shipped"), ("🏁 Ёпиш", "delivered"), ("❌ Рад этиш", "canceled")]:
        kb.button(text=label, callback_data=f"u_st_{o['order_id']}_{st}")
    kb.adjust(2)
    kb.button(text="🔙 Орқага", callback_data=f"adm_ord_{o['status']}")
    await call.message.edit_text(txt, parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("u_st_"))
async def admin_ord_save_st(call: CallbackQuery):
    _, _, oid, st = call.data.split("_")
    await update_order_status(oid, st)
    await call.answer("Янгиланди!")
    await admin_ord_detail(call)

@dp.message(F.text == "🛍 Дўкон")
async def user_shop(m: types.Message): await user_shop_page(m, 0)

async def user_shop_page(m_or_call, page):
    prods, total = await get_products_paginated(page, 6)
    if not prods: return await (m_or_call.answer("Маҳсулот йўқ") if isinstance(m_or_call, types.Message) else m_or_call.answer("Бўш"))
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']}", callback_data=f"u_v_{p['_id']}")
    kb.adjust(2)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"u_p_{page-1}"))
    if (page + 1) * 6 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"u_p_{page+1}"))
    if nav: kb.row(*nav)
    if isinstance(m_or_call, types.Message): await m_or_call.answer("Маҳсулотларимиз:", reply_markup=kb.as_markup())
    else: await m_or_call.message.edit_text("Маҳсулотларимиз:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("u_p_"))
async def user_shop_pg(call: CallbackQuery): await user_shop_page(call, int(call.data.split("_")[2]))

@dp.callback_query(F.data.startswith("u_v_"))
async def user_p_view(call: CallbackQuery):
    p = await get_product(call.data.split("_")[2])
    cap = f"📱 <b>{p['name']}</b>\n💰 {p['price']} сўм\n📝 {p['description']}\n📦 Омборда: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Саватга қўшиш", callback_data=f"u_a_{p['_id']}")
    kb.button(text="🔙 Орқага", callback_data="u_p_0")
    try: await call.message.answer_photo(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    except: await call.message.answer_document(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data.startswith("u_a_"))
async def user_cart_qty(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[2])
    await call.message.answer("Нечта керак? Рақам билан ёзинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.input_qty)

@dp.message(UserState.input_qty)
async def user_cart_save(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам киритинг!")
    qty = int(m.text)
    d = await state.get_data()
    p = await get_product(d['pid'])
    if qty > p['stock']: return await m.answer(f"Кечирасиз, фақат {p['stock']} та бор.")
    cart = d.get("cart", {})
    pid = str(p['_id'])
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty}
    await state.update_data(cart=cart)
    await m.answer("✅ Саватга қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.set_state(None)

@dp.message(F.text == "🛒 Сават")
async def user_cart_show(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart = d.get("cart", {})
    if not cart: return await m.answer("Саватингиз бўш.")
    txt = "🛒 Саватдагилар:\n"
    total = sum(i['price'] * i['qty'] for i in cart.values())
    for i in cart.values(): txt += f"- {i['name']} x {i['qty']} = {i['price']*i['qty']} сўм\n"
    txt += f"\n💰 Жами: {total} сўм"
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Буюртма бериш", callback_data="u_checkout")
    kb.button(text="🗑 Тозалаш", callback_data="u_clear")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "u_clear")
async def user_cart_clr(call: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Сават тозаланди.")

@dp.callback_query(F.data == "u_checkout")
async def user_checkout_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Телефон рақамингизни юборинг:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Юбориш", request_contact=True)]], resize_keyboard=True))
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def user_phone_get(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number if m.contact else m.text)
    d = await state.get_data()
    cart = d.get("cart", {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    oid = await create_order(m.from_user.id, m.from_user.full_name, d['phone'], cart, total, "Нақд", "Етказиб", "Йўқ", "Янги")
    for pid, i in cart.items(): await decrease_stock(pid, i['qty'])
    await m.answer(f"✅ Буюртма қабул қилинди! Чек ID: #{oid}", reply_markup=main_kb(m.from_user.id))
    for a in ADMIN_IDS: await bot.send_message(a, f"🚨 Янги буюртма: #{oid}")
    await state.update_data(cart={})
    await state.set_state(None)

@dp.message(F.text == "🗑 Маълуmot ўчириш")
async def admin_delete_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="🛠 Хизмат", callback_data="dl_srv")
    kb.button(text="📍 Филиал", callback_data="dl_loc")
    kb.button(text="🔥 Аксия", callback_data="dl_ad")
    kb.adjust(1)
    await m.answer("Нимани ўчирмоқчисиз?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dl_"))
async def admin_del_list(call: CallbackQuery):
    t = call.data.split("_")[1]
    kb = InlineKeyboardBuilder()
    if t == "srv":
        items = await get_all_services()
        for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"ex_dsrv_{i['_id']}")
    elif t == "loc":
        items = await get_all_locations()
        for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"ex_dloc_{i['_id']}")
    elif t == "ad":
        items = await get_all_ads()
        for i in items: kb.button(text=f"❌ {i['title']}", callback_data=f"ex_dad_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ex_d"))
async def admin_del_exec(call: CallbackQuery):
    parts = call.data.split("_")
    p = parts[1]    # 'dsrv', 'dloc' yoki 'dad'
    oid = parts[2]  # Bazadagi haqiqiy ID
    
    if p == "dsrv": 
        await delete_service(oid)
    elif p == "dloc": 
        await delete_location(oid)
    elif p == "dad": 
        await delete_ad(oid)
        
    await call.answer("✅ Муваффақиятли ўчирилди!")
    await call.message.delete()

@dp.message(F.text == "⚙️ Созламалар")
async def admin_extra(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Омбор", callback_data="es_l")
    kb.button(text="❌ Маҳсулотни ўчириш", callback_data="dp_l")
    kb.adjust(1)
    await m.answer("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "es_l")
async def admin_es_list(call: CallbackQuery):
    items = await get_all_products()
    kb = InlineKeyboardBuilder()
    for i in items: kb.button(text=f"{i['name']} ({i['stock']})", callback_data=f"es_v_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("es_v_"))
async def admin_es_val(call: CallbackQuery, state: FSMContext):
    await state.update_data(pid=call.data.split("_")[2])
    await call.message.answer("Янги сонини ёзинг:")
    await state.set_state(AdminState.edit_stock_qty)

@dp.message(AdminState.edit_stock_qty)
async def admin_es_save(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Рақам!")
    d = await state.get_data()
    await set_product_stock(d['pid'], int(m.text))
    await m.answer("✅ Янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "dp_l")
async def admin_dp_list(call: CallbackQuery):
    items = await get_all_products()
    kb = InlineKeyboardBuilder()
    for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"dp_e_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган маҳсулот:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dp_e_"))
async def admin_dp_exec(call: CallbackQuery):
    await delete_product(call.data.split("_")[2])
    await call.answer("Ўчирилди!")
    await admin_dp_list(call)

@dp.message(F.text == "ℹ️ Биз ҳақимизда")
async def about_handler(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Манзил: {i['address']}\n📞 Тел: {i['phone']}\nℹ️ {i['about']}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
