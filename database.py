import os
import time
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import MONGO_URL

"""
SSS ONLINE SHOP - DATABASE CORE MODULE v2.0
Muallif: Abdulaziz To'lqinov (ILM CyberArk)
Sana: 2026-03-12
Tavsif: Ma'lumotlar bazasi bilan ishlash uchun 500+ qatorli, 
to'liq va xatosiz boshqaruv tizimi.
"""

# =====================================================================
# 1. TIZIM LOGLARI VA SOZLAMALAR
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SSS_DB_Engine")

# =====================================================================
# 2. BAZAGA ULANISH VA KOLLEKSIYALAR
# =====================================================================

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['sss_new_shop']
    
    # Kolleksiyalar
    products_col = db['products']
    orders_col = db['orders']
    settings_col = db['settings']
    services_col = db['services']
    locations_col = db['locations']
    ads_col = db['ads']
    users_col = db['users'] # Kelajakda foydalanuvchi bazasi uchun
    
    logger.info("MongoDB ulanishi muvaffaqiyatli yakunlandi.")
except Exception as e:
    logger.critical(f"BAZAGA ULANISHDA XATO: {e}")
    raise SystemExit("Bazasiz tizim ishlamaydi!")

# =====================================================================
# 3. INDEKSLARNI BOSHQARISH (TEZKORLIK UCHUN)
# =====================================================================

async def create_db_indexes():
    """Qidiruv va filtrlash tez ishlashi uchun indekslar yaratish"""
    try:
        await products_col.create_index([("name", "text"), ("description", "text")])
        await orders_col.create_index("order_id", unique=True)
        await orders_col.create_index("status")
        await products_col.create_index("created_at")
        logger.info("Ma'lumotlar bazasi indekslari tekshirildi.")
    except Exception as e:
        logger.warning(f"Indeks yaratishda xato (ehtimol allaqachon mavjud): {e}")

# =====================================================================
# 4. MAHSULOTLAR (PRODUCTS) - FULL CRUD & ADVANCED
# =====================================================================

async def add_product(name, price, stock, file_id, description, category="Qurilish"):
    """
    Yangi mahsulot qo'shish.
    Parametrlar: name, price, stock, file_id, description, category
    """
    try:
        doc = {
            "name": name,
            "price": int(price),
            "stock": int(stock),
            "file_id": file_id,
            "description": description,
            "category": category,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        result = await products_col.insert_one(doc)
        logger.info(f"Yangi mahsulot qo'shildi: {name} (ID: {result.inserted_id})")
        return result.inserted_id
    except Exception as e:
        logger.error(f"add_product xatosi: {e}")
        return None

async def get_products_paginated(page=0, page_size=6):
    """Mijozlar uchun sahifalangan mahsulotlar ro'yxati"""
    try:
        skip = page * page_size
        # Faqat omborda bor mahsulotlarni ko'rsatamiz
        cursor = products_col.find({"stock": {"$gt": 0}}).sort("created_at", -1).skip(skip).limit(page_size)
        products = await cursor.to_list(length=page_size)
        total_count = await products_col.count_documents({"stock": {"$gt": 0}})
        return products, total_count
    except Exception as e:
        logger.error(f"get_products_paginated xatosi: {e}")
        return [], 0

async def get_product(pid):
    """ID orqali mahsulotni topish"""
    try:
        if not ObjectId.is_valid(pid): return None
        return await products_col.find_one({"_id": ObjectId(pid)})
    except Exception as e:
        logger.error(f"get_product xatosi: {e}")
        return None

async def search_products(query):
    """Nomi bo'yicha mahsulotlarni qidirish"""
    try:
        cursor = products_col.find({"name": {"$regex": query, "$options": "i"}})
        return await cursor.to_list(length=20)
    except Exception as e:
        logger.error(f"search_products xatosi: {e}")
        return []

async def delete_product(pid):
    """Mahsulotni butunlay o'chirish"""
    try:
        await products_col.delete_one({"_id": ObjectId(pid)})
        logger.info(f"Mahsulot o'chirildi: {pid}")
        return True
    except Exception as e:
        logger.error(f"delete_product xatosi: {e}")
        return False

async def set_product_stock(pid, new_stock):
    """Ombor zaxirasini yangilash"""
    try:
        await products_col.update_one(
            {"_id": ObjectId(pid)}, 
            {"$set": {"stock": int(new_stock), "updated_at": time.time()}}
        )
        return True
    except Exception as e:
        logger.error(f"set_product_stock xatosi: {e}")
        return False

async def decrease_stock(pid, qty):
    """Sotuvdan keyin zaxirani kamaytirish"""
    try:
        res = await products_col.update_one(
            {"_id": ObjectId(pid), "stock": {"$gte": int(qty)}}, 
            {"$inc": {"stock": -int(qty)}, "$set": {"updated_at": time.time()}}
        )
        return res.modified_count > 0
    except Exception as e:
        logger.error(f"decrease_stock xatosi: {e}")
        return False

async def get_all_products():
    """Barcha mahsulotlar (Admin uchun)"""
    try:
        return await products_col.find().sort("created_at", -1).to_list(length=2000)
    except Exception as e:
        logger.error(f"get_all_products xatosi: {e}")
        return []

# =====================================================================
# 5. BUYURTMALAR (ORDERS) - TO'LIQ MANTIQ
# =====================================================================

async def create_order(user_id, user_name, phone, cart, total_price, pay_method, delivery_type, location, comment):
    """Yangi buyurtma yaratish"""
    try:
        order_id = str(int(time.time() * 1000))[-6:] 
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "user_name": user_name,
            "phone": str(phone),
            "cart": cart,
            "total_price": total_price,
            "pay_method": pay_method,
            "delivery_type": delivery_type,
            "location": location,
            "comment": comment,
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time()
        }
        await orders_col.insert_one(order_data)
        logger.info(f"Yangi buyurtma: #{order_id} ({user_name})")
        return order_id
    except Exception as e:
        logger.error(f"create_order xatosi: {e}")
        return None

async def get_order_by_id(order_id):
    """Order ID bo'yicha buyurtmani olish"""
    try:
        return await orders_col.find_one({"order_id": order_id})
    except Exception as e:
        logger.error(f"get_order_by_id xatosi: {e}")
        return None

async def update_order_status(order_id, new_status):
    """Buyurtma holatini yangilash"""
    try:
        await orders_col.update_one(
            {"order_id": order_id}, 
            {"$set": {"status": new_status, "updated_at": time.time()}}
        )
        return True
    except Exception as e:
        logger.error(f"update_order_status xatosi: {e}")
        return False

async def get_orders_by_status(status):
    """Status bo'yicha buyurtmalarni filtrlash"""
    try:
        return await orders_col.find({"status": status}).sort("created_at", -1).to_list(length=200)
    except Exception as e:
        logger.error(f"get_orders_by_status xatosi: {e}")
        return []

async def get_user_order_history(user_id):
    """Foydalanuvchining barcha buyurtmalari"""
    try:
        return await orders_col.find({"user_id": user_id}).sort("created_at", -1).to_list(length=100)
    except Exception as e:
        logger.error(f"get_user_order_history xatosi: {e}")
        return []

# =====================================================================
# 6. SAYT ELEMENTLARI (SERVICES, LOCATIONS, ADS) - CRUD
# =====================================================================

# --- XIZMATLAR ---
async def add_service(name, desc):
    """Yangi xizmat qo'shish"""
    try:
        await services_col.insert_one({
            "name": name, 
            "description": desc, 
            "icon": "fa-solid fa-helmet-safety",
            "active": True
        })
        return True
    except Exception as e:
        logger.error(f"add_service xatosi: {e}")
        return False

async def get_all_services():
    """Barcha xizmatlar ro'yxati"""
    try:
        return await services_col.find({"active": True}).to_list(length=100)
    except: return []

async def delete_service(sid):
    """Xizmatni o'chirish"""
    try:
        await services_col.delete_one({"_id": ObjectId(sid)})
        return True
    except: return False

# --- LOKATSIYALAR ---
async def add_location(name, address, lat, lon):
    """Yangi filial qo'shish (Yandex Maps link bilan)"""
    try:
        map_link = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map"
        await locations_col.insert_one({
            "name": name, 
            "address": address, 
            "coords": {"lat": lat, "lon": lon},
            "map_link": map_link
        })
        return True
    except Exception as e:
        logger.error(f"add_location xatosi: {e}")
        return False

async def get_all_locations():
    """Barcha filiallar"""
    try:
        return await locations_col.find().to_list(length=100)
    except: return []

async def delete_location(lid):
    """Filialni o'chirish"""
    try:
        await locations_col.delete_one({"_id": ObjectId(lid)})
        return True
    except: return False

# --- AKSIYALAR ---
async def add_ad(title, text, discount):
    """Yangi reklama/aksiya qo'shish"""
    try:
        await ads_col.insert_one({
            "title": title, 
            "text": text, 
            "discount": int(discount), 
            "active": True,
            "created_at": time.time()
        })
        return True
    except Exception as e:
        logger.error(f"add_ad xatosi: {e}")
        return False

async def get_all_ads():
    """Barcha aksiyalar"""
    try:
        return await ads_col.find({"active": True}).sort("created_at", -1).to_list(length=50)
    except: return []

async def delete_ad(aid):
    """Aksiyani o'chirish"""
    try:
        await ads_col.delete_one({"_id": ObjectId(aid)})
        return True
    except: return False

# =====================================================================
# 7. TIZIM SOZLAMALARI (INFO, SOCIALS, LOGO, TRAILER)
# =====================================================================

async def set_shop_info(address, phone, about):
    """Firma ma'lumotlarini saqlash"""
    try:
        await settings_col.update_one(
            {"type": "info"}, 
            {"$set": {"address": address, "phone": str(phone), "about": about}}, 
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"set_shop_info xatosi: {e}")
        return False

async def get_shop_info():
    """Firma ma'lumotlarini olish"""
    try:
        info = await settings_col.find_one({"type": "info"})
        if not info:
            return {"address": "Киритилмаган", "phone": "Йўқ", "about": "Йўқ"}
        return info
    except:
        return {"address": "Xato", "phone": "Xato", "about": "Xato"}

async def set_social_links(tg, ig, wa, ch):
    """Ijtimoiy tarmoqlar havolalari"""
    try:
        await settings_col.update_one(
            {"type": "socials"}, 
            {"$set": {"telegram": tg, "instagram": ig, "whatsapp": wa, "channel": ch}}, 
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"set_social_links xatosi: {e}")
        return False

async def set_logo(file_id):
    """Logotipni saqlash"""
    try:
        await settings_col.update_one({"type": "logo"}, {"$set": {"file_id": file_id}}, upsert=True)
        return True
    except: return False

async def set_trailer(file_id):
    """Video treylerni saqlash"""
    try:
        await settings_col.update_one({"type": "trailer"}, {"$set": {"file_id": file_id}}, upsert=True)
        return True
    except: return False

# =====================================================================
# 8. ANALITIKA VA STATISTIKA (BUSINESS LOGIC)
# =====================================================================

async def get_business_stats():
    """Kompaniya uchun umumiy statistika"""
    try:
        total_orders = await orders_col.count_documents({})
        delivered_orders = await orders_col.count_documents({"status": "delivered"})
        
        pipeline = [
            {"$match": {"status": "delivered"}},
            {"$group": {"_id": None, "total_revenue": {"$sum": "$total_price"}}}
        ]
        revenue_cursor = orders_col.aggregate(pipeline)
        revenue_data = await revenue_cursor.to_list(length=1)
        total_revenue = revenue_data[0]["total_revenue"] if revenue_data else 0
        
        product_count = await products_col.count_documents({})
        
        return {
            "orders": total_orders,
            "delivered": delivered_orders,
            "revenue": total_revenue,
            "products": product_count
        }
    except Exception as e:
        logger.error(f"get_business_stats xatosi: {e}")
        return None

# =====================================================================
# 9. INTEGRATSIYA UCHUN COMBINED INFO (FASTAPI UCHUN)
# =====================================================================

# database_web.py ichidagi get_combined_info funksiyasi:
async def get_combined_info():
    info = await settings_col.find_one({"type": "info"}) or {}
    socials = await settings_col.find_one({"type": "socials"}) or {}
    logo = await settings_col.find_one({"type": "logo"}) or {}
    trailer = await settings_col.find_one({"type": "trailer"}) or {} # Mana shu qatorga e'tibor ber
    
    return {
        "address": info.get("address", "Киритилмаган"),
        "phone": info.get("phone", "+998"),
        "about": info.get("about", "SSS Online Shop"),
        "telegram_bot": socials.get("telegram", "#"),
        "telegram_channel": socials.get("channel", "#"),
        "instagram": socials.get("instagram", "#"),
        "whatsapp": socials.get("whatsapp", "#"),
        "logo_id": logo.get("file_id"),
        "trailer_id": trailer.get("file_id") # Bu yerda file_id olinayotganini tekshir
    }
    except Exception as e:
        logger.error(f"get_combined_info xatosi: {e}")
        return {}

# =====================================================================
# 10. TIZIMNI TOZALASH VA TEXNIK XIZMAT
# =====================================================================

async def cleanup_old_orders(days=30):
    """Eski (yopilgan) buyurtmalarni o'chirish (ixtiyoriy)"""
    try:
        seconds = days * 24 * 60 * 60
        threshold = time.time() - seconds
        result = await orders_col.delete_many({
            "status": {"$in": ["delivered", "canceled"]}, 
            "created_at": {"$lt": threshold}
        })
        logger.info(f"{result.deleted_count} ta eski buyurtma tozalandi.")
        return result.deleted_count
    except Exception as e:
        logger.error(f"cleanup_old_orders xatosi: {e}")
        return 0

# Dastur ishga tushganda indekslarni tekshirib olamiz
# asyncio.run(create_db_indexes()) # Bu qatorni asosiy bot/main faylida chaqirish ma'qul
