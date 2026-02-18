from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL
from bson import ObjectId
import time

client = AsyncIOMotorClient(MONGO_URL)
db = client['sss_new_shop']
products_col = db['products']
settings_col = db['settings']
orders_col = db['orders'] # Yangi: Buyurtmalar to'plami

# --- MAHSULOTLAR (Paginatsiya bilan) ---
async def add_product(name, price, stock, file_id, description):
    await products_col.insert_one({
        "name": name, "price": price, "stock": stock,
        "file_id": file_id, "description": description
    })

async def get_products_paginated(page=0, page_size=6):
    # page 0 dan boshlanadi
    skip = page * page_size
    cursor = products_col.find().skip(skip).limit(page_size)
    products = await cursor.to_list(length=page_size)
    total_count = await products_col.count_documents({})
    return products, total_count

async def get_product(pid):
    try: return await products_col.find_one({"_id": ObjectId(pid)})
    except: return None

async def delete_product(pid):
    await products_col.delete_one({"_id": ObjectId(pid)})

async def decrease_stock(pid, qty):
    await products_col.update_one({"_id": ObjectId(pid)}, {"$inc": {"stock": -qty}})

async def set_product_stock(pid, new_stock):
    await products_col.update_one({"_id": ObjectId(pid)}, {"$set": {"stock": new_stock}})

async def get_all_products():
    # Admin uchun hammasini olish (ro'yxat uchun)
    return await products_col.find().to_list(length=1000)

# --- BUYURTMALAR (ORDER) ---
async def create_order(user_id, user_name, phone, cart, total_price, pay_method, delivery_type, location, comment):
    # Unikal 6 xonali ID yasash (Vaqt millisekundlaridan foydalanib)
    order_id = str(int(time.time() * 1000))[-6:] 
    
    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "user_name": user_name,
        "phone": phone,
        "cart": cart, # {pid: {name, price, qty}}
        "total_price": total_price,
        "pay_method": pay_method,
        "delivery_type": delivery_type,
        "location": location,
        "comment": comment,
        "status": "new", # new, processing, ready, delivered, canceled
        "created_at": time.time()
    }
    await orders_col.insert_one(order_data)
    return order_id

async def get_order_by_id(order_id):
    return await orders_col.find_one({"order_id": order_id})

async def update_order_status(order_id, new_status):
    await orders_col.update_one({"order_id": order_id}, {"$set": {"status": new_status}})

async def get_orders_by_status(status):
    return await orders_col.find({"status": status}).to_list(length=50)

# --- SOZLAMALAR ---
async def set_shop_info(address):
    await settings_col.update_one({"type": "info"}, {"$set": {"address": address}}, upsert=True)

async def get_shop_info():
    info = await settings_col.find_one({"type": "info"})
    return info if info else {"address": "Manzil kiritilmagan"}
