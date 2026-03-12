import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import MONGO_URL

# =====================================================================
# LOGLARNI SOZLASH
# =====================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SSS_Database_Engine")

# =====================================================================
# BAZAGA ULANISH
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
    
    logger.info("MongoDB ulanishi 100% muvaffaqiyatli!")
except Exception as e:
    logger.critical(f"BAZA BILAN ALOQA YO'Q: {e}")

# =====================================================================
# 1. MAHSULOTLAR (PRODUCTS) MANTIQI
# =====================================================================

async def add_product(name, price, stock, file_id, description):
    """Yangi mahsulotni bazaga barcha detallari bilan qo'shish"""
    try:
        doc = {
            "name": name,
            "price": int(price),
            "stock": int(stock),
            "file_id": file_id,
            "description": description,
            "created_at": time.time()
        }
        result = await products_col.insert_one(doc)
        return result.inserted_id
    except Exception as e:
        logger.error(f"add_product xatosi: {e}")
        return None

async def get_products_paginated(page=0, page_size=6):
    """Mijozlar uchun mahsulotlarni sahifalab chiqarish"""
    try:
        skip = page * page_size
        cursor = products_col.find({"stock": {"$gt": 0}}).sort("created_at", -1).skip(skip).limit(page_size)
        products = await cursor.to_list(length=page_size)
        total_count = await products_col.count_documents({"stock": {"$gt": 0}})
        return products, total_count
    except Exception as e:
        logger.error(f"Pagination xatosi: {e}")
        return [], 0

async def get_product(pid):
    """ID orqali mahsulot ma'lumotlarini olish"""
    try:
        if not ObjectId.is_valid(pid): return None
        return await products_col.find_one({"_id": ObjectId(pid)})
    except Exception as e:
        logger.error(f"get_product xatosi: {e}")
        return None

async def delete_product(pid):
    """Mahsulotni o'chirish"""
    try:
        await products_col.delete_one({"_id": ObjectId(pid)})
        return True
    except Exception as e:
        logger.error(f"delete_product xatosi: {e}")
        return False

async def set_product_stock(pid, new_stock):
    """Omborni tahrirlash"""
    try:
        await products_col.update_one({"_id": ObjectId(pid)}, {"$set": {"stock": int(new_stock)}})
        return True
    except Exception as e:
        logger.error(f"set_product_stock xatosi: {e}")
        return False

async def decrease_stock(pid, qty):
    """Sotuvdan keyin ombordagi mahsulotni kamaytirish"""
    try:
        await products_col.update_one({"_id": ObjectId(pid)}, {"$inc": {"stock": -int(qty)}})
        return True
    except Exception as e:
        logger.error(f"decrease_stock xatosi: {e}")
        return False

async def get_all_products():
    """Admin uchun barcha mahsulotlar ro'yxati"""
    try:
        return await products_col.find().sort("created_at", -1).to_list(length=2000)
    except Exception as e:
        logger.error(f"get_all_products xatosi: {e}")
        return []

# =====================================================================
# 2. BUYURTMALAR (ORDERS) MANTIQI
# =====================================================================

async def create_order(user_id, user_name, phone, cart, total_price, pay_method, delivery_type, location, comment):
    """Yangi buyurtma va unikal ID"""
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
            "created_at": time.time()
        }
        await orders_col.insert_one(order_data)
        return order_id
    except Exception as e:
        logger.error(f"create_order xatosi: {e}")
        return None

async def get_order_by_id(order_id):
    try:
        return await orders_col.find_one({"order_id": order_id})
    except Exception as e:
        logger.error(f"get_order_by_id xatosi: {e}")
        return None

async def update_order_status(order_id, new_status):
    try:
        await orders_col.update_one({"order_id": order_id}, {"$set": {"status": new_status}})
        return True
    except Exception as e:
        logger.error(f"update_order_status xatosi: {e}")
        return False

async def get_orders_by_status(status):
    try:
        return await orders_col.find({"status": status}).sort("created_at", -1).to_list(length=100)
    except Exception as e:
        logger.error(f"get_orders_by_status xatosi: {e}")
        return []

# =====================================================================
# 3. SAYT ELEMENTLARI (XIZMAT, LOKATSIYA, AKSIYA) - CRUD
# =====================================================================

async def add_service(name, desc):
    try:
        await services_col.insert_one({"name": name, "description": desc, "icon": "fa-solid fa-helmet-safety"})
        return True
    except Exception as e:
        logger.error(f"add_service xatosi: {e}")
        return False

async def get_all_services():
    try:
        return await services_col.find().to_list(length=100)
    except: return []

async def delete_service(sid):
    try:
        await services_col.delete_one({"_id": ObjectId(sid)})
        return True
    except: return False

async def add_location(name, address, lat, lon):
    try:
        map_link = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map"
        await locations_col.insert_one({"name": name, "address": address, "map_link": map_link})
        return True
    except Exception as e:
        logger.error(f"add_location xatosi: {e}")
        return False

async def get_all_locations():
    try:
        return await locations_col.find().to_list(length=100)
    except: return []

async def delete_location(lid):
    try:
        await locations_col.delete_one({"_id": ObjectId(lid)})
        return True
    except: return False

async def add_ad(title, text, discount):
    try:
        await ads_col.insert_one({"title": title, "text": text, "discount": int(discount), "active": True})
        return True
    except Exception as e:
        logger.error(f"add_ad xatosi: {e}")
        return False

async def get_all_ads():
    try:
        return await ads_col.find().to_list(length=50)
    except: return []

async def delete_ad(aid):
    try:
        await ads_col.delete_one({"_id": ObjectId(aid)})
        return True
    except: return False

# =====================================================================
# 4. SOZLAMALAR (INFO, LOGO, SOCIALS, TRAILER)
# =====================================================================

async def set_shop_info(address, phone, about):
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
    try:
        info = await settings_col.find_one({"type": "info"})
        if not info:
            return {"address": "Киритилмаган", "phone": "Йўқ", "about": "Йўқ"}
        return info
    except Exception as e:
        logger.error(f"get_shop_info xatosi: {e}")
        return {"address": "Xato", "phone": "Xato", "about": "Xato"}

async def set_social_links(tg, ig, wa, ch):
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
    try:
        await settings_col.update_one({"type": "logo"}, {"$set": {"file_id": file_id}}, upsert=True)
        return True
    except Exception as e:
        logger.error(f"set_logo xatosi: {e}")
        return False

async def set_trailer(file_id):
    """Sayt headeri uchun video file_id (trailer) saqlash"""
    try:
        # BUNDA FILE_ID'NI TRAILER_ID KALITI OSTIDA SAQLAYMIZ (SAYT BILAN BIR XIL BO'LISHI UCHUN)
        await settings_col.update_one(
            {"type": "trailer"}, 
            {"$set": {"trailer_id": file_id}}, # MUHIM: trailer_id deb yozdik
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"set_trailer xatosi: {e}")
        return False

# =====================================================================
# 5. INTEGRATSIYA (COMBINED INFO)
# =====================================================================

async def get_combined_info():
    """FastAPI (Website) uchun barcha ma'lumotlarni yig'ish"""
    try:
        info = await settings_col.find_one({"type": "info"}) or {}
        socials = await settings_col.find_one({"type": "socials"}) or {}
        logo = await settings_col.find_one({"type": "logo"}) or {}
        trailer = await settings_col.find_one({"type": "trailer"}) or {}
        
        return {
            "address": info.get("address", "Манзил киритилмаган"),
            "phone": info.get("phone", "Телефон киритилмаган"),
            "about": info.get("about", "SSS Online Shop"),
            "telegram_bot": socials.get("telegram", "#"),
            "telegram_channel": socials.get("channel", "#"),
            "instagram": socials.get("instagram", "#"),
            "whatsapp": socials.get("whatsapp", "#"),
            "logo_id": logo.get("file_id"),
            "trailer_id": trailer.get("trailer_id") # BU YERDA HAM TRAILER_ID
        }
    except Exception as e:
        logger.error(f"get_combined_info xatosi: {e}")
        return {}
