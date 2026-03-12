import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import MONGO_URL

# Tizim loglarini sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ma'lumotlar bazasiga ulanish sozlamalari
try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['sss_new_shop']
    
    # Kolleksiyalar ro'yxati
    products_col = db['products']
    settings_col = db['settings']
    orders_col = db['orders']
    services_col = db['services']
    locations_col = db['locations']
    ads_col = db['ads']
    logger.info("MongoDB bilan aloqa muvaffaqiyatli o'rnatildi.")
except Exception as e:
    logger.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")

# =====================================================================
# 1. MAHSULOTLAR (PRODUCTS) - CRUD FUNKSIYALARI
# =====================================================================

async def add_product(name, price, stock, file_id, description):
    """Yangi mahsulotni bazaga qo'shish"""
    try:
        product_data = {
            "name": name,
            "price": int(price),
            "stock": int(stock),
            "file_id": file_id,
            "description": description,
            "created_at": time.time()
        }
        result = await products_col.insert_one(product_data)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Mahsulot qo'shishda xato: {e}")
        return None

async def get_products_paginated(page=0, page_size=6):
    """Mahsulotlarni sahifalarga bo'lib olish (UX uchun)"""
    try:
        skip = page * page_size
        cursor = products_col.find().sort("created_at", -1).skip(skip).limit(page_size)
        products = await cursor.to_list(length=page_size)
        total_count = await products_col.count_documents({})
        return products, total_count
    except Exception as e:
        logger.error(f"Mahsulotlarni yuklashda xato: {e}")
        return [], 0

async def get_product(pid):
    """ID bo'yicha bitta mahsulotni olish"""
    try:
        return await products_col.find_one({"_id": ObjectId(pid)})
    except Exception as e:
        logger.error(f"Mahsulotni topishda xato: {pid} - {e}")
        return None

async def delete_product(pid):
    """Mahsulotni butunlay o'chirish"""
    try:
        await products_col.delete_one({"_id": ObjectId(pid)})
        return True
    except Exception as e:
        logger.error(f"Mahsulotni o'chirishda xato: {e}")
        return False

async def set_product_stock(pid, new_stock):
    """Ombordagi mahsulot sonini qo'lda yangilash"""
    try:
        await products_col.update_one(
            {"_id": ObjectId(pid)}, 
            {"$set": {"stock": int(new_stock)}}
        )
        return True
    except Exception as e:
        logger.error(f"Zaxirani yangilashda xato: {e}")
        return False

async def decrease_stock(pid, qty):
    """Sotuvdan keyin ombordagi sonini kamaytirish"""
    try:
        await products_col.update_one(
            {"_id": ObjectId(pid)}, 
            {"$inc": {"stock": -int(qty)}}
        )
        return True
    except Exception as e:
        logger.error(f"Zaxirani kamaytirishda xato: {e}")
        return False

async def get_all_products():
    """Barcha mahsulotlar ro'yxatini olish (Admin uchun)"""
    try:
        return await products_col.find().to_list(length=1000)
    except Exception as e:
        logger.error(f"Barcha mahsulotlarni olishda xato: {e}")
        return []

# =====================================================================
# 2. BUYURTMALAR (ORDERS) - BOSHQARUV
# =====================================================================

async def create_order(user_id, user_name, phone, cart, total_price, pay_method, delivery_type, location, comment):
    """Yangi buyurtma yaratish"""
    try:
        order_id = str(int(time.time() * 1000))[-6:] 
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "user_name": user_name,
            "phone": str(phone), # Har qanday formatdagi raqamni saqlaydi
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
    except Exception as e:
        logger.error(f"Buyurtma yaratishda xato: {e}")
        return None

async def get_order_by_id(order_id):
    """ID bo'yicha buyurtmani olish"""
    try:
        return await orders_col.find_one({"order_id": order_id})
    except Exception as e:
        logger.error(f"Buyurtmani topishda xato: {e}")
        return None

async def update_order_status(order_id, new_status):
    """Buyurtma holatini yangilash"""
    try:
        await orders_col.update_one({"order_id": order_id}, {"$set": {"status": new_status}})
        return True
    except Exception as e:
        logger.error(f"Statusni yangilashda xato: {e}")
        return False

async def get_orders_by_status(status):
    """Status bo'yicha filtrlangan buyurtmalar ro'yxati"""
    try:
        return await orders_col.find({"status": status}).limit(50).to_list(length=50)
    except Exception as e:
        logger.error(f"Buyurtmalarni yuklashda xato: {e}")
        return []

# =====================================================================
# 3. XIZMATLAR (SERVICES) - BOSHQARUV
# =====================================================================

async def add_service(name, desc):
    """Saytga yangi xizmat turini qo'shish"""
    try:
        await services_col.insert_one({
            "name": name, 
            "description": desc, 
            "icon": "fa-solid fa-helmet-safety"
        })
        return True
    except Exception as e:
        logger.error(f"Xizmat qo'shishda xato: {e}")
        return False

async def get_all_services():
    """Barcha xizmatlar ro'yxatini olish"""
    try:
        return await services_col.find().to_list(length=50)
    except Exception as e:
        logger.error(f"Xizmatlarni olishda xato: {e}")
        return []

async def delete_service(sid):
    """Xizmatni o'chirish"""
    try:
        await services_col.delete_one({"_id": ObjectId(sid)})
        return True
    except Exception as e:
        logger.error(f"Xizmatni o'chirishda xato: {e}")
        return False

# =====================================================================
# 4. LOKATSIYALAR (LOCATIONS) - FILIALLAR
# =====================================================================

async def add_location(name, address, lat, lon):
    """Yangi filialni koordinatalar orqali qo'shish"""
    try:
        map_link = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map"
        await locations_col.insert_one({
            "name": name, 
            "address": address, 
            "map_link": map_link
        })
        return True
    except Exception as e:
        logger.error(f"Lokatsiya qo'shishda xato: {e}")
        return False

async def get_all_locations():
    """Barcha filiallar ro'yxatini olish"""
    try:
        return await locations_col.find().to_list(length=20)
    except Exception as e:
        logger.error(f"Lokatsiyalarni olishda xato: {e}")
        return []

async def delete_location(lid):
    """Filialni o'chirish"""
    try:
        await locations_col.delete_one({"_id": ObjectId(lid)})
        return True
    except Exception as e:
        logger.error(f"Lokatsiyani o'chirishda xato: {e}")
        return False

# =====================================================================
# 5. AKSIYALAR (ADS) - REKLAMA
# =====================================================================

async def add_ad(title, text, discount):
    """Saytga aksiya yoki chegirma e'lonini qo'shish"""
    try:
        await ads_col.insert_one({
            "title": title, 
            "text": text, 
            "discount": int(discount) if discount else 0, 
            "active": True
        })
        return True
    except Exception as e:
        logger.error(f"Aksiya qo'shishda xato: {e}")
        return False

async def get_all_ads():
    """Barcha e'lonlar ro'yxatini olish"""
    try:
        return await ads_col.find().to_list(length=10)
    except Exception as e:
        logger.error(f"Aksiyalarni olishda xato: {e}")
        return []

async def delete_ad(aid):
    """E'lonni o'chirish"""
    try:
        await ads_col.delete_one({"_id": ObjectId(aid)})
        return True
    except Exception as e:
        logger.error(f"Aksiyani o'chirishda xato: {e}")
        return False

# =====================================================================
# 6. SOZLAMALAR (SETTINGS) - INFO, LOGO, SOCIALS
# =====================================================================

async def set_shop_info(address, phone, about):
    """Firma asosiy ma'lumotlarini saqlash"""
    try:
        await settings_col.update_one(
            {"type": "info"}, 
            {"$set": {"address": address, "phone": str(phone), "about": about}}, 
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Info saqlashda xato: {e}")
        return False

async def get_shop_info():
    """Asosiy ma'lumotlarni olish"""
    try:
        info = await settings_col.find_one({"type": "info"})
        return info if info else {"address": "Киритилмаган", "phone": "Йўқ", "about": "Йўқ"}
    except Exception as e:
        logger.error(f"Info yuklashda xato: {e}")
        return {"address": "Xato", "phone": "Xato", "about": "Xato"}

async def set_social_links(tg, ig, wa, ch):
    """Ijtimoiy tarmoqlar va kanallarni sozlash"""
    try:
        await settings_col.update_one(
            {"type": "socials"}, 
            {"$set": {"telegram": tg, "instagram": ig, "whatsapp": wa, "channel": ch}}, 
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Tarmoqlarni saqlashda xato: {e}")
        return False

async def set_logo(file_id):
    """Sayt logotipi uchun file_id saqlash"""
    try:
        await settings_col.update_one(
            {"type": "logo"}, 
            {"$set": {"file_id": file_id}}, 
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Logotip saqlashda xato: {e}")
        return False

# 200 qator atrofida to'liq mantiqiy yakunlangan kod.
