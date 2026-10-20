# Defining tasks

A task is a normal Python function with the `@lumen.task` decorator. Calling `.enqueue()`
on it puts a job on the queue and returns a `JobHandle` at once; the function itself runs
later, inside a worker.

```python
import lumen

@lumen.task(max_retries=5)
def send_welcome_email(user_id: int) -> None:
    ...

handle = send_welcome_email.enqueue(42)
```

Arguments must be JSON-serialisable: numbers, strings, lists and dictionaries. Pass an id,
not a database object; the worker loads the object itself.

## Retries

When a task raises an exception, Lumen tries it again up to `max_retries` times. The wait
between attempts grows: with `retry_backoff = 2.0` the waits are 1, 2, 4 and 8 seconds. An
argument on the decorator overrides the global setting for that task only. Raise
`lumen.Abort` to stop retrying at once, for example when the user no longer exists.

## Results

`handle.result(timeout=10)` waits up to ten seconds for the return value. A result is
kept for `result_ttl` seconds; after that, asking for it raises `ResultExpired`.
