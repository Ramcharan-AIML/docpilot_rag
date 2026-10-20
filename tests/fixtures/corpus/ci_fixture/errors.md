# Error codes and troubleshooting

Every Lumen error message starts with a code, so you can search the logs for it.

| Code | Name | What it means |
|---|---|---|
| `LMN-101` | BrokerUnreachable | The worker cannot connect to `broker_url` |
| `LMN-202` | TaskTimeout | A job ran longer than its `time_limit` and was stopped |
| `LMN-303` | SerializationError | An argument or result is not JSON-serialisable |
| `LMN-404` | UnknownTask | A job names a task that no worker has imported |

## Common fixes

`LMN-101` usually means the broker is not running, or the URL has the wrong host or port.
Test the connection with `lumen ping`.

`LMN-303` appears when you pass objects such as a datetime or a database model to
`.enqueue()`. Convert them first: a datetime to an ISO string, a model to its id.

`LMN-404` means the worker was started without the module that defines the task. Add the
module with `--include myapp.tasks` when you start the worker.

`LMN-202`: give the task a larger `time_limit` in seconds, or split the work into smaller
tasks.
