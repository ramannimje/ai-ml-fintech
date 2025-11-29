import pandas as pd

CATEGORICAL_COLS = ["merchant_category", "transaction_type", "geo_location"]
NUMERIC_COLS = ["amount"]
TARGET_COL = "is_fraud"


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_COLS:
        df[col] = df[col].fillna(0)
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)
    return df


def split_features_target(df: pd.DataFrame):
    y = df[TARGET_COL].values
    drop_cols = [TARGET_COL, "transaction_id", "customer_id", "device_id", "timestamp"]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    return X, y
