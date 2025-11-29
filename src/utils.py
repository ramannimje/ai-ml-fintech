import io
import boto3
import pandas as pd
from . import config


def get_s3_client():
    return boto3.client("s3", region_name=config.AWS_REGION)


def load_csv_from_s3(bucket: str, key: str) -> pd.DataFrame:
    s3 = get_s3_client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def upload_df_to_s3(df: pd.DataFrame, bucket: str, key: str):
    s3 = get_s3_client()
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
