from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL
from bson import ObjectId

client = AsyncIOMotorClient(MONGO_URL)
db = client['sss_new_shop'] # Bazani nomini ham yangiladik
products_col = db['products']
settings_col = db['settings']

async def add_product(name, price, stock, file_id, description):
    await products_col.insert_one({
        "name": name, "price": price, "stock": stock,
        "file_id": file_id, "description": description
    })

async def get_all_products():
    return await products_col.find().to_list(length=100)

async def get_product(pid):
    try: return await products_col.find_one({"_id": ObjectId(pid)})
    except: return None

async def delete_product(pid):
    await products_col.delete_one({"_id": ObjectId(pid)})

async def decrease_stock(pid, qty):
    await products_col.update_one({"_id": ObjectId(pid)}, {"$inc": {"stock": -qty}})

async def set_product_stock(pid, new_stock):
    await products_col.update_one({"_id": ObjectId(pid)}, {"$set": {"stock": new_stock}})

async def set_shop_info(address):
    await settings_col.update_one({"type": "info"}, {"$set": {"address": address}}, upsert=True)

async def get_shop_info():
    info = await settings_col.find_one({"type": "info"})
    return info if info else {"address": "Manzil kiritilmagan"}
