# Ghanyx

> A modular Python framework for building desktop business applications.

**Ghanyx** provides reusable building blocks for desktop apps: logging,
configuration, database helpers, licensing, UI widgets, and more.
Built on top of **PySide6**.

---

## Why Ghanyx?

Most business apps repeat the same core needs:

- User authentication & permissions
- Database access & migrations
- Logging & error handling
- Licensing & activation
- Themes & UI widgets
- Reports & exports
- Backups & updates

**Ghanyx** gives you all of this in one place, so you focus on
your business logic, not on plumbing.

---

## Status

🚧 **Alpha** — under active development.

---

## Installation

```bash
pip install ghanyx
```

Or, in development mode:

```bash
git clone https://github.com/AbdelghanyElghawaty/ghanyx.git
cd ghanyx
pip install -e ".[dev]"
```

---

## Quick Start

```python
from ghanyx.logging import setup_logging

setup_logging(app_name="myapp", log_dir="logs")
```

---

## Structure

```
src/ghanyx/
├── logging/     # Unified logging system
├── config/      # Configuration management
├── database/    # SQLite helpers
├── errors/      # Custom exceptions
└── utils/       # General utilities
```

---

## Roadmap

- [x] Logging system
- [ ] Configuration management
- [ ] Database helpers & migrations
- [ ] User auth & permissions
- [ ] License system (RSA-based)
- [ ] UI themes & widgets
- [ ] Reports engine (Excel / PDF)
- [ ] Auto-update mechanism

---

## License

MIT © Abdelghany Elghawaty