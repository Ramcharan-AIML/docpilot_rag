# Monitoring

A queue that silently fills up is a common production failure, so Lumen exposes numbers
you can watch.

## Metrics endpoint

Start a worker with `--metrics-port 9187` and it serves Prometheus metrics at
`http://localhost:9187/metrics`. The most useful ones are `lumen_queue_depth` (jobs
waiting), `lumen_job_seconds` (how long jobs take) and `lumen_failures_total` (jobs that
failed after their last retry).

## Health checks

`lumen ping` sends a test message through the broker and waits for a worker to answer. It
exits with code 0 when a worker replied within five seconds, and with code 1 otherwise, so
it works as a container health check.

## What to alert on

Alert when `lumen_queue_depth` keeps growing for ten minutes: workers are too slow or
stopped. Alert when `lumen_failures_total` jumps: a deploy may have broken a task. Watch
the 95th percentile of `lumen_job_seconds`, not only the average, because a few very slow
jobs hide inside a good average.
