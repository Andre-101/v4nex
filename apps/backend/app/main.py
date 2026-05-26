from fastapi import FastAPI

app = FastAPI(title="v4nex-backend", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_v4nex/health")
def internal_health() -> dict[str, str]:
    return {"status": "ok"}
