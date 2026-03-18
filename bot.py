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
    category = State()
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
    delivery_type = State()
    phone = State()
    location = State()
    check_photo = State()
    pay_method = State()
   

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
        rows.append([KeyboardButton(text="⚙️ Тармоқлар ва инфо")])
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
    await m.answer("✅ Хизмат сайтга қўшилди!", reply_markup=main_kb(m.from_user.id))
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

# =====================================================================
# INFO & TARMOQLAR
# =====================================================================

@dp.message(F.text == "⚙️ Тармоқлар ва инфо")
async def admin_info_manage(m: types.Message):
    if not is_admin(m.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="📞 Телефон", callback_data="edit_info_phone")
    kb.button(text="📍 Манзил", callback_data="edit_info_address")
    kb.button(text="ℹ️ Биз ҳақида", callback_data="edit_info_about")
    kb.button(text="📢 ТГ Канал", callback_data="edit_soc_ch")
    kb.button(text="📸 Instagram", callback_data="edit_soc_ig")
    kb.button(text="💬 WhatsApp", callback_data="edit_soc_wa")
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
    current_state = await state.get_state()
    
    # Eski ma'lumotlar o'chib ketmasligi uchun ularni bazadan tortib olamiz
    info = await get_combined_info()
    address = info.get("address", "")
    phone = info.get("phone", "")
    about = info.get("about", "")
    ch = info.get("telegram_channel", "")
    ig = info.get("instagram", "")
    wa = info.get("whatsapp", "")
    
    bot_info = await bot.get_me()
    tg = f"https://t.me/{bot_info.username}"

    # Qaysi tugma bosilgan bo'lsa, faqat o'shaning qiymatini yangilaymiz
    if current_state == AdminState.info_phone.state: phone = m.text
    elif current_state == AdminState.info_address.state: address = m.text
    elif current_state == AdminState.info_about.state: about = m.text
    elif current_state == AdminState.soc_ch.state: ch = m.text
    elif current_state == AdminState.soc_ig.state: ig = m.text
    elif current_state == AdminState.soc_wa.state: wa = m.text

    # Yangilangan to'plamni bazaga qaytarib saqlaymiz
    await set_shop_info(address, phone, about)
    await set_social_links(tg, ig, wa, ch)
    
    await m.answer("✅ Маълумот муваффақиятли янгиланди!", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# =====================================================================
# MAHSULOT QO'SHISH, BUYURTMA, DO'KON... (QOLGAN HAMMASI)
# =====================================================================

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
    await m.answer("📸 Маҳсулот расмини юборинг:")
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
    # add_product ga d['category'] argumentini qo'shib yuborish
    await add_product(d['name'], d['price'], int(m.text), d['file_id'], d['desc'], d['category'])
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
async def user_shop(m: types.Message):
    cats = await get_categories()
    if not cats: return await m.answer("Маҳсулот йўқ")
    kb = InlineKeyboardBuilder()
    for c in cats:
        kb.button(text=c, callback_data=f"cat_{c[:20]}") 
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
    if not cat: return await call.answer("Хатолик: Категория топилмади, қайта киринг", show_alert=True)
    await user_shop_page(call, cat, int(call.data.split("_")[2]))

# MANA SHU FUNKSIYA SENDA TUSHIB QOLGAN EDI:
async def user_shop_page(m_or_call, cat, page):
    prods, total = await get_products_by_category_paginated(cat, page, 6)
    if not prods: 
        return await (m_or_call.answer("Маҳсулот йўқ") if isinstance(m_or_call, types.Message) else m_or_call.answer("Бўш", show_alert=True))
    
    kb = InlineKeyboardBuilder()
    for p in prods: 
        kb.button(text=f"{p['name']}", callback_data=f"u_v_{p['_id']}")
    kb.adjust(2)
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"u_p_{page-1}"))
    if (page + 1) * 6 < total: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"u_p_{page+1}"))
    
    # Katalogga qaytish tugmasi
    nav.append(InlineKeyboardButton(text="🔙 Каталог", callback_data="back_to_cats"))
    if nav: kb.row(*nav)
    
    text = f"📁 Категория: <b>{cat}</b>\nМаҳсулотларимиз:"
    if isinstance(m_or_call, types.Message): 
        await m_or_call.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else: 
        await m_or_call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")

# KATALOGGA QAYTISH HANDLERI HAM TUSHIB QOLGAN EDI:
@dp.callback_query(F.data == "back_to_cats")
async def back_to_categories(call: CallbackQuery):
    await user_shop(call.message)
    await call.message.delete()

@dp.callback_query(F.data.startswith("u_v_"))
async def user_p_view(call: CallbackQuery):
    p = await get_product(call.data.split("_")[2])
    cap = f"📱 <b>{p['name']}</b>\n💰 {p['price']} сўм\n📝 {p['description']}\n📦 Омборда: {p['stock']}"
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Саватга қўшиш", callback_data=f"u_a_{p['_id']}")
    kb.button(text="🔙 Орқага", callback_data="u_p_0")
    try: 
        await call.message.answer_photo(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
    except: 
        await call.message.answer_document(p['file_id'], caption=cap, parse_mode="HTML", reply_markup=kb.as_markup())
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
    # 1. Eng birinchi yetkazish usuli so'raladi
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚕 Етказиб бериш (Такси)"), KeyboardButton(text="🚶‍♂️ Ўзим олиб кетаман")],
        [KeyboardButton(text="❌ Бекор қилиш")]
    ], resize_keyboard=True)
    await call.message.answer("Етказиб бериш усулини танланг:", reply_markup=kb)
    await state.set_state(UserState.delivery_type)
    await call.message.delete()

@dp.message(F.text == "❌ Бекор қилиш")
async def cancel_checkout(m: types.Message, state: FSMContext):
    # Xaridor xohlagan payti otmen qilishi mumkin
    await state.set_state(None)
    await m.answer("Буюртма бекор қилинди.", reply_markup=main_kb(m.from_user.id))

@dp.message(UserState.delivery_type)
async def user_delivery_get(m: types.Message, state: FSMContext):
    # 2. Xaridor tugmani bosgach, nima bosganini tekshiramiz
    if m.text not in ["🚕 Етказиб бериш (Такси)", "🚶‍♂️ Ўзим олиб кетаман"]:
        return await m.answer("Илтимос, пастдаги тугмалардан бирини танланг!")
    
    await state.update_data(delivery_type=m.text) # Xotiraga saqladik
    
    # Agar taksi desa, lokatsiya so'raymiz
    if m.text == "🚕 Етказиб бериш (Такси)":
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📍 Локация юбориш", request_location=True)], 
            [KeyboardButton(text="❌ Бекор қилиш")]
        ], resize_keyboard=True)
        await m.answer("Манзилингизни (Локация) юборинг ёки матн кўринишида ёзинг:", reply_markup=kb)
        await state.set_state(UserState.location)
    # Agar o'zim olib ketaman desa, manzil kerak emas, to'g'ridan-to'g'ri nomer so'raymiz
    else:
        await state.update_data(location="Дўкондан олиб кетиш")
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📱 Рақамни юбориш", request_contact=True)], 
            [KeyboardButton(text="❌ Бекор қилиш")]
        ], resize_keyboard=True)
        await m.answer("Телефон рақамингизни юборинг ёки ёзинг:", reply_markup=kb)
        await state.set_state(UserState.phone)

@dp.message(UserState.location)
async def user_location_get(m: types.Message, state: FSMContext):
    # 3. Lokatsiya kelgach, uni saqlab, endi telefon nomer so'raymiz
    loc = f"{m.location.latitude},{m.location.longitude}" if m.location else m.text
    await state.update_data(location=loc)
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Рақамни юбориш", request_contact=True)], 
        [KeyboardButton(text="❌ Бекор қилиш")]
    ], resize_keyboard=True)
    await m.answer("Телефон рақамингизни юборинг ёки ёзинг:", reply_markup=kb)
    await state.set_state(UserState.phone)

@dp.message(UserState.phone)
async def user_phone_get(m: types.Message, state: FSMContext):
    # 4. Telefon kelgach, endi to'lov usulini so'raymiz
    phone = m.contact.phone_number if m.contact else m.text
    await state.update_data(phone=phone)
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💵 Нақд пул"), KeyboardButton(text="💳 Пластик карта")],
        [KeyboardButton(text="❌ Бекор қилиш")]
    ], resize_keyboard=True)
    await m.answer("Тўлов усулини танланг:", reply_markup=kb)
    await state.set_state(UserState.pay_method)

@dp.message(UserState.pay_method)
async def user_pay_method_get(m: types.Message, state: FSMContext):
    # 5. To'lov usuli tanlangach...
    if m.text not in ["💵 Нақд пул", "💳 Пластик карта"]:
        return await m.answer("Илтимос, тугмалардан бирини танланг!")
        
    await state.update_data(pay_method=m.text)
    
    # Agar Karta tanlasa, karta raqamini berib rasmini so'raymiz
    if m.text == "💳 Пластик карта":
        await m.answer(f"Тўловни қуйидаги картага амалга оширинг:\n\n💳 <b>{CARD_NUMBER}</b>\n\nТўлов қилгач, скриншот (чек) ни шу ерга юборинг:", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        await state.set_state(UserState.check_photo)
    # Agar naqd bo'lsa, rasmni kutmasdan buyurtmani yopamiz
    else:
        await finish_order(m, state)

@dp.message(UserState.check_photo, F.photo)
async def user_check_get(m: types.Message, state: FSMContext):
    # 6. Rasm kelgach, uni xotiraga olib buyurtmani yopamiz
    await state.update_data(check_file_id=m.photo[-1].file_id)
    await finish_order(m, state)
    
@dp.message(UserState.check_photo)
async def user_check_invalid(m: types.Message):
    # Agar rasm o'rniga yozuv tashlasa so'kish
    await m.answer("Илтимос, тўлов чекини фақат расм (скриншот) кўринишида юборинг!")

async def finish_order(m: types.Message, state: FSMContext):
    # 7. Final. Xotiradagi barcha ma'lumotlarni yig'amiz
    d = await state.get_data()
    cart = d.get("cart", {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    
    delivery = d.get('delivery_type', 'Noma\'lum')
    location = d.get('location', 'Noma\'lum')
    phone = d.get('phone', 'Noma\'lum')
    pay = d.get('pay_method', 'Noma\'lum')
    check = d.get('check_file_id', 'Йўқ')
    
    # Bazaga yozamiz. Chek rasmini ID sini comment ustuniga tiqib yubordim.
    oid = await create_order(m.from_user.id, m.from_user.full_name, phone, cart, total, pay, delivery, location, f"Чек ID: {check}")
    
    # Ombordan mahsulotlarni ayiramiz
    for pid, i in cart.items(): await decrease_stock(pid, i['qty'])
    
    await m.answer(f"✅ Буюртма қабул қилинди! Чек ID: #{oid}\nТез орада алоқага чиқамиз.", reply_markup=main_kb(m.from_user.id))
    
    # Adminga boradigan xabarni tayyorlaymiz
    admin_text = f"🚨 <b>ЯНГИ БУЮРТМА: #{oid}</b>\n👤 Исм: {m.from_user.full_name}\n📞 Тел: {phone}\n🚕 Усул: {delivery}\n📍 Манзил: {location}\n💵 Тўлов: {pay}\n💰 Сумма: {total} сўм"
    
    for a in ADMIN_IDS:
        # Agar karta orqali to'lagan bo'lsa adminga rasmi bilan boradi
        if check != 'Йўқ':
            await bot.send_photo(a, photo=check, caption=admin_text, parse_mode="HTML")
        # Agar naqd bo'lsa oddiy xabar
        else:
            await bot.send_message(a, admin_text, parse_mode="HTML")
            # Agar haqiqiy lokatsiya tashlagan bo'lsa, xaritadagi nuqtani ham adminga alohida tashlaymiz
            if location != "Дўкондан олиб кетиш" and "," in location:
                try:
                    lat, lon = location.split(",")
                    await bot.send_location(a, latitude=float(lat), longitude=float(lon))
                except: pass
            
    # Savatni va xotirani tozalash
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
