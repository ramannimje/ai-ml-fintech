from datetime import datetime, timezone
import pandas as pd

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

from .. import config
from ..utils import load_csv_from_s3, upload_df_to_s3
from ..features.feature_engineering import preprocess


def load_reference_data() -> pd.DataFrame:
    return load_csv_from_s3(config.S3_BUCKET, config.S3_TRAIN_DATA_KEY)


def load_recent_data() -> pd.DataFrame:
    return load_csv_from_s3(config.S3_BUCKET, config.S3_TRAIN_DATA_KEY)


def run_drift_report():
    ref = load_reference_data()
    cur = load_recent_data()

    ref_p = preprocess(ref)
    cur_p = preprocess(cur)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_p, current_data=cur_p)

    now = datetime.now(timezone.utc)
    report_key = f"{config.S3_MONITOR_DATA_PREFIX}drift_report_{now.strftime('%Y%m%d_%H%M%S')}.html"
    df_key = f"{config.S3_MONITOR_DATA_PREFIX}drift_input_{now.strftime('%Y%m%d_%H%M%S')}.csv"

    upload_df_to_s3(cur_p, config.S3_BUCKET, df_key)

    html = report.as_html()
    import boto3

    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    s3.put_object(
        Bucket=config.S3_BUCKET,
        Key=report_key,
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )

    summary = report.as_dict()
    drift = summary["metrics"][0]["result"]["dataset_drift"]
    print("Data drift detected?", drift)

    if drift:
        s3.put_object(
            Bucket=config.S3_BUCKET,
            Key=f"{config.S3_MONITOR_DATA_PREFIX}drift_flag.txt",
            Body=f"drift_detected_at={now.isoformat()}".encode("utf-8"),
        )


if __name__ == "__main__":
    run_drift_report()
