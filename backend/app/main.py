from fastapi import FastAPI

app = FastAPI(title="v4nex-backend", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
