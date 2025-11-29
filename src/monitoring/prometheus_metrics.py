from prometheus_client import Counter, Histogram
from .. import config

PREDICTION_COUNTER = Counter(
    f"{config.PROMETHEUS_NAMESPACE}_predictions_total",
    "Total number of predictions",
)

PREDICTION_LATENCY = Histogram(
    f"{config.PROMETHEUS_NAMESPACE}_prediction_latency_seconds",
    "Latency of prediction endpoint",
)
