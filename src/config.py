import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
S3_BUCKET = os.getenv("S3_BUCKET", "fraud-mlops-models")
S3_TRAIN_DATA_KEY = os.getenv("S3_TRAIN_DATA_KEY", "data/train/transactions.csv")
S3_MONITOR_DATA_PREFIX = os.getenv("S3_MONITOR_DATA_PREFIX", "data/monitoring/")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "fraud-detection")
MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "fraud_detection_model")

MODEL_ARTIFACT_S3_KEY = os.getenv(
    "MODEL_ARTIFACT_S3_KEY",
    "models/fraud_detection/latest/model.pkl"
)

PROMETHEUS_NAMESPACE = "fraud_detection_service"

ENV = os.getenv("ENV", "local")
