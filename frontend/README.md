# Mini THSR Frontend Documentation

## 1. File Responsibilities

| File | Purpose |
| --- | --- |
| `index.html` | Train Search page: travel date, origin/destination stations, optional time filters, and train results table. |
| `booking.html` | Booking page: displays the selected train, ticket count, seat preferences, adjacent seat options, and booking result section. |
| `bookings.html` | Booking Overview page: booking ID search field and list of bookings for the current user. |
| `booking-detail.html` | Booking Details page: displays complete details of an individual booking, with a Cancel Booking button. |
| `css/style.css` | Shared styling across all four pages: colors, fonts, layout grid, buttons, tables, and mobile responsive styles. |
| `js/config.js` | User API URL and request timeout configurations. |
| `js/main.js` | Shared functionality across all four pages: fetching users, persisting user selection, reading inputs, toggling seat requirement options, rendering data, and API integration hooks. |

HTML determines content structure, CSS controls visual presentation, and JavaScript handles interactions and data. These seven files contain no backend logic or database access.

### Directory Structure and Placement

Ensure files are organized in the `frontend` directory as shown below. The folder name `frontend` can be renamed if desired, but relative paths inside it must remain consistent.

| Downloaded File Name | Target Placement |
| --- | --- |
| `index.html` | `frontend/index.html` |
| `booking.html` | `frontend/booking.html` |
| `bookings.html` | `frontend/bookings.html` |
| `booking-detail.html` | `frontend/booking-detail.html` |
| `style.css` | `frontend/css/style.css` |
| `config.js` | `frontend/js/config.js` |
| `main.js` | `frontend/js/main.js` |

Inside `frontend`, create `css` and `js` directories; the four HTML files sit in `frontend`, CSS goes into `css`, and the two JavaScript files go into `js`. This README can stay in `frontend` alongside `index.html`.

HTML files reference `css/style.css`, `js/config.js`, and `js/main.js`; navigation links also use clean HTML filenames without numbered suffixes.

## 2. Prerequisites

### Previewing the UI & Testing Frontend Interactions

Requirements:

1. The seven structured frontend files.
2. A modern JavaScript-enabled browser such as Chrome or Edge.
3. Docker Desktop or Docker Engine with Docker Compose v2.

This frontend does not require `npm install` or any frontend build tools. The official template serves static files using an Nginx container.

### Populating the User Dropdown

In addition to the above, an active user list API is required. Currently, `config.js` is set to:

```js
usersUrl: "/users"
```

This sends requests to `/users` on the current origin.

For instance, if the web page is opened at `http://localhost:8080/`, it requests `http://localhost:8080/users`. The provided Nginx configuration already proxies this path to `backend:8000/users`, so no frontend URL modifications or CORS setup are necessary.

If the user API is hosted elsewhere, change `usersUrl` in `config.js` to the target full URL. When origins or ports differ, the backend must enable Cross-Origin Resource Sharing (CORS).

### Searching Trains and Making Bookings

These features require the corresponding backend APIs to be implemented and the `TODO` hooks in `main.js` to be connected. Having the backend endpoints exist alone is not enough; the frontend must also be wired to call them.

## 3. Running the Frontend

1. Launch Docker Desktop and ensure the Docker engine is running.
2. Open a terminal and navigate to the project root directory containing `docker-compose.yml`. Do not run this from inside `frontend/`.
3. Run:

```bash
docker compose up --build frontend
```

4. Keep the terminal running. Once services have started, open your browser to:

```text
http://localhost:8080/
```

5. Confirm the page styles load properly and the top-right user dropdown populates with names. This confirms that Nginx is serving the frontend and `/users` successfully proxies to the backend.

To run containers in the background without tying up your terminal:

```bash
docker compose up -d --build frontend
```

Check status and view logs:

```bash
docker compose ps
docker compose logs -f frontend backend
```

The user dropdown calls the official backend `GET /users`. The **Load Example Stations and Trains** button on the home page, **Show Example Result** on the booking page, and **Show Example Booking Details** on the details page only load mock preview data from `examples/ui-example.js`; they do not call real APIs or persist bookings.

Page URLs:

| Page | URL |
| --- | --- |
| Train Search | `http://localhost:8080/index.html` |
| Book Tickets | `http://localhost:8080/booking.html` |
| Booking Overview | `http://localhost:8080/bookings.html` |
| Booking Details | `http://localhost:8080/booking-detail.html` |

Use the top navigation bar to switch between pages without manually editing the URL.

### Stopping the Services

Press `Ctrl+C` in the running terminal. Once stopped, cached pages may still appear in the browser, but refreshing or making API calls will fail.

### Expected Behavior After Startup

| Observation | Cause |
| --- | --- |
| Page structure, styling, and English buttons display | Frontend static files loaded successfully. |
| `Unable to load users.` | The `/users` API is unreachable or returned an error. |
| Stations show only `Select a station` | Station API is not yet connected; no static stations are hard-coded. |
| Trains or bookings display `No data available` | No data has been fetched yet. |
| Prompts such as `Booking is not available yet.` | Feature remains a TODO; API call is not yet wired up. |

## 4. Shared Operations Across All Pages

### Current User Selection

When any page opens, `loadUsers()` in `main.js` fetches the user list from the configured API.

- After loading, select a user from the top-right dropdown.
- The dropdown displays user names, while the application stores the corresponding `user_id`.
- Navigating between pages or refreshing will restore the selection, provided the origin is the same, browser storage is enabled, and the ID remains in the user list.
- Selecting `Select a user` clears the current selection.
- If loading fails, mock users will not be inserted automatically.

The `Reload` button re-fetches the user list from the API (useful for retrying after a failure). It does not reset the database or cancel bookings.

### Navigation Links

| Label | Description |
| --- | --- |
| `Train Search` | Search for available trains |
| `Book Tickets` | Ticket reservation page |
| `Booking Overview` | View list of bookings |
| `Booking Details` | Detailed view of a single booking |

Clicking `Book Tickets` or `Booking Details` directly navigates to the page without pre-selecting a train or booking. These pages typically expect parameters passed from the preceding search or overview page.

## 5. Page Operations Guide

### A. Train Search (`index.html`)

Input fields:

| Field | Description / Format |
| --- | --- |
| `Travel Date` | Required. Date picker input; submitted as `YYYY-MM-DD`. Valid range: 2026-12-01 to 2027-01-31. |
| `Departure Station` | Required origin. Populated once the Station API is connected. |
| `Arrival Station` | Required destination. Populated once the Station API is connected. |
| `Earliest Departure Time` | Optional lower bound for departure time; leave blank for no restriction. |
| `Latest Departure Time` | Optional upper bound for departure time; leave blank for no restriction. |

Operational flow once connected:

1. Select travel date, origin station, and destination station.
2. Optionally specify a departure time range. Origin and destination must not be the same; earliest time cannot be later than latest time.
3. Click `Search Trains`.
4. Inspect the results table for train numbers, departure/arrival times, and available seats.
5. Click `Book This Train` in the row to pass selected train details to the booking page.

### B. Book Tickets (`booking.html`)

The standard flow enters via clicking `Book This Train` on the search results table, which passes train number, date, stations, and times via URL query parameters.

If opened directly without URL parameters, `Selected Train` will naturally show `No data available`.

Field constraints and behavior:

| Field | Current Behavior |
| --- | --- |
| `Number of Tickets` | Required integer between 1 and 5; defaults to 1. |
| `Seat Preference` | For 1 ticket: enter `window`, `aisle`, or leave blank. |
| `Adjacent Seats` | For 2–5 tickets: checkbox to request contiguous seating. |

Constraint rules in this template:

- 1 ticket: Preference field is editable; adjacent seats checkbox is unchecked and disabled.
- 2–5 tickets: Preference field is cleared and disabled; adjacent seats checkbox becomes interactive (not automatically checked).
- Changing between 2–5 tickets: Preserves the current state of the adjacent seats checkbox.
- Switching from multiple tickets back to 1: Clears adjacent checkbox, re-enables preference input (previously cleared text is not restored).

The preference text input does not have a frontend whitelist; inputs such as `abc` or `WINDOW` can still be submitted. Validity is verified by the backend once connected. During payload preparation, empty or whitespace-only inputs become `null`, while other strings are preserved as-is.

Once connected, clicking `Confirm Booking` submits the payload. Results display under `Booking Result`. Seat allocation, remaining seats, and error reasons are determined by the backend; the frontend displays the returned data.

### C. Booking Overview (`bookings.html`)

Operational flow once connected:

1. Select the target user under `Current User`.
2. Leaving `Booking ID` empty queries all bookings for that user (including canceled ones).
3. Enter a specific booking ID to query a single reservation.
4. Click `Search Bookings`.
5. Click a booking ID or `View Details` in the table to open the details page.

Results may return multiple rows, one row, or an empty list. An empty list simply means no matching records were found.

### D. Booking Details (`booking-detail.html`)

The standard flow enters from the overview page with a `booking_id` in the URL query string.

Once connected, this page displays user, train, itinerary segment, times, ticket count, allocated seat numbers, preferences/adjacent fulfillment, and booking status.

- `Back to Booking Overview`: Returns to the overview table.
- `Cancel Booking`: Sends a request to cancel the entire booking.
- When a booking contains multiple tickets, cancellation applies to the whole booking, not individual seats.
- Once successfully canceled by the backend, the status updates to canceled and seats are released; historical records remain.

## 6. API Integration Guide (`main.js`)

Search for `TODO` in `js/main.js`. TODO comments mark locations where integration code needs to be implemented.

| Feature | Primary Location in `main.js` | Rendering Helper Function |
| --- | --- | --- |
| User list (already active) | `loadUsers()`, URL in `config.js` | Built-in option generation |
| Stations | `initializeSearch()` at `GET /stations` TODO | `renderStations(response)` |
| Train search | `initializeSearch()` at `GET /schedules` TODO | `renderSchedules(response, params)` |
| Ticket reservation | `initializeBooking()` at `POST /bookings` TODO | `renderBookingResult(response)` |
| Booking overview | `initializeBookings()` at `GET /bookings` TODO | `renderBookings(response)` |
| Single booking details | `prepareDetailLookup()` at `GET /bookings` TODO | `renderBookingDetails(response)` |
| Cancellation | `initializeDetail()` at `POST /bookings/{booking_id}/cancel` TODO | `renderBookingDetails([response])` |

Functions named `collectSearch()`, `collectBookingRequest()`, and `collectBookingsQuery()` parse and sanitize form inputs; `render...` functions render data to the DOM. They do not send network requests on their own.

Booking and query actions must use the dynamically selected `user_id` rather than a hard-coded ID. Ensure network requests, headers, payload formats, and error handling strictly follow the course API specification.

*Note on `adjacent`:* The `adjacent` field is currently a frontend draft parameter. Verify that your backend accepts this field name before final integration.

## 7. Frontend Verification Checklist

You can test these interactions immediately without backend implementation:

| Test Action | Expected Result |
| --- | --- |
| Click all four navigation links | All four pages render properly with styles applied. |
| Set ticket count to 1 on booking page | Preference input is active; adjacent seats checkbox is unchecked and disabled. |
| Enter `window` for 1 ticket, then switch to 2 tickets | Preference input is cleared and disabled; adjacent seats checkbox becomes interactive. |
| Check adjacent seats with 2 tickets, then change count to 5 | Checkbox remains checked. |
| Switch back to 1 ticket | Adjacent seats checkbox is cleared and disabled. |
| Enter `abc` into single-ticket preference | Value is accepted in input (backend will validate upon API integration). |
| Submit booking with ticket count empty, 0, 6, or 1.5 | Native browser validation blocks form submission. |
| Open booking page without URL train parameters | Selected train section indicates no data available. |
| Stop backend service | UI displays load failure message; user dropdown remains empty without mock injection. |

If user API is reachable: select a user, navigate across pages, and refresh. The selected user should remain persisted. Selecting `Select a user` should reset state.

## 8. Troubleshooting

### Text appears unstyled or misaligned?
Verify that `style.css` is located inside `frontend/css/` without duplicate or numbered filenames.

### Navigation links return 404 Not Found?
Ensure all four HTML files are placed in the root of `frontend/`: `index.html`, `booking.html`, `bookings.html`, and `booking-detail.html`.

### "Users API returned HTTP 404"?
Nginx cannot reach the backend service, the backend has not finished starting, or the `GET /users` route failed. Run `docker compose logs frontend backend` to inspect container logs.
