# Running workers

A worker is the process that takes jobs from the queue and runs them. Start one with:

```bash
lumen worker --concurrency 8 --pool threads
```

## Concurrency and pools

`--concurrency` sets how many jobs one worker runs at the same time; the default is the
number of CPU cores. The pool decides how: `prefork` (the default) uses separate processes
and suits CPU-heavy work; `threads` uses threads in one process and suits work that mostly
waits for the network, such as calling an API.

## Stopping a worker safely

On SIGTERM a worker stops taking new jobs and waits up to 60 seconds for running jobs to
finish; this grace period is set with `--shutdown-timeout`. Jobs still running after that
are put back on the queue and will run again, so tasks should be safe to repeat.

## Prefetch and long jobs

A worker takes `prefetch` messages at once. For jobs that run for minutes, set `prefetch`
to 1, so that one slow job does not hold back messages another worker could run.
