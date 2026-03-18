import asyncio
import logging
import sys
import math
import pytz
from datetime import datetime
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

# =====================================================================
# TIZIMNI SOZLASH VA MATEMATIKA
# =====================================================================
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_delivery_time(lang):
    tz = pytz.timezone('Asia/Bishkek')
    now = datetime.now(tz)
    if now.hour < 13:
        return {"uz": "бугун тушдан кейин", "ru": "сегодня после обеда", "kg": "бүгүн түштөн кийин"}.get(lang, "бугун тушдан кейин")
    else:
        return {"uz": "эртага тушгача", "ru": "завтра до обеда", "kg": "эртең түшкө чейин"}.get(lang, "эртага тушгача")

# =====================================================================
# STATES (HOLATLAR)
# =====================================================================

class AdminState(StatesGroup):
    category = State()
    delivery_size = State()
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
    base_name = State()
    base_geo = State()
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
    edit_stock_qty = State()

class UserState(StatesGroup):
    lang = State()
    input_qty = State()
    delivery_type = State()
    upsell_loc = State()
    location = State()
    phone = State()
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
        rows.append([KeyboardButton(text="🔥 Аксия"), KeyboardButton(text="🏢 Базалар")])
        rows.append([KeyboardButton(text="⚙️ Тармоқлар ва инфо"), KeyboardButton(text="🖼 Логотип")])
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
# ADMIN: SAYT BOSHQARUVI VA O'CHIRISH
# =====================================================================

@dp.message(F.text == "🛠 Хизмат")
async def admin_srv_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Қўшиш", callback_data="srv_add")
    kb.button(text="❌ Ўчириш", callback_data="dl_srv")
    kb.adjust(2)
    await m.answer("Хизматни бошқариш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "srv_add")
async def admin_add_srv_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Янги хизмат номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.srv_name)
    await call.message.delete()

@dp.message(AdminState.srv_name)
async def admin_srv_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Хизмат ҳақида қисқача маълумот ёзинг:")    
    await state.set_state(AdminState.srv_desc)

@dp.message(AdminState.srv_desc)
async def admin_srv_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_service(d['name'], m.text)
    await m.answer("✅ Хизмат қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "📍 Филиал")
async def admin_loc_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Қўшиш", callback_data="loc_add")
    kb.button(text="❌ Ўчириш", callback_data="dl_loc")
    kb.adjust(2)
    await m.answer("Филиални бошқариш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "loc_add")
async def admin_add_loc_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Филиал номи:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.loc_name)
    await call.message.delete()

@dp.message(AdminState.loc_name)
async def admin_loc_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Манзилни ёзинг:")
    await state.set_state(AdminState.loc_address)

@dp.message(AdminState.loc_address)
async def admin_loc_addr(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Локация юбориш", request_location=True)]], resize_keyboard=True)
    await m.answer("Харитадан нуқтани юборинг:", reply_markup=kb)
    await state.set_state(AdminState.loc_geo)

@dp.message(AdminState.loc_geo, F.location)
async def admin_loc_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_location(d['name'], d['address'], m.location.latitude, m.location.longitude)
    await m.answer("✅ Филиал қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "🏢 Базалар")
async def admin_base_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Қўшиш", callback_data="base_add")
    kb.button(text="❌ Ўчириш", callback_data="dl_base")
    kb.adjust(2)
    await m.answer("Базаларни бошқариш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "base_add")
async def admin_add_base_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("База номини ёзинг (мас: Марказий омбор):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.base_name)
    await call.message.delete()

@dp.message(AdminState.base_name)
async def admin_base_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📍 Локация юбориш", request_location=True)]], resize_keyboard=True)
    await m.answer("Базанинг харитадаги локациясини юборинг:", reply_markup=kb)
    await state.set_state(AdminState.base_geo)

@dp.message(AdminState.base_geo, F.location)
async def admin_base_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    await add_base(d['name'], m.location.latitude, m.location.longitude)
    await m.answer("✅ База қўшилди!", reply_markup=main_kb(m.from_user.id))
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
    await m.answer("Аксия ҳақида маълумот:")
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
    await m.answer("✅ Аксия қўшилди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# --- O'CHIRISH IJROSI (HAMMASI SHU YERDA) ---
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
    elif t == "base":
        items = await get_all_bases()
        for i in items: kb.button(text=f"❌ {i['name']}", callback_data=f"ex_dbase_{i['_id']}")
    kb.adjust(1)
    await call.message.edit_text("Ўчириладиган элементни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ex_d"))
async def admin_del_exec(call: CallbackQuery):
    parts = call.data.split("_")
    p = parts[1]
    oid = parts[2]
    if p == "dsrv": await delete_service(oid)
    elif p == "dloc": await delete_location(oid)
    elif p == "dad": await delete_ad(oid)
    elif p == "dbase": await delete_base(oid)
    await call.answer("✅ Ўчирилди!", show_alert=True)
    await call.message.delete()

# =====================================================================
# INFO, MAHSULOT QO'SHISH, BUYURTMALAR
# =====================================================================

@dp.message(F.text == "⚙️ Тармоқлар ва инфо")
async def admin_info_manage(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    for txt, cd in [("📞 Телефон", "edit_info_phone"), ("📍 Манзил", "edit_info_address"), ("ℹ️ Биз ҳақида", "edit_info_about"), ("📢 ТГ Канал", "edit_soc_ch"), ("📸 Instagram", "edit_soc_ig"), ("💬 WhatsApp", "edit_soc_wa")]:
        kb.button(text=txt, callback_data=cd)
    kb.adjust(2)
    await m.answer("Қайси маълумотни ўзгартирмоқчисиз?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("edit_"))
async def admin_edit_info_start(call: CallbackQuery, state: FSMContext):
    field = call.data.replace("edit_", "")
    prompts = {
        "info_phone": ("📞 Янги телефон рақамни ёзинг:", AdminState.info_phone),
        "info_address": ("📍 Янги манзилни ёзинг:", AdminState.info_address),
        "info_about": ("ℹ️ Фирма ҳақида янги маълумот ёзинг:", AdminState.info_about),
        "soc_ch": ("📢 Янги Telegram канал ҳаволасини ёзинг:", AdminState.soc_ch),
        "soc_ig": ("📸 Янги Instagram ҳаволасини ёзинг:", AdminState.soc_ig),
        "soc_wa": ("💬 Янги WhatsApp ҳаволасини ёзинг:", AdminState.soc_wa)
    }
    await call.message.answer(prompts[field][0], reply_markup=ReplyKeyboardRemove())
    await state.set_state(prompts[field][1])
    await call.message.delete()

@dp.message(StateFilter(AdminState.info_phone, AdminState.info_address, AdminState.info_about, AdminState.soc_ch, AdminState.soc_ig, AdminState.soc_wa))
async def admin_info_save_single(m: types.Message, state: FSMContext):
    st = await state.get_state()
    info = await get_combined_info()
    address, phone, about = info.get("address", ""), info.get("phone", ""), info.get("about", "")
    ch, ig, wa = info.get("telegram_channel", ""), info.get("instagram", ""), info.get("whatsapp", "")
    tg = f"https://t.me/{(await bot.get_me()).username}"

    if st == AdminState.info_phone.state: phone = m.text
    elif st == AdminState.info_address.state: address = m.text
    elif st == AdminState.info_about.state: about = m.text
    elif st == AdminState.soc_ch.state: ch = m.text
    elif st == AdminState.soc_ig.state: ig = m.text
    elif st == AdminState.soc_wa.state: wa = m.text

    await set_shop_info(address, phone, about)
    await set_social_links(tg, ig, wa, ch)
    await m.answer("✅ Маълумот янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "🖼 Логотип")
async def admin_logo(m: types.Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await m.answer("📸 Янги логотип учун расм юборинг:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.logo_photo)

@dp.message(AdminState.logo_photo, F.photo)
async def admin_logo_save(m: types.Message, state: FSMContext):
    await set_logo(m.photo[-1].file_id)
    await m.answer("✅ Логотип янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

@dp.message(F.text == "➕ Маҳсулот")
async def admin_product_menu(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Қўшиш", callback_data="prod_add")
    kb.button(text="❌ Ўчириш", callback_data="dp_l")
    kb.button(text="📦 Омборни таҳрирлаш", callback_data="es_l")
    kb.adjust(1)
    await m.answer("Маҳсулотларни бошқариш:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "prod_add")
async def admin_add_p_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📁 Маҳсулот категориясини ёзинг (мас: Сантехника, Электр):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.category)
    await call.message.delete()

@dp.message(AdminState.category)
async def admin_p_category(m: types.Message, state: FSMContext):
    await state.update_data(category=m.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚕 Такси"), KeyboardButton(text="🚛 Лабо")]], resize_keyboard=True)
    await m.answer("Транспорт турини танланг:", reply_markup=kb)
    await state.set_state(AdminState.delivery_size)

@dp.message(AdminState.delivery_size)
async def admin_p_delsize(m: types.Message, state: FSMContext):
    if m.text not in ["🚕 Такси", "🚛 Лабо"]: return await m.answer("Тугмани босинг!")
    await state.update_data(delivery_size=m.text)
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
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'], d['category'], d['delivery_size'])
    await m.answer("✅ Маҳсулот қўшилди!", reply_markup=main_kb(m.from_user.id))
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
    txt = f"🆔 <b>Чек: #{o['order_id']}</b>\n👤 {o['user_name']}\n📞 {o['phone']}\n💰 {o['total_price']} сом\n📊 Ҳолати: {o['status']}"
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

# =====================================================================
# FOYDALANUVCHI: DO'KON VA SAVAT
# =====================================================================

@dp.message(F.text == "ℹ️ Биз ҳақимизда")
async def about_handler(m: types.Message):
    i = await get_shop_info()
    await m.answer(f"📍 Манзил: {i['address']}\n📞 Тел: {i['phone']}\nℹ️ {i['about']}")

@dp.message(F.text == "🛍 Дўкон")
async def user_shop(m: types.Message):
    cats = await get_categories()
    if not cats: return await m.answer("Маҳсулот йўқ")
    kb = InlineKeyboardBuilder()
    for c in cats: kb.button(text=c, callback_data=f"cat_{c[:20]}") 
    kb.adjust(2)
    await m.answer("📁 Категорияни танланг:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("cat_"))
async def user_shop_cat(call: CallbackQuery, state: FSMContext):
    cat = call.data.replace("cat_", "")
    await state.update_data(current_cat=cat)
    await user_shop_page(call, cat, 0)

@dp.callback_query(F.data.startswith("u_p_"))
async def user_shop_pg(call: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    cat = d.get("current_cat")
    if not cat: return await call.answer("Хатолик: қайта киринг", show_alert=True)
    await user_shop_page(call, cat, int(call.data.split("_")[2]))

async def user_shop_page(m_or_call, cat, page):
    prods, total = await get_products_by_category_paginated(cat, page, 6)
    if not prods: 
        return await (m_or_call.answer("Бўш") if isinstance(m_or_call, types.Message) else m_or_call.answer("Бўш", show_alert=True))
    kb = InlineKeyboardBuilder()
    for p in prods: kb.button(text=f"{p['name']}", callback_data=f"u_v_{p['_id']}")
    kb.adjust(2)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"u_p_{page-1}"))
    if (page + 1) * 6 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"u_p_{page+1}"))
    nav.append(InlineKeyboardButton(text="🔙 Каталог", callback_data="back_to_cats"))
    if nav: kb.row(*nav)
    text = f"📁 Категория: <b>{cat}</b>\nМаҳсулотларимиз:"
    if isinstance(m_or_call, types.Message): await m_or_call.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else: await m_or_call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "back_to_cats")
async def back_to_categories(call: CallbackQuery):
    await user_shop(call.message)
    await call.message.delete()

@dp.callback_query(F.data.startswith("u_v_"))
async def user_p_view(call: CallbackQuery):
    p = await get_product(call.data.split("_")[2])
    cap = f"📱 <b>{p['name']}</b>\n💰 {p['price']} сом\n📝 {p['description']}\n📦 Омборда: {p['stock']}"
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
    
    del_size = p.get('delivery_size', '🚕 Такси') 
    if pid in cart: cart[pid]['qty'] += qty
    else: cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': qty, 'delivery_size': del_size}
    
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
    for i in cart.values(): txt += f"- {i['name']} x {i['qty']} = {i['price']*i['qty']} сом\n"
    txt += f"\n💰 Жами: {total} сом"
    kb = InlineKeyboardBuilder()
    kb.button(text="🏁 Буюртма бериш", callback_data="u_checkout")
    kb.button(text="🗑 Тозалаш", callback_data="u_clear")
    await m.answer(txt, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "u_clear")
async def user_cart_clr(call: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    await call.message.edit_text("Сават тозаланди.")

# =====================================================================
# CHECKOUT MANTIQI (3 TIL, 20% CHEGIRMA, 10% ZAKALAT, MULTI-BASE)
# =====================================================================

@dp.callback_query(F.data == "u_checkout")
async def user_checkout_start(call: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 Ўзбекча", callback_data="lang_uz")
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇰🇬 Кыргызча", callback_data="lang_kg")
    await call.message.answer("Буюртмани расмийлаштириш учун тилни танланг:\nВыберите язык:\nТилди тандаңыз:", reply_markup=kb.as_markup())
    await call.message.delete()

@dp.callback_query(F.data.startswith("lang_"))
async def set_user_language(call: CallbackQuery, state: FSMContext):
    lang = call.data.split("_")[1]
    await state.update_data(lang=lang)
    
    texts = {
        "uz": ["🚚 Етказиб бериш", "🚶‍♂️ Ўзим олиб кетаман", "❌ Бекор қилиш", "Қабул қилиш усулини танланг:"],
        "ru": ["🚚 Доставка", "🚶‍♂️ Самовывоз", "❌ Отмена", "Выберите способ получения:"],
        "kg": ["🚚 Жеткирүү", "🚶‍♂️ Өзүм алып кетем", "❌ Жокко чыгаруу", "Алуу ыкмасын тандаңыз:"]
    }
    t = texts[lang]
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t[0]), KeyboardButton(text=t[1])], [KeyboardButton(text=t[2])]], resize_keyboard=True)
    await call.message.answer(t[3], reply_markup=kb)
    await state.set_state(UserState.delivery_type)
    await call.message.delete()

@dp.message(UserState.delivery_type)
async def user_delivery_get(m: types.Message, state: FSMContext):
    d = await state.get_data()
    lang = d.get('lang', 'uz')

    cancel_btns = ["❌ Бекор қилиш", "❌ Отмена", "❌ Жокко чыгаруу"]
    delivery_btns = ["🚚 Етказиб бериш", "🚚 Доставка", "🚚 Жеткирүү"]
    pickup_btns = ["🚶‍♂️ Ўзим олиб кетаман", "🚶‍♂️ Самовывоз", "🚶‍♂️ Өзүм алып кетем"]

    if m.text in cancel_btns:
        await state.set_state(None)
        return await m.answer("Бекор қилинди / Отменено / Жокко чыгарылды.", reply_markup=main_kb(m.from_user.id))

    if m.text in delivery_btns:
        await state.update_data(delivery_type="Етказиб бериш")
        prompt = {
            "uz": "📍 Йўл кирани ҳисоблаш учун юк БОРАДИГАН манзил локациясини юборинг:",
            "ru": "📍 Отправьте локацию КУДА нужно доставить груз:",
            "kg": "📍 Жол кирени эсептөө үчүн жүк БАРА ТУРГАН даректин локациясын жөнөтүңүз:"
        }[lang]
        loc_btn = {"uz":"📍 Локация юбориш","ru":"📍 Отправить локацию","kg":"📍 Локация жөнөтүү"}[lang]
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=loc_btn, request_location=True)], [KeyboardButton(text=cancel_btns[0])]], resize_keyboard=True)
        await m.answer(prompt, reply_markup=kb)
        await state.set_state(UserState.location)

    elif m.text in pickup_btns:
        await state.update_data(delivery_type="Ўзи олиб кетади")
        prompt = {
            "uz": "Вақтингиз ва пулингизни тежанг! Локациянгизни ташланг, балки биз олиб борганимиз ўзингиз келганингиздан арзонроқ тушар? Етказиб беришга 20% чегирмамиз бор! 👇",
            "ru": "Сэкономьте время и деньги! Скиньте локацию, возможно наша доставка со скидкой 20% выйдет дешевле! 👇",
            "kg": "Убактыңызды жана акчаңызды үнөмдөңүз! Локацияңызды таштаңыз, балким биздин 20% арзандатуу менен жеткирүүбүз арзаныраак түшөр! 👇"
        }[lang]
        btn_no = {"uz":"Йўқ, ўзим бораман","ru":"Нет, приеду сам","kg":"Жок, өзүм барам"}[lang]
        loc_btn = {"uz":"📍 Локация юбориш","ru":"📍 Отправить локацию","kg":"📍 Локация жөнөтүү"}[lang]
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=loc_btn, request_location=True)], [KeyboardButton(text=btn_no)]], resize_keyboard=True)
        await m.answer(prompt, reply_markup=kb)
        await state.set_state(UserState.upsell_loc)

@dp.message(UserState.upsell_loc)
async def handle_upsell(m: types.Message, state: FSMContext):
    d = await state.get_data()
    lang = d.get('lang', 'uz')
    no_btns = ["Йўқ, ўзим бораман", "Нет, приеду сам", "Жок, өзүм барам"]

    if m.text in no_btns:
        await state.update_data(location="Базадан олиб кетади", delivery_price=0, distance=0)
        prompt = {"uz":"Рақамингизни юборинг:","ru":"Отправьте ваш номер:","kg":"Номериңизди жөнөтүңүз:"}[lang]
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text={"uz":"📱 Рақам","ru":"📱 Номер","kg":"📱 Номер"}[lang], request_contact=True)]], resize_keyboard=True)
        await m.answer(prompt, reply_markup=kb)
        await state.set_state(UserState.phone)
        return

    if m.location:
        await state.update_data(delivery_type="Етказиб бериш")
        await user_location_get(m, state)

@dp.message(UserState.location)
async def user_location_get(m: types.Message, state: FSMContext):
    d = await state.get_data()
    lang = d.get('lang', 'uz')
    cart = d.get("cart", {})
    cart_total = sum(i['price'] * i['qty'] for i in cart.values())

    vehicle = "🚕 Такси"
    for item in cart.values():
        if item.get("delivery_size") == "🚛 Лабо":
            vehicle = "🚛 Лабо/Портер"
            break

    await state.update_data(vehicle_type=vehicle)

    if not m.location:
        return await m.answer({"uz":"Илтимос, харитадан локация юборинг.","ru":"Пожалуйста, отправьте локацию.","kg":"Сураныч, локация жөнөтүңүз."}[lang])

    bases = await get_all_bases()
    if not bases:
        return await m.answer({"uz":"❌ Тизимда ҳеч қандай база киритилмаган. Админга хабар беринг.","ru":"❌ В системе нет баз. Сообщите админу.","kg":"❌ Базалар киргизилген эмес. Админге билдириңиз."}[lang])

    min_dist = float('inf')
    closest_base = "Номаълум"
    for base in bases:
        dist = calculate_distance(base['lat'], base['lon'], m.location.latitude, m.location.longitude)
        if dist < min_dist:
            min_dist = dist
            closest_base = base['name']

    distance_km = min_dist

    if distance_km > 50:
        return await m.answer({"uz":"❌ 50 км дан узоққа элтиб бермаймиз. Ёки сизга яқин база йўқ.","ru":"❌ Доставка только до 50 км от ближайшей базы.","kg":"❌ Эң жакын базадан 50 кмге чейин гана жеткиребиз."}[lang])

    base_price = 0
    if vehicle == "🚕 Такси":
        if distance_km > 30:
            return await m.answer({"uz":"❌ Такси фақат 30 км гача.","ru":"❌ Такси только до 30 км.","kg":"❌ Такси 30 кмге чейин."}[lang])
        if cart_total > 50000: base_price = max(0, distance_km - 10) * 200
        else: base_price = distance_km * 200
    else:
        base_price = 500 + (distance_km * 2 * 50)

    base_price = round(base_price, -1)
    discounted_price = round(base_price * 0.8, -1) 

    await state.update_data(location=f"{m.location.latitude},{m.location.longitude}", delivery_price=discounted_price, distance=round(distance_km, 1), closest_base=closest_base)

    time_text = get_delivery_time(lang)

    info = {
        "uz": f"⏱ Етказиш вақти: <b>{time_text}</b>\n🏢 Сизга энг яқин омбор: <b>{closest_base}</b>\n🚙 Транспорт: <b>{vehicle}</b>\n📏 Масофа: <b>{round(distance_km,1)} км</b>\n💸 Йўл кира: ~{base_price}~ эмас, 20% чегирма билан <b>{int(discounted_price)} сом</b>!\n\nТелефон рақамингизни юборинг:",
        "ru": f"⏱ Время: <b>{time_text}</b>\n🏢 Ближайший склад: <b>{closest_base}</b>\n🚙 Авто: <b>{vehicle}</b>\n📏 Дистанция: <b>{round(distance_km,1)} км</b>\n💸 Доставка: вместо ~{base_price}~ со скидкой 20% <b>{int(discounted_price)} сом</b>!\n\nОтправьте номер:",
        "kg": f"⏱ Жеткирүү убактысы: <b>{time_text}</b>\n🏢 Эң жакын кампа: <b>{closest_base}</b>\n🚙 Унаа: <b>{vehicle}</b>\n📏 Аралык: <b>{round(distance_km,1)} км</b>\n💸 Жол кире: ~{base_price}~ эмес, 20% арзандатуу менен <b>{int(discounted_price)} сом</b>!\n\nНомериңизди жөнөтүңүз:"
    }[lang]

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text={"uz":"📱 Рақам","ru":"📱 Номер","kg":"📱 Номер"}[lang], request_contact=True)]], resize_keyboard=True)
    await m.answer(info, parse_mode="HTML", reply_markup=kb)
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def user_phone_get(m: types.Message, state: FSMContext):
    phone = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=phone)
    d = await state.get_data()
    lang = d.get('lang', 'uz')

    cart_total = sum(i['price'] * i['qty'] for i in d.get("cart", {}).values())
    delivery_price = d.get('delivery_price', 0)
    final_total = cart_total + delivery_price

    advance = round(final_total * 0.1, -1)
    remaining = final_total - advance

    msg = {
        "uz": f"💳 <b>10% Олдиндан Тўлов (Закалат)</b>\n\n📦 Маҳсулотлар: {cart_total} сом\n🚕 Йўл кира: {delivery_price} сом\n💰 ЖАМИ: <b>{int(final_total)} сом</b>\n\nТасдиқлаш учун 10% закалат: <b>{int(advance)} сом</b> тўланг.\n\n💳 Карта: <b>{CARD_NUMBER}</b>\n\n<i>Қолган {int(remaining)} сом юк етиб боргач ҳайдовчига тўланади.</i>\n\n📸 Тўлов чекини (расм) шу ерга юборинг:",
        "ru": f"💳 <b>Предоплата 10%</b>\n\n📦 Товары: {cart_total} сом\n🚕 Доставка: {delivery_price} сом\n💰 ИТОГО: <b>{int(final_total)} сом</b>\n\nДля подтверждения оплатите 10%: <b>{int(advance)} сом</b>.\n\n💳 Карта: <b>{CARD_NUMBER}</b>\n\n<i>Остаток {int(remaining)} сом оплачивается водителю при получении.</i>\n\n📸 Отправьте фото чека:",
        "kg": f"💳 <b>10% Алдын ала төлөө</b>\n\n📦 Товарлар: {cart_total} сом\n🚕 Жол кире: {delivery_price} сом\n💰 БААРДЫГЫ: <b>{int(final_total)} сом</b>\n\nТастыктоо үчүн 10% төлөңүз: <b>{int(advance)} сом</b>.\n\n💳 Карта: <b>{CARD_NUMBER}</b>\n\n<i>Калган {int(remaining)} сом жүк келгенде айдоочуга төлөнөт.</i>\n\n📸 Чектин сүрөтүн жөнөтүңүз:"
    }[lang]

    await m.answer(msg, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.check_photo)

@dp.message(UserState.check_photo, F.photo)
async def finish_order(m: types.Message, state: FSMContext):
    d = await state.get_data()
    lang = d.get('lang', 'uz')
    
    check_file_id = m.photo[-1].file_id
    cart = d.get("cart", {})
    cart_total = sum(i['price'] * i['qty'] for i in cart.values())
    delivery_price = d.get('delivery_price', 0)
    final_total = cart_total + delivery_price
    advance = round(final_total * 0.1, -1)
    
    delivery = d.get('delivery_type', 'Номаълум')
    vehicle = d.get('vehicle_type', 'Йўқ')
    location = d.get('location', 'Номаълум')
    closest_base = d.get('closest_base', 'Номаълум')
    phone = d.get('phone', 'Номаълум')
    
    oid = await create_order(m.from_user.id, m.from_user.full_name, phone, cart, final_total, "Карта орқали 10%", delivery, location, f"Тўланди: {advance} сом | Йўл: {delivery_price} | База: {closest_base} | Чек: {check_file_id}")
    
    for pid, i in cart.items(): await decrease_stock(pid, i['qty'])
    
    success_msg = {
        "uz": f"✅ Буюртма тасдиқланди! Чек ID: #{oid}\n{get_delivery_time('uz')} кутинг.",
        "ru": f"✅ Заказ подтвержден! ID чека: #{oid}\nОжидайте {get_delivery_time('ru')}.",
        "kg": f"✅ Буйрутма тастыкталды! Чек ID: #{oid}\n{get_delivery_time('kg')} күтүңүз."
    }[lang]
    await m.answer(success_msg, reply_markup=main_kb(m.from_user.id))
    
    admin_text = f"🚨 <b>ЯНГИ БУЮРТМА: #{oid}</b>\n👤 Исм: {m.from_user.full_name}\n📞 Тел: {phone}\n🚚 Етказиш: {delivery} ({vehicle})\n🏢 База: {closest_base}\n📍 Манзил: {location}\n💰 ЖАМИ Сумма: {final_total} сом\n💵 Олдиндан тўланди (10%): {advance} сом\n📦 Қолдиқ (Ҳайдовчи олади): {final_total - advance} сом"
    
    for a in ADMIN_IDS:
        await bot.send_photo(a, photo=check_file_id, caption=admin_text, parse_mode="HTML")
        if location != "Базадан олиб кетади" and "," in location:
            try:
                lat, lon = location.split(",")
                await bot.send_location(a, latitude=float(lat), longitude=float(lon))
            except: pass
            
    await state.update_data(cart={})
    await state.set_state(None)

@dp.message(UserState.check_photo)
async def user_check_invalid(m: types.Message):
    await m.answer("Илтимос, тўлов чекини фақат расм (скриншот) кўринишида юборинг!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
