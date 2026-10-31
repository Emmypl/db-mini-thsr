# Mini THSR Backend

This project serves as the backend starter template for the Database Systems final project "Mini THSR High-Speed Rail Booking System", implemented with **Flask + PostgreSQL**. It demonstrates the end-to-end workflow: "create tables → import CSV → query data → expose API endpoints".

The starter template currently implements only the "Get Users" endpoint (`GET /users`). All other APIs (stations list, train search, booking creation, booking lookup, and cancellation) must be designed and implemented according to the course specification.

## Tech Stack

| Category | Technology |
| --- | --- |
| Language | Python 3.12 |
| Framework | Flask |
| Database | PostgreSQL 17 |
| DB Driver | psycopg 3 |
| Package Management | uv |
| Linting & Formatting | Ruff |
| Containers | Docker + Docker Compose |

## Project Structure

```text
DB_FinalProject/
├── .env.example               # Environment variable template (copy to local .env)
├── docker-compose.yml         # Defines services: db, db-init, backend, frontend
├── schema/
│   └── schema.sql             # Table creation SQL
├── data/
│   └── users.csv              # Initial users dataset
└── backend/
    ├── Dockerfile             # Backend image: Python runtime, dependencies, entrypoint
    ├── pyproject.toml         # Project config: dependencies, Ruff settings
    ├── uv.lock                # Pinned dependency lockfile
    ├── .python-version        # Target Python version used by uv
    ├── run.py                 # Backend entrypoint: starts Flask server
    ├── db_init.py             # DB initialization: schema migration + CSV import
    └── app/
        ├── __init__.py        # create_app(): initializes and configures Flask app
        ├── core/
        │   ├── config.py      # Environment variables and path resolution
        │   └── database.py    # Database connection management
        ├── api/               # Routing layer: API blueprints
        │   ├── __init__.py    # Blueprint registration
        │   └── users.py       # /users blueprint
        ├── services/          # Business logic layer: aggregates repositories, formats responses
        │   └── user_service.py
        ├── repositories/      # Data access layer: SQL queries and execution
        │   └── user_repository.py
        └── responses/         # API response data schemas
            └── user.py
```

### Request Flow

```text
HTTP Request → api (routes) → services (business logic) → repositories (SQL) → PostgreSQL
                                         ↓
HTTP Response ← api (to JSON) ← responses (schemas)
```

## Prerequisites

Install the following tools before getting started.

### uv

`uv` is an extremely fast Python package and project manager written in Rust. It manages Python versions, virtual environments (`.venv`), and project dependencies (`pyproject.toml`) with a single tool.

`uv` automatically downloads the Python version specified in `.python-version` (**no manual Python installation required**), builds an isolated virtual environment, and installs dependencies matching `uv.lock`.

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal and verify:

```bash
uv --version
```

Common commands (executed inside `backend/`):

| Command | Description |
| --- | --- |
| `uv sync` | Sets up `.venv` and installs dependencies pinned in `uv.lock` |
| `uv run <command>` | Runs a command inside the project virtual environment |
| `uv add <package>` | Adds a dependency (updates `pyproject.toml` and `uv.lock`) |
| `uv add --dev <package>` | Adds a development dependency |
| `uv remove <package>` | Removes a dependency |
| `uv lock --upgrade` | Upgrades all dependencies and rewrites `uv.lock` |

### Docker

Docker packages applications and runtime environments into lightweight, isolated containers. Docker Compose coordinates multi-container configurations.

**Windows / macOS**

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose; on Windows, enable WSL 2 integration). Ensure **Docker Desktop is running**.

**Linux**

```bash
curl -fsSL https://get.docker.com | sh       # Install Docker Engine and Compose plugin
sudo usermod -aG docker $USER                # Allow running Docker without sudo (requires re-login)
```

Verify installation:

```bash
docker --version
docker compose version
```

Common Docker commands (executed in project root):

| Command | Description |
| --- | --- |
| `docker compose up --build` | Builds container images and starts all services |
| `docker compose up -d` | Starts services in background (detached mode) |
| `docker compose ps -a` | Displays status of all containers |
| `docker compose logs -f <service>` | Streams logs for a specific service |
| `docker compose stop` | Stops running containers, retaining stored data |
| `docker compose down -v` | Tears down containers and deletes database volume (reset) |

## Getting Started

### Option 1: Run with Docker

From the project root:

```bash
docker compose up --build
```

Services boot in order: `db` (PostgreSQL) → `db-init` (creates tables and loads CSV data) → `backend` (Flask API) and `frontend` (Nginx). Add `--build` whenever modifying backend dependencies or the Dockerfile.

| Service | Access URL |
| --- | --- |
| Frontend | <http://localhost:8080/> |
| Backend API | <http://localhost:8000/users> |
| PostgreSQL | `localhost:5432` |

### Option 2: Run Backend Locally via `uv`

For daily backend development, running PostgreSQL in Docker and Flask locally on your host with `uv` provides faster feedback and instant hot-reloading:

```bash
docker compose up -d db-init     # Boots PostgreSQL and runs initialization
cd backend
uv sync                          # Installs dependencies
uv run python run.py             # Starts Flask with auto-reload
```

- Run `docker compose logs db-init` to verify initialization (`database initialized` or `already initialized, skip`).
- Press `Ctrl + C` to stop Flask.
- Run `docker compose stop` in the root folder when finished to stop PostgreSQL.

### Configuration (`.env`)

The `.env` file in the **project root** is the single source of truth for runtime configuration. Create your local config by copying `.env.example`:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEBUG` | `true` | Flask debug mode (hot reload, interactive debugger) |
| `LOG_LEVEL` | `INFO` | Minimum logging threshold |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port exposed to host |
| `DB_NAME` | `mini_thsr` | Database name |
| `DB_USER` | `postgres` | Database user account |
| `DB_PASSWORD` | `postgres` | Database user password |

> [!WARNING]
> `.env` contains credentials and is ignored by Git. Never commit `.env`; commit `.env.example` when introducing new configuration keys.

## Data Initialization

On initial startup, `db-init` runs `schema/schema.sql` and loads CSV files located in `data/`. The operation runs inside a single database transaction; failure at any step triggers a rollback. If tables already exist, initialization is skipped to prevent duplicate records.

### CSV Files

CSV datasets reside in `data/`. Filenames must match table names (e.g., `users.csv` loads into `users`). The first row must contain column headers matching table attribute names (e.g., `user_id,name,phone`), encoded in UTF-8.

### Adding a New Table

1. Add the `CREATE TABLE` statement to `schema/schema.sql`.
2. Place the initial data file in `data/<table_name>.csv`.
3. Add the table name to the `TABLES` list in [`db_init.py`](db_init.py) (respect foreign key order; referenced tables must precede dependent tables).
4. Reset and restart the database.

### Resetting the Database

Because initialization only executes when tables are absent, modifying `schema.sql`, updating CSV files, or changing credentials requires clearing the database volume:

```bash
docker compose down -v
docker compose up --build
```

## Development Workflow

Follow the architecture demonstrated by `GET /users` when creating new API endpoints.

### Layered Architecture Example: `GET /users`

Returns all users sorted by `user_id`:

```json
[
  { "user_id": "U001", "name": "Alice" },
  { "user_id": "U002", "name": "Bob" }
]
```

Layer breakdown:

| Layer | File | Responsibility |
| --- | --- | --- |
| Response | [`responses/user.py`](app/responses/user.py) | Defines response fields using `@dataclass` (`user_id`, `name`) |
| Repository | [`repositories/user_repository.py`](app/repositories/user_repository.py) | Executes SQL: `SELECT ... FROM users` |
| Service | [`services/user_service.py`](app/services/user_service.py) | Manages connection, calls repository, maps rows to response dataclass |
| API | [`api/users.py`](app/api/users.py) | Defines route `GET /users`, serializes to JSON |
| Register | [`api/__init__.py`](app/api/__init__.py) | Registers Flask blueprint for routing |

### Code Quality with Ruff

Ruff handles linting and formatting. Run these checks from `backend/` before committing:

```bash
uv run ruff check --fix .     # Lint and auto-fix violations (including import sorting)
uv run ruff format .          # Reformat code
```

VS Code users can install the [Ruff Extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) and enable formatting on save in `settings.json`:

```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll": "explicit",
    "source.organizeImports": "explicit"
  }
}
```
