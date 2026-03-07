import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get('https://query2.finance.yahoo.com/v8/finance/chart/GC=F', headers={'User-Agent': 'Mozilla/5.0'})
            data = r.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            print("YF Gold Price:", price)
        except Exception as e:
            print("YF Error:", e)

asyncio.run(test())
