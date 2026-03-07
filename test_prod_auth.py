import os
import sys

# Load Render prod credentials from .env.production
from dotenv import load_dotenv
load_dotenv(".env.production")

# Override to enforce prod extraction
os.environ["ENVIRONMENT"] = "production"
os.environ["INFISICAL_ENV"] = "prod"

from app.services.vault_service import VaultService

def test_prod_auth():
    print("========================================")
    print("Testing Prod Secrets Retrieval for /auth")
    print("========================================\n")

    service = VaultService()
    if not service.enabled:
        print("VaultService not enabled! Check credentials.")
        sys.exit(1)

    print("Fetching /auth path...")
    
    # Simulate exactly the VaultService path loading process
    # It fetches each key sequentially
    keys = service._path_keys("auth")
    print(f"Keys to fetch: {keys}")
    
    success_count = 0
    for key in keys:
        try:
            val = service._get_secret_value(path="/auth", key=key)
            if val:
                masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "***"
                print(f"✅ {key}: {masked}")
                success_count += 1
            else:
                print(f"⚠️ {key}: None (empty or not found)")
        except Exception as e:
            print(f"❌ {key}: ERROR - {type(e).__name__} {e}")

    print(f"\n--- DONE: {success_count}/{len(keys)} successful ---")

if __name__ == "__main__":
    test_prod_auth()
