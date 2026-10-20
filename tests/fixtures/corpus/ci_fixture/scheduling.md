# Scheduling periodic tasks

Some jobs should run on a timetable: a nightly report, or cleaning old files every hour.
Lumen's scheduler is a separate process, started with `lumen beat`. It does not run tasks
itself; at the right moment it puts them on the queue for the workers.

```python
from lumen import Schedule

nightly = Schedule(cron="0 3 * * *", task="reports.build_daily")
hourly = Schedule(every=3600, task="files.clean_tmp")
```

`cron` uses the usual five fields (minute, hour, day, month, weekday). `every` takes a
number of seconds. Use one of the two, not both.

## Time zones

The scheduler reads cron times in UTC by default. Set `timezone = "Europe/Berlin"` in
`lumen.toml` to use local time instead; daylight-saving changes are then handled for you.

## Only one scheduler

Run exactly one `lumen beat` process. Two schedulers would both put every periodic job on
the queue, so each job would run twice. The scheduler keeps a lock in the broker and
refuses to start if another one already holds it.
