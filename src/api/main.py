from fastapi import FastAPI
from src.api.zapier_test_endpoints import router as zapier_router

app = FastAPI()
app.include_router(zapier_router)


# Optional root endpoint
@app.get("/")
def read_root():
    return {"status": "ok"}
