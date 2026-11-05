import asyncio
import httpx


async def main():
    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
            client.post("http://localhost:8000/tokens/acquire"),
        )

        for response in responses:
            print(response.json())


asyncio.run(main())