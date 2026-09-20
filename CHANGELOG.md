# Changelog

All notable changes to **Ghanyx** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Configuration management module
- Database helpers & migrations
- User authentication & permissions
- License system (RSA-based)
- UI themes & widgets
- Reports engine (Excel / PDF)
- Auto-update mechanism

---

## [0.1.0] — 2026-09-21

### Added

#### Logging system (`ghanyx.logging`)
- `setup_logging()` — one-call configuration for the whole app
- `get_logger()` — namespaced loggers under `ghanyx.*`
- `shutdown_logging()` — clean shutdown of all handlers
- `is_configured()` — check setup state
- Idempotent setup (safe to call multiple times)
- `force=True` option to wipe & reconfigure
- Automatic `atexit` cleanup

#### Handlers (`ghanyx.logging.handlers`)
- `SafeRotatingFileHandler` — Windows-friendly rotation that never crashes
- `make_console_handler()` — colored terminal output
- `make_file_handler()` — rotating log file
- `make_error_file_handler()` — separate file for ERROR+ only

#### Formatters (`ghanyx.logging.formatters`)
- `ConsoleFormatter` — colored, human-friendly output
- `FileFormatter` — detailed, timestamped output
- `JsonFormatter` — machine-readable, ships to aggregation systems

#### Errors (`ghanyx.errors`)
- `GhanyxError` — base exception class
- `ConfigError` — configuration problems
- `DatabaseError`, `NotFoundError`, `DuplicateError`, `IntegrityError`
- `LoggingError`
- `ValidationError`
- `AuthenticationError`, `PermissionDeniedError`
- `LicenseError`, `LicenseExpiredError`, `LicenseInvalidError`,
  `LicenseDeviceMismatchError`

#### Utilities (`ghanyx.utils`)
- `ensure_dir()` — safe directory creation
- `get_app_data_dir()` — cross-platform per-user data directory
- `get_project_root()` — project root detection
- `safe_filename()` — sanitize arbitrary strings into safe filenames

#### Testing
- 18 unit tests covering logging, formatters, namespacing, shutdown
- Unicode / Arabic log message coverage
- Windows-safe rotation tested

### Notes
- Python 3.10+ required
- No external runtime dependencies except `python-dotenv`

---

## [0.0.0] — 2026-09-21

- Initial scaffolding (empty project structure)