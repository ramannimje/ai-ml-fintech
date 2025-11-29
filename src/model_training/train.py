import tempfile
import joblib
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from .data_loader import load_training_data
from ..features.feature_engineering import preprocess, split_features_target
from .mlflow_utils import log_and_register_model, transition_model_to_production
from .. import config


def train_and_register():
    df = load_training_data()
    df_processed = preprocess(df)
    X, y = split_features_target(df_processed)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        use_label_encoder=False,
    )

    model.fit(X_train, y_train)

    result = log_and_register_model(
        model=model,
        run_name="xgb_fraud_detection",
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
    )

    print("Registered model version:", result.version)

    with tempfile.NamedTemporaryFile(suffix=".pkl") as tmp:
        joblib.dump(model, tmp.name)
        tmp.seek(0)
        import boto3

        s3 = boto3.client("s3", region_name=config.AWS_REGION)
        s3.upload_file(
            Filename=tmp.name,
            Bucket=config.S3_BUCKET,
            Key=config.MODEL_ARTIFACT_S3_KEY,
        )

    transition_model_to_production(result.version)
    print("Model transitioned to Production.")


if __name__ == "__main__":
    train_and_register()
