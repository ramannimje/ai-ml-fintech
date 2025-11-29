# Real-Time Fraud Detection MLOps (FinTech)

End-to-end MLOps project for real-time transaction fraud detection in a fintech setting.

## Stack

- Model: XGBoost binary classifier for fraud detection
- Serving: FastAPI + Docker + AWS ECS Fargate
- Experiment Tracking & Registry: MLflow
- Monitoring: Evidently (data drift) + Prometheus metrics
- Infra as Code: Terraform (ECR, ECS, S3, IAM, VPC, ALB)
- CI/CD: GitHub Actions
- Cloud Storage: S3 for data and model artifacts

## Quickstart (Local)

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install --upgrade pip
pip install -r requirements.txt

# Start MLflow + API
docker-compose up --build
```

See the full README content in the repo for detailed instructions.
