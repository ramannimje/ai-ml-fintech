import asyncio
from app.db.session import AsyncSessionLocal
from app.services.commodity_service import CommodityService

async def debug_train():
    service = CommodityService()
    print("Methods available:", [m for m in dir(service) if not m.startswith('_')])

asyncio.run(debug_train())
