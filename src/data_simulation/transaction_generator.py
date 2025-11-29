import uuid
import random
from datetime import datetime, timezone
import time
import pandas as pd
import requests

from .. import config
from ..utils import upload_df_to_s3

MERCHANT_CATEGORIES = ["groceries", "electronics", "travel", "luxury", "gaming"]
TRANSACTION_TYPES = ["online", "pos", "atm"]
GEO_LOCATIONS = ["IN-MH", "IN-KA", "IN-DL", "US-CA", "DE-BE"]


def generate_transaction() -> dict:
    amount = round(random.uniform(1, 5000), 2)
    category = random.choice(MERCHANT_CATEGORIES)
    tx_type = random.choice(TRANSACTION_TYPES)
    geo = random.choice(GEO_LOCATIONS)
    customer_id = f"cust_{random.randint(1, 1000)}"

    is_fraud = int(
        (amount > 2000 and category == "luxury")
        or (geo.startswith("US") and tx_type == "online" and amount > 1500)
    )

    return {
        "transaction_id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "amount": amount,
        "merchant_category": category,
        "transaction_type": tx_type,
        "device_id": f"dev_{random.randint(1, 2000)}",
        "geo_location": geo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_fraud": is_fraud,
    }


def generate_batch(n: int = 1000) -> pd.DataFrame:
    data = [generate_transaction() for _ in range(n)]
    return pd.DataFrame(data)


def generate_training_data_to_s3():
    df = generate_batch(5000)
    upload_df_to_s3(df, config.S3_BUCKET, config.S3_TRAIN_DATA_KEY)
    print(f"Uploaded {len(df)} rows to s3://{config.S3_BUCKET}/{config.S3_TRAIN_DATA_KEY}")


def stream_to_api(api_url: str, sleep_secs: float = 0.5):
    while True:
        tx = generate_transaction()
        payload = {k: v for k, v in tx.items() if k != "is_fraud"}
        try:
            r = requests.post(f"{api_url}/predict", json=payload, timeout=2)
            print("API response:", r.status_code, r.json())
        except Exception as e:
            print("Error calling API:", e)
        time.sleep(sleep_secs)


if __name__ == "__main__":
    generate_training_data_to_s3()
