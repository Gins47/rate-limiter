import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.redis_client import create_redis_client
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent / "scripts" / "acquire_token.lua"
lua_script = SCRIPT_PATH.read_text()

@asynccontextmanager
async def lifespan(app:FastAPI):
    client = create_redis_client()
    try:

        await client.ping()
        print("Redis connected successfully")
        await client.set("token",50,nx=True)

        # initialize token bucket
        bucket_key = "provider:rate_limit"

        if not await client.exists(bucket_key):
            current_time_ms = int(time.time() * 1000)
            await client.hset(bucket_key,mapping={
                    "tokens": 50,
                    "last_refill": current_time_ms,
            })
            print("Token bucket initialized")


        app.state.redis = client

        yield
    finally:
        await client.aclose()
        print("Redis connection closed")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tokens")
async def get_tokens(request:Request):
    client = request.app.state.redis
    result = await client.hgetall("provider:rate_limit")
    return {
        "tokens": float(result["tokens"]),
        "last_refill": int(float(result["last_refill"])),
    }

@app.post("/tokens/acquire")
async def acquire_tokens(request:Request):
    client = request.app.state.redis
    result = await client.eval(lua_script, 1, "provider:rate_limit")
    return {"acquired": bool(result)}

    # result = await client.get("token")
    # await asyncio.sleep(2)
    # tokens = int(result) if result is not None else None

    # if tokens == 0:
    #     return {"acquired":False, "remaining_tokens":0 }
    # elif tokens >= 1:
    #     remaining_tokens = await client.decr("token")
    #     return {"acquired":True,"remaining_tokens":remaining_tokens}

    

