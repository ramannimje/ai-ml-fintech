from pathlib import Path


def test_contract_alignment_backend_vs_frontend() -> None:
    backend_schema = Path("app/schemas/responses.py").read_text(encoding="utf-8")
    frontend_client = Path("frontend/src/api/client.ts").read_text(encoding="utf-8")

    required_backend_fields = [
        "commodity",
        "region",
        "unit",
        "currency",
        "live_price",
        "source",
        "timestamp",
    ]
    for field in required_backend_fields:
        assert field in backend_schema

    required_frontend_zod = [
        "livePriceSchema",
        "historicalSchema",
        "predictionSchema",
    ]
    for schema_name in required_frontend_zod:
        assert schema_name in frontend_client
