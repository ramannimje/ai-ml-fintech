from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    merchant_category: str
    transaction_type: str
    device_id: str
    geo_location: str
    timestamp: datetime


class PredictionResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    is_fraud: bool
    model_version: Optional[str] = None
