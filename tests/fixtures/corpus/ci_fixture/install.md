# Installing Lumen

Lumen is a small task-queue library for Python. A web request puts a job on a queue, and a
separate worker process runs it later, so slow work such as sending e-mails or resizing
images never blocks the request.

## Requirements

Lumen needs Python 3.11 or newer and a message broker. Two brokers are supported: Redis 7
and RabbitMQ 3.13. For local experiments you can use the built-in memory broker, which
keeps every message in the worker's own process and loses them when it stops.

## Install the package

Install Lumen from PyPI with the extra for your broker:

```bash
pip install "lumen-queue[redis]"
```

Use the `rabbitmq` extra instead of `redis` for RabbitMQ. The package is called
`lumen-queue` because the name `lumen` was already taken on PyPI, but you import it as
`lumen`.

## Check the installation

Run `lumen --version` in a terminal. It prints the installed version and the Python
version it runs on. If the command is not found, the folder with your virtual
environment's scripts is not on the PATH.
