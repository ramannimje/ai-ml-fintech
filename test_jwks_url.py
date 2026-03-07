import httpx
import asyncio

async def test():
    # Simulate exactly what the backend does
    raw_domain = "dev-mrxlgcmm2f0itm0g.us.auth0.com  "
    print(f"[{raw_domain}]")
    domain = raw_domain
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.startswith("http://"):
        domain = domain[7:]
    
    url = f"https://{domain}/.well-known/jwks.json"
    print(f"Fetching: [{url}]")
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get(url)
            print("Status:", r.status_code)
        except Exception as e:
            print("Error:", type(e).__name__, e)

asyncio.run(test())
