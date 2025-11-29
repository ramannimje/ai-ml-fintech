import mlflow
from mlflow.tracking import MlflowClient
from .. import config


def setup_mlflow():
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT_NAME)


def log_and_register_model(model, run_name: str, X_train, y_train, X_test, y_test):
    from sklearn.metrics import roc_auc_score

    setup_mlflow()

    with mlflow.start_run(run_name=run_name) as run:
        y_pred = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred)

        mlflow.log_metric("roc_auc", auc)
        mlflow.sklearn.log_model(model, "model")

        mlflow.set_tag("model_type", type(model).__name__)
        mlflow.set_tag("use_case", "fraud_detection")

        run_id = run.info.run_id
        model_uri = f"runs:/{run_id}/model"

        result = mlflow.register_model(
            model_uri=model_uri,
            name=config.MLFLOW_MODEL_NAME,
        )

    return result


def transition_model_to_production(version: int):
    client = MlflowClient(tracking_uri=config.MLFLOW_TRACKING_URI)
    client.transition_model_version_stage(
        name=config.MLFLOW_MODEL_NAME,
        version=version,
        stage="Production",
        archive_existing_versions=True,
    )
