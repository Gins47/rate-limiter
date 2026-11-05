
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.producer import publish_vehicle_ids


app = FastAPI(title="Company A - Vehicle Marketplace")


class SyncRequest(BaseModel):
    count: int = Field(default=1000, ge=1, le=10000)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/sync")
async def start_sync(request: SyncRequest):
    published = await publish_vehicle_ids(request.count)

    return {
        "status": "queued",
        "published": published,
        "queue": "vehicle.price.sync",
    }
