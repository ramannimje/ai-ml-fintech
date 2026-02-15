import argparse
import asyncio

from backend.app.db.session import AsyncSessionLocal
from backend.app.services.commodity_service import CommodityService


async def main(commodity: str, horizon: int) -> None:
    service = CommodityService()
    async with AsyncSessionLocal() as session:
        payload = await service.predict(session, commodity, horizon)
    print(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("commodity", choices=["gold", "silver", "crude_oil"])
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main(args.commodity, args.horizon))
