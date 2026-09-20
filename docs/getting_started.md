# Getting Started with Ghanyx

A step-by-step guide to using the Ghanyx framework in your Python project.

---

## Requirements

- Python 3.10 or newer
- pip (usually bundled with Python)

---

## Installation

### From source (recommended during development)

```bash
git clone https://github.com/AbdelghanyElghawaty/ghanyx.git
cd ghanyx
pip install -e ".[dev]"
```

The `-e` flag installs the package in **editable mode**, so changes to
the source are reflected immediately — no reinstall needed.

The `[dev]` part installs development tools (pytest, ruff, coverage).

---

## Quick Start

### 1. Set up logging

```python
from ghanyx.logging import setup_logging, get_logger, shutdown_logging

# Call once at app startup
setup_logging(
    app_name="myapp",
    log_dir="logs",
    level="INFO",
)

logger = get_logger(__name__)

logger.info("App started")
logger.warning("Something to keep an eye on")
logger.error("Something went wrong", exc_info=True)

# Call at app exit
shutdown_logging()
```

### 2. What you get

After `setup_logging`, the framework creates:

```
logs/
├── myapp.log          # all records (DEBUG and above)
├── myapp.error.log    # only ERROR and above
└── myapp.log.1        # rotated backup when file exceeds 5 MB
```

---

## Logging Configuration Options

```python
setup_logging(
    app_name="myapp",           # used for file names
    log_dir="logs",             # where to write log files
    level="DEBUG",              # minimum level
    console=True,               # also print to terminal
    console_colors=True,        # ANSI colors in terminal
    file_logging=True,          # write to a rotating file
    error_file=True,            # separate file for ERROR+
    max_bytes=5 * 1024 * 1024,  # rotate after 5 MB
    backup_count=5,             # keep 5 backups
    capture_warnings=True,      # route warnings.warn through logging
    force=False,                # True → wipe & reconfigure
)
```

---

## Logging Levels

| Level | Numeric | When to use |
|-------|---------|-------------|
| DEBUG | 10 | Detailed diagnostics during development |
| INFO | 20 | Normal events ("user logged in") |
| WARNING | 30 | Something unexpected, but not fatal |
| ERROR | 40 | An operation failed |
| CRITICAL | 50 | The app cannot continue |

**Rule of thumb:** ship with `INFO`, debug with `DEBUG`.

---

## Examples

### Basic

```python
from ghanyx.logging import setup_logging, get_logger

setup_logging(app_name="pos", log_dir="logs")
logger = get_logger(__name__)

logger.info("Starting POS system")
```

### With exception traceback

```python
try:
    risky_operation()
except Exception:
    logger.error("Operation failed", exc_info=True)
```

### Attach custom data (JSON-friendly)

```python
logger.info("User action", extra={"user_id": 42, "action": "login"})
```

### Multiple modules

```python
# module_a.py
from ghanyx.logging import get_logger
logger = get_logger(__name__)   # → "ghanyx.module_a"

# module_b.py
from ghanyx.logging import get_logger
logger = get_logger(__name__)   # → "ghanyx.module_b"
```

---

## Custom formatters

If you need a different shape, import the formatters directly:

```python
from ghanyx.logging.formatters import (
    ConsoleFormatter,
    FileFormatter,
    JsonFormatter,
)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
```

The **JSON formatter** is useful when shipping logs to a server
(ELK, Loki, CloudWatch, etc.).

---

## Error Handling

Ghanyx ships with a small exception hierarchy:

```python
from ghanyx.errors import (
    GhanyxError,
    ConfigError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    LicenseError,
)

try:
    do_something()
except NotFoundError as e:
    logger.warning("Record missing: %s", e)
except GhanyxError as e:
    logger.error("Framework error: %s", e, exc_info=True)
```

**Catch `GhanyxError`** to handle any framework-level problem in one place.

---

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=ghanyx --cov-report=html
```

Open `htmlcov/index.html` in a browser to see the report.

---

## Project Structure

```
ghanyx/
├── src/ghanyx/
│   ├── logging/        # Logging system
│   ├── errors/         # Exception hierarchy
│   └── utils/          # Small helpers
├── tests/
├── docs/
└── pyproject.toml
```

---

## Roadmap

- [x] Logging system
- [ ] Configuration management
- [ ] Database helpers
- [ ] Auth & permissions
- [ ] License system
- [ ] UI widgets & themes
- [ ] Reports engine
- [ ] Auto-update

---

## Getting Help

- Open an issue: <https://github.com/AbdelghanyElghawaty/ghanyx/issues>
- Read the source — every module has docstrings and examples.