# Mini THSR Ticket Booking System

This is a starter template for a database systems final project. It provides a working frontend UI, a Docker runtime environment, PostgreSQL, and a sample `GET /users` backend endpoint. The station, train, seat, and booking features are left for students to design and implement.

## Project Contents

```text
.
├── frontend/                 # HTML, CSS, JavaScript, and the Nginx container
├── backend/                  # Flask + psycopg backend example
├── data/                     # CSV files provided by the course
├── schema/schema.sql         # SQL for creating database tables
├── docker-compose.yml        # One-command startup configuration
└── .env.example              # Local environment configuration template
```

Scope of the current official example:

- The frontend provides pages for train search, booking, the booking list, and booking details.
- The backend only demonstrates `GET /users`, a layered structure, and parameterized SQL.
- Database initialization currently only creates and imports `users`.
- The frontend is already wired to the official `GET /users` example through Nginx.
- The station, train, and booking pages also include clearly labeled frontend-only demo data; all other official APIs remain for students to implement.

## Requirements

Recommended environment:

- Windows 10/11, macOS, or a common Linux distribution
- Docker Desktop, or Docker Engine with Docker Compose v2
- A terminal that can run the `docker compose` command
- A modern browser such as Chrome, Edge, or Firefox

You do not need to install Python, PostgreSQL, Nginx, or any frontend packages on the host.

Before starting, make sure the following ports are not in use by other programs:

| Port | Service |
| --- | --- |
| `8080` | Frontend web page |
| `8000` | Backend API |
| `5432` | PostgreSQL |

## One-Command Startup

On first use, create a local `.env` in the project root.

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

`.env` is for local use only and is ignored by Git; do not commit real accounts or passwords. Then run:

```bash
docker compose up --build
```

The first run downloads images and builds containers, so it may take a few minutes. Once the services are up, open:

- Frontend: <http://localhost:8080>
- Backend Users API: <http://localhost:8000/users>

Nginx proxies the frontend's `/users` requests to the backend, so the user menu in the top-right corner loads the users from the CSV. Stations, trains, and booking are not yet wired to official APIs; the **Load Example Stations and Trains** button on the home page is only for previewing the UI.

## Stopping and Resetting

Press `Ctrl+C` in the running terminal, then run:

```bash
docker compose down
```

PostgreSQL data is stored in a Docker volume. To delete the data and re-initialize from the CSVs:

```bash
docker compose down -v
docker compose up --build
```

`down -v` deletes this project's database volume; do not use it in an environment where booking data must be kept.

## Common Checks

View container status:

```bash
docker compose ps
```

View logs for all services:

```bash
docker compose logs -f
```

Test the backend directly, without going through the frontend or Nginx:

```bash
curl http://localhost:8000/users
```

## Development Direction

Following the course API specification, students must implement the tables, CSV import, train search, segment-based seat availability, booking, booking lookup, cancellation, and transaction and concurrency control. Do not hard-code responses based on the public data; during grading, the CSVs in `data/` will be replaced with different files of the same names.

For details on the frontend files and the places that still need to be wired up, see [`frontend/README.md`](frontend/README.md). `frontend/examples/` only contains clearly labeled UI demo data and does not replace the APIs students are expected to build.
