import asyncio
import os
import sys

# Optional: suppress output from dotenv if you have local files
from dotenv import load_dotenv
load_dotenv(".env.production")

from app.services.vault_service import VaultService
from app.core.secrets import get_secret_value, DB_SECRETS

async def test_db_connection():
    print("========================================")
    print("🧪 Testing Database Connection Locally")
    print("========================================\n")

    os.environ["ENVIRONMENT"] = "production"
    os.environ["INFISICAL_ENV"] = "prod"
    
    # Check auth
    token = os.getenv("INFISICAL_TOKEN", "")
    client_id = os.getenv("INFISICAL_CLIENT_ID", "")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET", "")
    has_auth = token or (client_id and client_secret)

    if not has_auth:
        print("❌ ERROR: Missing Infisical auth credentials.")
        sys.exit(1)

    print("Initializing VaultService and fetching secrets...")
    try:
        service = VaultService()
        if not service.enabled:
            print("❌ VaultService initialized, but reports as disabled.")
            sys.exit(1)
            
        secrets = service.get_secret("/database", force_refresh=True)
        if not secrets:
            print("❌ Could not retrieve secrets from /database.")
            sys.exit(1)
            
        db_user = secrets.get("POSTGRES_USER")
        db_password = secrets.get("POSTGRES_PASSWORD")
        db_host = secrets.get("POSTGRES_HOST")
        db_name = secrets.get("POSTGRES_DB")
        db_url_direct = secrets.get("DATABASE_URL")
        
        print("\n--- Fetched Database Secrets ---")
        print(f"POSTGRES_USER: {db_user}")
        print(f"POSTGRES_PASSWORD: {'*' * len(db_password) if db_password else None}")
        print(f"POSTGRES_HOST: '{db_host}'")
        print(f"POSTGRES_DB: {db_name}")
        print(f"DATABASE_URL secret exists: {bool(db_url_direct)}")
        
        # Determine the final connection string
        # This mirrors app/core/config.py resolve_database_url()
        settings_db_url = os.environ.get("DATABASE_URL")
        
        if settings_db_url and settings_db_url.strip():
            final_url = settings_db_url
            source = "environment variable"
        elif db_user and db_password and db_host and db_name:
            # We strip the host in case there are accidental spaces
            clean_host = db_host.strip()
            final_url = f"postgresql+asyncpg://{db_user}:{db_password}@{clean_host}:5432/{db_name}"
            source = "constructed from individual POSTGRES_* secrets"
        else:
            final_url = "sqlite+aiosqlite:///./commodity.db"
            source = "fallback SQLite"
            
        print(f"\n--- Final Connection String ({source}) ---")
        # Mask password
        safe_url = final_url
        if ":" in final_url and "@" in final_url and final_url.startswith("postgresql"):
            parts = final_url.split("@")
            user_pass = parts[0].split(":")
            if len(user_pass) >= 3:
                safe_url = f"{user_pass[0]}:{user_pass[1]}:********@{parts[1]}"
        print(f"URL: {safe_url}")
            
    except Exception as e:
        print("\n❌ Error retrieving secrets:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nAttempting to connect to database using SQLAlchemy...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        import socket
        
        # Test basic DNS resolution first since that's what failed on Render
        if "postgresql" in final_url:
            host = final_url.split("@")[1].split(":")[0].split("/")[0]
            print(f"Testing DNS resolution for host: '{host}'...")
            try:
                ip = socket.gethostbyname(host)
                print(f"✅ DNS resolution successful: {host} -> {ip}")
            except Exception as e:
                print(f"❌ DNS resolution FAILED: {e}")
                print(f"Hint: Make sure there are no spaces, http://, or trailing slashes in your POSTGRES_HOST secret.")
                sys.exit(1)
        
        engine = create_async_engine(final_url, echo=False)
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"🎉 SUCCESS! Connected to database.")
            print(f"Database version: {version}")
            
    except Exception as e:
        print(f"\n❌ Connection FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_db_connection())
