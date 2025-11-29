import time
import io
import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from ..schemas import Transaction, PredictionResponse
from ..features.feature_engineering import preprocess
from ..monitoring.prometheus_metrics import (
    PREDICTION_COUNTER,
    PREDICTION_LATENCY,
)
from .. import config
from ..utils import get_s3_client

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Fraud Detection API")

_model = None
_model_version = "unknown"


def load_model_from_s3():
    s3 = get_s3_client()
    buf = io.BytesIO()
    s3.download_fileobj(config.S3_BUCKET, config.MODEL_ARTIFACT_S3_KEY, buf)
    buf.seek(0)
    return joblib.load(buf)


@app.on_event("startup")
def startup_event():
    global _model
    _model = load_model_from_s3()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/predict", response_model=PredictionResponse)
def predict(tx: Transaction):
    global _model
    if _model is None:
        _model = load_model_from_s3()

    start = time.time()

    df = pd.DataFrame([tx.dict()])
    df["is_fraud"] = 0
    df_processed = preprocess(df)
    X = df_processed.drop(columns=["is_fraud"], errors="ignore")

    prob = float(_model.predict_proba(X)[:, 1][0])
    is_fraud = prob > 0.5

    latency = time.time() - start
    PREDICTION_COUNTER.inc()
    PREDICTION_LATENCY.observe(latency)

    return PredictionResponse(
        transaction_id=tx.transaction_id,
        fraud_probability=prob,
        is_fraud=is_fraud,
        model_version=_model_version,
    )


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
