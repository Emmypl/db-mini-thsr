# Mini THSR Ticket Booking System

This is a starter template for a database systems final project. It provides a working frontend UI, a Docker runtime environment, PostgreSQL, and working `GET /users`, `GET /stations` and `GET /schedules` endpoints. Seat availability and booking APIs remain to be implemented.

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

Current implementation:

- The frontend provides pages for train search, booking, the booking list, and booking details.
- The backend implements `GET /users`, `GET /stations` and `GET /schedules` through a layered structure and handwritten SQL.
- Database initialization creates the full schema, imports users, stations and timetables, and generates seats and dated train runs.
- The frontend loads users and stations from the backend through Nginx.
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

Nginx proxies the frontend's `/users` requests to the backend, so the user menu in the top-right corner loads the users from the CSV. Stations load automatically from the database. Train search now queries the backend; booking is not implemented yet; the **Load Example Stations and Trains** button on the home page is only for previewing the UI.

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

## Timetable initialization

On a fresh database, initialization imports all three course CSVs in one transaction. Station IDs come from stations.csv; northbound stops are ordered in travel direction. Each car receives four rows of A–E seats. Train runs are generated for operating weekdays from 2026-12-01 through 2027-01-31.

A successful import is marked transactionally in the train_runs table comment. Subsequent starts skip import and preserve bookings, even if the CSV files are unavailable. An empty, complete schema can also be populated. Legacy, incomplete, or populated unmarked databases fail with a migration message; they are never automatically erased. If preserving existing data matters, apply a reviewed migration rather than resetting the database.

This change imports reference data; seat availability and booking APIs are not implemented yet. See tests/README.md for PostgreSQL integration tests.

## Station list

`GET http://localhost:8000/stations` returns HTTP 200 and an array containing only `station_id` and `name`, ordered by the station's north-to-south `seq`. An empty database returns `[]`. No user selection or login is required. Nginx also forwards `/stations` on port 8080, and the search page loads both station dropdowns automatically. Loading failures display an error; reload the page to retry. Explicitly selected UI demo data remains a separate preview.

## Train search

`GET /schedules` requires date (YYYY-MM-DD), from_station_id and to_station_id. Optional departure_time_from and departure_time_to use HH:MM with inclusive bounds at the requested departure station. Results are ordered by departure time, then train number. Each result contains train_no, date, departure_time, arrival_time and remain_seats.

Only runs on the requested date stopping at both stations in travel order match. No matches, including dates outside the operating period, return HTTP 200 with an empty array. Invalid or missing parameters and unknown/equal stations return HTTP 422 with error.code INVALID_PARAMETER.

Remaining seats are counted across the whole journey using confirmed bookings for the same train and date. Adjoining intervals do not overlap. Cancelled bookings do not block seats. Sold-out trains remain in the results. This read-only availability is a snapshot, not a reservation; transactional booking is a later implementation step.

The search form and Nginx `/schedules` proxy are connected. Example request after starting the application:

```sh
curl 'http://localhost:8000/schedules?date=2026-12-07&from_station_id=TPE&to_station_id=TXG'
```
