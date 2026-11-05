
-- Token bucket configuration
local capacity = 50
local refill_rate = 10  -- tokens per second

-- 1. Read current bucket state
local tokens = tonumber(redis.call("HGET", KEYS[1], "tokens")) or 0
local last_refill = tonumber(redis.call("HGET", KEYS[1], "last_refill"))

-- 2. Get Redis server time
local current_time = redis.call("TIME")
local now_ms = tonumber(current_time[1]) * 1000
             + tonumber(current_time[2]) / 1000

-- Initialize the bucket if it doesn't exist
if last_refill == nil then
    tokens = capacity
    last_refill = now_ms
end

-- 3. Calculate elapsed time
local elapsed_seconds = math.max(0, (now_ms - last_refill) / 1000)

-- 4. Refill tokens (maximum 50)
tokens = math.min(capacity, tokens + elapsed_seconds * refill_rate)

-- 5. Try to acquire one token
local acquired = 0

if tokens >= 1 then
    tokens = tokens - 1
    acquired = 1
end

-- 6. Persist updated state
redis.call(
    "HSET",
    KEYS[1],
    "tokens", tostring(tokens),
    "last_refill", tostring(now_ms)
)

-- 7. Return acquisition result
return acquired
