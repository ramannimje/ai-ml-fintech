import pandas as pd
from ..utils import load_csv_from_s3
from .. import config


def load_training_data() -> pd.DataFrame:
    return load_csv_from_s3(config.S3_BUCKET, config.S3_TRAIN_DATA_KEY)
