# cronwatcher

Lightweight daemon that monitors cron job execution and sends alerts on failures or missed runs.

## Installation

```bash
pip install cronwatcher
```

## Usage

Define your monitored jobs in a `cronwatcher.yaml` config file:

```yaml
jobs:
  backup-db:
    schedule: "0 2 * * *"
    alert_after: 10m
    notify:
      - email: ops@example.com

  sync-files:
    schedule: "*/15 * * * *"
    alert_after: 5m
    notify:
      - slack: "#alerts"
```

Start the daemon:

```bash
cronwatcher start --config cronwatcher.yaml
```

Wrap your existing cron commands to report status:

```bash
# In your crontab
0 2 * * * cronwatcher run backup-db -- /usr/local/bin/backup.sh
```

Check status of monitored jobs:

```bash
cronwatcher status
```

## Configuration

| Field | Description | Default |
|---|---|---|
| `schedule` | Cron expression for expected run time | required |
| `alert_after` | Grace period before alerting on a missed run | `5m` |
| `notify` | List of alert channels (email, slack, webhook) | `[]` |

## License

MIT