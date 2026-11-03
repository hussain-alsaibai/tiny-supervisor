# tiny-supervisor

> Zero-dependency process supervisor for Python. Keep your agents, webhooks, and workers running.

## Why?

You're running an autonomous agent or a webhook server in a container. It crashes. You don't want to install `systemd` in Docker or set up `supervisord` with a complex config file.

**tiny-supervisor** is a single Python file that supervises a command, handles restarts with backoff, and cleans up on exit.

## 📦 Install

```bash
pip install tiny-supervisor
```

Or just copy `tiny_supervisor.py` into your project - it has **zero dependencies**.

## Usage

```python
from tiny_supervisor import Supervisor

# Supervise a command with 5 restarts and 10s delay
sup = Supervisor(
    command=["node", "webhook.js"],
    restarts=5,
    delay=10
)

sup.start()

# Process runs in a background thread. 
# Keep the main thread alive or wait for the supervisor.
import time
try:
    while sup.running:
        time.sleep(1)
except KeyboardInterrupt:
    sup.stop()
```

## Features

- **Automatic Restarts**: Retries on failure up to `restarts`.
- **Delay**: Configurable wait time between restarts.
- **Threaded**: Runs monitor in a daemon thread.
- **Clean Shutdown**: Terminates child process on stop.
- **Zero Deps**: Stdlib only.

## 🧪 Testing

```bash
python -m pytest tests/
```

## 📄 License

MIT - see [LICENSE](LICENSE).

---

Built by [Hussain Al-Saibai](https://github.com/hussain-alsaibai) as part of the [`dev-masterkit`](https://github.com/hussain-alsaibai/dev-masterkit) ecosystem.
