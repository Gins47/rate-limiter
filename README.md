# Rate limiter

A Python system-design learning project exploring rate limiting with Redis,
Lua, Nginx, and queued background work.

## Projects

| Folder                | Purpose                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| `redis-rate-limiter/` | FastAPI token-bucket service with atomic Redis Lua updates.                                                  |
| `company-b/`          | Mock vehicle-pricing API behind an Nginx rate limiter.                                                       |
| `company-a/`          | FastAPI producer and RabbitMQ consumer that fetch vehicle prices using a shared Redis moving-window limiter. |

These are separate Python projects with their own `pyproject.toml`, `uv.lock`,
and `.venv`. Run `uv` commands inside the relevant project directory. The
Company A consumer uses the `limits` library directly; it does not call the
`redis-rate-limiter` HTTP service.

## Requirements

- Python 3.13 or later for local development
- `uv`
- Docker with Docker Compose for Redis, RabbitMQ, and the provider stack

Commands below assume you start in this `rate-limiter` directory. Use separate
terminals for each long-running process. If another project's virtual
environment is activated, run `deactivate` before changing projects; `uv run`
selects the current project's environment automatically.

## Start Redis

Both Redis-based examples need Redis on `localhost:6379`. If you already have
a Redis instance there, use it. Otherwise:

```sh
docker run -d --name rate-limiter-redis -p 127.0.0.1:6379:6379 redis:7-alpine
docker exec rate-limiter-redis redis-cli PING
```

The expected response is `PONG`. To restart this container later:

```sh
docker start rate-limiter-redis
```

## Run the token-bucket service

```sh
cd redis-rate-limiter
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The Redis connection is currently configured in `app/redis_client.py` to use
`localhost:6379`, database `0`. Redis must be available when the app starts.

| Method | Endpoint          | Behavior                                                                                                    |
| ------ | ----------------- | ----------------------------------------------------------------------------------------------------------- |
| GET    | `/health`         | Returns `{"status":"ok"}`.                                                                                  |
| GET    | `/tokens`         | Reads the saved token balance and refill timestamp.                                                         |
| POST   | `/tokens/acquire` | Refills the bucket, attempts to consume one token, and returns `{"acquired":true}` or `{"acquired":false}`. |

Interactive API documentation: <http://127.0.0.1:8000/docs>.

```sh
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/tokens/acquire
curl http://127.0.0.1:8000/tokens
```

The Lua script currently allows a burst of **50 tokens** and replenishes
**10 tokens per second**. It stores state in the Redis hash
`provider:rate_limit`. Refilling happens on acquisition, so repeatedly reading
`/tokens` returns the last saved state. `last_refill` is a Unix timestamp in
milliseconds. Acquisition denial is returned as JSON with HTTP 200.

To change the bucket policy, edit `capacity` and `refill_rate` in
`app/scripts/acquire_token.lua` and keep the initial `tokens` value in
`app/main.py` consistent with capacity. A token bucket permits bursts; it does
not enforce a strict maximum in every rolling one-second window.

In another terminal, run the existing 10-request concurrency demonstration:

```sh
cd redis-rate-limiter
uv run python test/token_async_test.py
```

With a full 50-token bucket, all 10 requests can succeed. This script prints
responses and does not assert a rate-limit threshold.

To inspect the hash using the Redis container created above:

```sh
docker exec rate-limiter-redis redis-cli HGETALL provider:rate_limit
```

## Run the pricing provider

```sh
cd pricing-provider
docker compose up --build -d
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/prices/BMW-123
```

Nginx exposes port `8080` and forwards to the provider on container port
`8001`. Requests to `/prices/` are limited per client IP to **50 requests per
second**, with `burst=50 nodelay`; excess requests receive HTTP **429**.
Other paths, including `/health`, are proxied without this limit.

Run the 100-request burst demonstration from `pricing-provider/`:

```sh
uv sync
uv run python test/test_rate_limit.py
```

The script prints HTTP status counts; the exact counts depend on timing.

For local API development without Nginx, an alternative is:

```sh
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

This direct endpoint has no Nginx rate limiting. Stop the Docker provider stack
from its directory with `docker compose down`.

## Run Company A's queued workflow

Start Redis and the Docker pricing-provider stack first. Then:

```sh
cd company-a
uv sync
docker compose up -d
```

Create `company-a/.env` with these local development settings:

```dotenv
RABBITMQ_URL=amqp://admin:adminPass@localhost:5672/
RABBITMQ_QUEUE=vehicle.price.sync
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT=10/second
RATE_LIMIT_KEY=pricing-provider
PROVIDER_URL=http://127.0.0.1:8080
```

These RabbitMQ credentials match the development Compose configuration.
The environment file is local configuration and should stay out of Git.

Start the producer API from `company-a/`:

```sh
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Start the consumer in another terminal, also from `company-a/`:

```sh
uv run python -m app.consumer
```

Publish work:

```sh
curl -X POST http://127.0.0.1:8002/sync \
  -H 'Content-Type: application/json' \
  -d '{"count":100}'
```

The API queues vehicle IDs. The consumer waits for permission from its shared
Redis moving-window limiter, fetches prices through Nginx, and acknowledges
each successful message. Consumers using the same Redis database and limit key
share the configured limit. RabbitMQ's management UI is at
<http://127.0.0.1:15672> using the development credentials above.

The current consumer logs and raises processing errors, which stops that
consumer process; automatic application-level retry handling is not implemented.
Stop RabbitMQ from `company-a/` with `docker compose down`; its named volume
preserves broker data.
