
# 🚀 Real-Time Fraud Detection MLOps System (FinTech)

**End-to-end production-grade MLOps project built for real-time fraud detection in financial transactions.**  
This system simulates live banking transactions, scores them through an XGBoost model, detects data drift, retrains automatically, and deploys continuously using AWS, Docker, Terraform, and GitHub Actions.

A complete showcase of **machine learning engineering + MLOps + cloud deployment**.

---

## ⭐ Project Highlights (Why This Project Stands Out)

- **FinTech domain** – Realistic fraud detection use case  
- **Real-time inference API** (FastAPI + Docker + ECS Fargate)  
- **MLflow-powered experiment tracking + model registry**  
- **Automated training pipeline** (feature engineering, evaluation, registry)  
- **Data drift monitoring** using Evidently AI  
- **Automated CI/CD deployment** through GitHub Actions  
- **Infrastructure-as-Code** using Terraform (ECR, ECS, ALB, IAM, VPC, S3)  
- **Prometheus metrics + Grafana dashboard**  
- **Production-style architecture** — not a toy ML project  
- **Fully reproducible end-to-end pipeline**  

This is a **portfolio-ready FinTech MLOps system** built to demonstrate senior engineering capability.

---

# 📸 Screenshots (Showcase)

### **Fraud Detection API Screenshot**

![Fraud Detection API UI](A_screenshot_of_an_API_web_interface_displays_a_fr.png)

---

# 🧠 Architecture Overview

```
                ┌────────────────────────┐
                │ Synthetic Transaction   │
                │     Generator (Python) │
                └───────────────▲────────┘
                                │
                                ▼
                        ┌─────────────┐
                        │   S3 Bucket │◄─────────────┐
                        └───────▲─────┘              │
                                │                    │
                                │                    │
                     ┌──────────┴──────────┐   ┌─────┴───────────┐
                     │ Model Training (CI) │   │ Drift Monitor    │
                     │  XGBoost + MLflow   │   │  Evidently AI    │
                     └──────────▲──────────┘   └────────▲─────────┘
                                │                     │
                                │                     │ triggers retrain
                                ▼                     │
                     ┌─────────────────────┐          │
                     │   MLflow Registry   │──────────┘
                     └──────────▲──────────┘
                                │ deploy latest Production model
                                ▼
                         ┌─────────────┐
                         │  AWS ECR    │
                         └────▲────────┘
                              │ Docker image
                              ▼
                        ┌───────────────┐
                        │ AWS ECS Fargate│
                        │  FastAPI API  │
                        └───────▲───────┘
                                │
                                ▼
                         ┌────────────┐
                         │   Users     │
                         └────────────┘
```

---

# 🧬 End-to-End Pipeline

### **1️⃣ Data Simulation Layer**
- Generates realistic banking transactions  
- Uploads them to S3 (training + monitoring)  
- Can stream live to API  

### **2️⃣ Training Pipeline**
- Feature engineering  
- XGBoost training  
- MLflow experiment tracking  
- Model registry + Production stage transitions  
- Model artifact stored in S3  

### **3️⃣ Real-Time Inference**
- FastAPI service  
- Dockerized  
- Deployed on AWS ECS Fargate  
- Low latency predictions  

### **4️⃣ Drift Monitoring**
- Evidently AI reports  
- Feature drift  
- Data drift  
- Prediction drift  
- Auto‑retrain trigger via S3 drift flag  

### **5️⃣ CI/CD**
- GitHub Actions pipeline  
- Build → Test → Dockerize → Push to ECR → Terraform Apply → Deploy  

---

# 🛠️ Tech Stack

### **MLOps**
MLflow, Evidently AI, XGBoost

### **Backend**
FastAPI, Uvicorn, Docker

### **Cloud**
AWS ECS, ECR, S3, ALB, IAM, VPC

### **Infrastructure**
Terraform, GitHub Actions, Prometheus, Grafana

---

# 🚀 Local Setup

### **1. Install dependencies**
```
pip install -r requirements.txt
```

### **2. Start local API + MLflow**
```
docker-compose up --build
```

### **3. Generate training data**
```
python -m src.data_simulation.transaction_generator
```

### **4. Train the model**
```
python -m src.model_training.train
```

### **5. Test prediction**
```
curl -X POST http://localhost:8000/predict   -H "Content-Type: application/json"   -d '{
    "transaction_id": "t1",
    "customer_id": "c1",
    "amount": 1500,
    "merchant_category": "electronics",
    "transaction_type": "online",
    "device_id": "dev123",
    "geo_location": "IN-MH",
    "timestamp": "2024-11-01T10:00:00Z"
  }'
```

---

# 🌩️ Deploy to AWS

### **Prerequisites**
- AWS account
- IAM OIDC role for GitHub
- Terraform installed
- GitHub Secrets configured:
  - `AWS_ACCOUNT_ID`
  - `AWS_OIDC_ROLE_ARN`

### **Deploy**
Push to `main`:
```
git push
```

GitHub Actions:
- Builds Docker image  
- Pushes to ECR  
- Runs Terraform  
- Deploys to ECS  

---

# 📊 Monitoring Dashboards

- Prometheus metrics scraped at `/metrics`  
- Grafana dashboard included:  
  `monitoring/grafana-dashboard.json`

---

# 🏁 Final Notes

This project demonstrates **real-world MLOps expertise**:
- Automated retraining  
- Drift detection  
- CI/CD  
- Cloud deployment  
- ML API serving  
- Infrastructure as Code  

Perfect for showcasing production engineering skills to recruiters.
