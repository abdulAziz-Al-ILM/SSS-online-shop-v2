from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL
from bson import ObjectId
import time

# Ma'lumotlar bazasiga ulanish
client = AsyncIOMotorClient(MONGO_URL)
db = client['sss_new_shop']
products_col = db['products']
settings_col = db['settings']
orders_col = db['orders']

# Saytning dinamik bo'limlari uchun yangi kolleksiyalar
services_col = db['services']
locations_col = db['locations']
ads_col = db['ads']

# ================= MAHSULOTLAR BILAN ISHLASH (ESKI FUNKSIYALAR) =================

async def add_product(name, price, stock, file_id, description):
    """Yangi mahsulot qo'shish"""
    await products_col.insert_one({
        "name": name, "price": price, "stock": stock,
        "file_id": file_id, "description": description
    })

async def get_products_paginated(page=0, page_size=6):
    """Mahsulotlarni sahifalarga bo'lib olish"""
    skip = page * page_size
    cursor = products_col.find().skip(skip).limit(page_size)
    products = await cursor.to_list(length=page_size)
    total_count = await products_col.count_documents({})
    return products, total_count

async def get_product(pid):
    """ID bo'yicha mahsulotni topish"""
    try: 
        return await products_col.find_one({"_id": ObjectId(pid)})
    except: 
        return None

async def delete_product(pid):
    """Mahsulotni o'chirish"""
    await products_col.delete_one({"_id": ObjectId(pid)})

async def decrease_stock(pid, qty):
    """Sotuvdan keyin ombordagi sonini kamaytirish"""
    await products_col.update_one({"_id": ObjectId(pid)}, {"$inc": {"stock": -qty}})

async def set_product_stock(pid, new_stock):
    """Ombordagi sonini qo'lda tahrirlash"""
    await products_col.update_one({"_id": ObjectId(pid)}, {"$set": {"stock": new_stock}})

async def get_all_products():
    """Barcha mahsulotlar ro'yxatini olish"""
    return await products_col.find().to_list(length=1000)

# ================= BUYURTMALAR BILAN ISHLASH (ESKI FUNKSIYALAR) =================

async def create_order(user_id, user_name, phone, cart, total_price, pay_method, delivery_type, location, comment):
    """Yangi buyurtma yaratish"""
    order_id = str(int(time.time() * 1000))[-6:] 
    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "user_name": user_name,
        "phone": phone,
        "cart": cart,
        "total_price": total_price,
        "pay_method": pay_method,
        "delivery_type": delivery_type,
        "location": location,
        "comment": comment,
        "status": "new",
        "created_at": time.time()
    }
    await orders_col.insert_one(order_data)
    return order_id

async def get_order_by_id(order_id):
    """ID bo'yicha buyurtmani olish"""
    return await orders_col.find_one({"order_id": order_id})

async def update_order_status(order_id, new_status):
    """Buyurtma statusini yangilash"""
    await orders_col.update_one({"order_id": order_id}, {"$set": {"status": new_status}})

async def get_orders_by_status(status):
    """Status bo'yicha buyurtmalarni filtrlash"""
    return await orders_col.find({"status": status}).to_list(length=50)

# ================= SAYTNI BOSHQARISH (YANGI FUNKSIYALAR) =================

async def set_shop_info(address, phone, about):
    """Firma ma'lumotlarini (manzil, tel, tavsif) saqlash"""
    await settings_col.update_one(
        {"type": "info"}, 
        {"$set": {"address": address, "phone": phone, "about": about}}, 
        upsert=True
    )

async def set_social_links(tg, ig, wa, ch):
    """Ijtimoiy tarmoqlar va kanal havolalarini saqlash"""
    await settings_col.update_one(
        {"type": "socials"}, 
        {"$set": {"telegram": tg, "instagram": ig, "whatsapp": wa, "channel": ch}}, 
        upsert=True
    )

async def set_logo(file_id):
    """Sayt logotipi uchun file_id saqlash"""
    await settings_col.update_one(
        {"type": "logo"}, 
        {"$set": {"file_id": file_id}}, 
        upsert=True
    )

async def add_service(name, desc):
    """Saytga yangi xizmat turini qo'shish"""
    await services_col.insert_one({
        "name": name, 
        "description": desc, 
        "icon": "fa-solid fa-tools"
    })

async def add_location(name, address, lat, lon):
    """Yangi filial lokatsiyasini Telegram koordinatalari orqali qo'shish"""
    # Koordinatalarni avtomatik Yandex xarita linkiga aylantirish
    map_link = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map"
    await locations_col.insert_one({
        "name": name, 
        "address": address, 
        "map_link": map_link
    })

async def add_ad(title, text, discount):
    """Saytga reklama yoki bonus e'lonini qo'shish"""
    await ads_col.insert_one({
        "title": title, 
        "text": text, 
        "discount": discount, 
        "active": True
    })

async def get_shop_info():
    """Firma ma'lumotlarini bazadan o'qish"""
    info = await settings_col.find_one({"type": "info"})
    return info if info else {"address": "Киритилмаган", "phone": "Киритилмаган", "about": "Киритилмаган"}
