import asyncio
from collections import Counter
import httpx

URL = "http://localhost:8080/prices/BMW-123"

async def make_request(client:httpx.AsyncClient):
    response = await client.get(URL)
    return response.status_code


async def main():
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100)
    ) as client:
        tasks = [
            make_request(client)
            for _ in range(100)
        ]

        results = await asyncio.gather(*tasks)

        print("HTTP response counts:")
        print(Counter(results))


if __name__ == "__main__":
    asyncio.run(main())

