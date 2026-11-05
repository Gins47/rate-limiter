from fastapi import FastAPI

app = FastAPI(title="Vehicle Pricing Provider")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/prices/{vehicle_id}")
async def get_vehicle_price(vehicle_id: str):
    return {
        "vehicle_id": vehicle_id,
        "currency": "EUR",
        "market_price": 18500,
    }