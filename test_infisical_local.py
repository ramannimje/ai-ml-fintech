import os
import sys

# Optional: suppress output from dotenv if you have local files, we only care about Infisical
from dotenv import load_dotenv
load_dotenv(".env.production")

from app.services.vault_service import VaultService

def test_infisical():
    print("========================================")
    print("🧪 Testing Infisical Connection Locally")
    print("========================================\n")

    # Manually configure the environment variables that simulate Render
    # Use environment=prod to match what Render is trying to do
    os.environ["ENVIRONMENT"] = "production"
    os.environ["INFISICAL_ENV"] = "prod"
    
    # Required keys that MUST be present for the CLI to work!
    # If these are empty, we will prompt the user to fill them in.
    project_id = os.getenv("INFISICAL_PROJECT_ID", "")
    token = os.getenv("INFISICAL_TOKEN", "")
    client_id = os.getenv("INFISICAL_CLIENT_ID", "")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET", "")

    has_auth = token or (client_id and client_secret)

    if not project_id or not has_auth:
        print("❌ ERROR: Missing required environment variables.")
        print("Please ensure INFISICAL_PROJECT_ID and either INFISICAL_TOKEN or (INFISICAL_CLIENT_ID + INFISICAL_CLIENT_SECRET) are set.")
        sys.exit(1)

    print(f"✅ Loaded INFISICAL_PROJECT_ID: {project_id}")
    if token:
        print(f"✅ Loaded INFISICAL_TOKEN: {token[:10]}... (truncated for security)")
    else:
        print(f"✅ Loaded INFISICAL_CLIENT_ID: {client_id}")
        print(f"✅ Loaded INFISICAL_CLIENT_SECRET: {client_secret[:10]}... (truncated for security)")
    print(f"✅ Target Environment: {os.getenv('INFISICAL_ENV')}\n")

    print("Initializing VaultService...")
    try:
        service = VaultService()
        
        if not service.enabled:
            print("❌ VaultService initialized, but reports as disabled.")
            print("Check that the infisical CLI is installed and your token/project ID are correct.")
            sys.exit(1)

        print("✅ VaultService initialized successfully.\n")
        
        test_path = "/database"
        print(f"Fetching secrets for path: '{test_path}'...")
        
        secrets = service.get_secret(test_path, force_refresh=True)
        
        if secrets:
            print(f"🎉 SUCCESS! Retrieved {len(secrets)} secrets from {test_path}.")
            for key in secrets.keys():
                print(f"  - Found key: {key}")
        else:
            print(f"⚠️ WARNING: Request succeeded, but no secrets were returned for path '{test_path}'.")
            print("This usually means the token is valid, but the path is empty or the token doesn't have read access to this specific path.")

    except Exception as e:
        print("\n❌ FATAL ERROR during Infisical operation:")
        print(f"{type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_infisical()
