# Configuration

Lumen reads its settings from a `lumen.toml` file in the working directory. Every setting
can also be given as an environment variable: upper-case the name and add the prefix
`LUMEN_`, for example `LUMEN_MAX_RETRIES=5`. An environment variable always wins over the
file.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `broker_url` | `memory://` | Where the queue lives, e.g. `redis://localhost:6379/0` |
| `max_retries` | `3` | How many times a failed task is tried again |
| `retry_backoff` | `2.0` | Multiplier for the wait between two retries |
| `visibility_timeout` | `30` | Seconds a worker may hold a message before others see it again |
| `result_ttl` | `86400` | Seconds a task result is kept (one day) |
| `prefetch` | `4` | Messages a worker takes from the broker at once |

## Example file

```toml
broker_url = "redis://localhost:6379/0"
max_retries = 5
result_ttl = 3600
```

Settings are read once, when the worker starts. Restart the workers after you change them.
