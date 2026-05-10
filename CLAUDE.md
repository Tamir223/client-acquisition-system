# Client Machinery — Client Portal Build Instructions

## What You Are Building

A client portal that allows paying clients to log in, upload their leads via CSV or manual form,
and see their pipeline stats in real time. The portal connects to their individual Google Sheet
so every lead they upload flows automatically into the Make.com automation sequence.

This portal is added to the EXISTING Flask backend in this repository. Do not create a new project.

---

## Tech Stack

- **Backend**: Python Flask (already set up)
- **Auth**: Flask-Login + Werkzeug password hashing + JWT tokens
- **Database**: SQLite (simple, no extra setup, stores client accounts)
- **Frontend**: HTML + CSS + Vanilla JS (match existing style in css/style.css)
- **Google Sheets**: google-api-python-client (pipes uploaded leads to client sheet)
- **Deployment**: Render (already configured via render.yaml and Procfile)

---

## Database Schema

Create `backend/database.py` with SQLite. Tables needed:

```sql
CREATE TABLE clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  business_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  google_sheet_id TEXT,
  niche TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lead_uploads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone TEXT,
  service_requested TEXT,
  lead_source TEXT,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE activity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (client_id) REFERENCES clients(id)
);
```

---

## New Files to Create

### 1. `backend/database.py`
- SQLite connection helper
- Functions: `get_db()`, `init_db()`, `close_db()`
- Call `init_db()` on app startup

### 2. `backend/auth.py`
Flask Blueprint with these routes:

```
POST /api/portal/login
  - Body: { email, password }
  - Returns: { token, client_name, business_name }
  - Use JWT with 7-day expiry
  - Hash check with werkzeug check_password_hash

POST /api/portal/logout
  - Clears token

GET /api/portal/me
  - Requires auth header: Bearer <token>
  - Returns current client info
```

### 3. `backend/portal.py`
Flask Blueprint with these routes:

```
GET /api/portal/dashboard
  - Requires auth
  - Returns stats pulled from SQLite:
    {
      total_leads: int,
      contacted: int,
      replied: int,
      booked: int,
      recent_activity: [ last 10 activity log entries ]
    }

POST /api/portal/upload-csv
  - Requires auth
  - Accepts multipart form with CSV file
  - Parse CSV columns: First Name, Last Name, Email, Phone, Service Requested
  - Insert each row into lead_uploads table
  - Write each row to client's Google Sheet via Sheets API
  - Log to activity_log: "Uploaded X leads via CSV"
  - Return: { success: true, count: X }

POST /api/portal/add-lead
  - Requires auth
  - Body: { first_name, last_name, email, phone, service_requested }
  - Insert single lead into lead_uploads table
  - Write to client's Google Sheet
  - Log to activity_log
  - Return: { success: true }

GET /api/portal/leads
  - Requires auth
  - Returns all leads for this client from lead_uploads table
  - Order by uploaded_at DESC
  - Limit 100
```

### 4. `backend/sheets.py`
Google Sheets helper:

```python
def append_lead_to_sheet(sheet_id, lead_data):
    """
    Appends a lead row to the client's Google Sheet.
    Columns match CAS Master Tracker LEADS tab:
    A: Date Added
    B: First Name
    C: Last Name
    D: Business Name (use service_requested field)
    E: Industry (use client niche)
    F: Email
    G: Phone
    H: Lead Source (set to "Portal")
    """
```

Use service account credentials from environment variable GOOGLE_SERVICE_ACCOUNT_JSON.
The JSON should be the full service account key file content as a string.

---

## Files to Modify

### `backend/app.py`
Add to existing file:
```python
from auth import auth_bp
from portal import portal_bp
from database import init_db

app.register_blueprint(auth_bp)
app.register_blueprint(portal_bp)

with app.app_context():
    init_db()

# Serve portal pages
@app.route("/portal")
@app.route("/portal/")
def portal_login():
    return send_from_directory("../portal", "index.html")

@app.route("/portal/dashboard")
def portal_dashboard():
    return send_from_directory("../portal", "dashboard.html")
```

### `backend/requirements.txt`
Add these lines:
```
flask-login
pyjwt
google-api-python-client
google-auth
google-auth-oauthlib
```

---

## Frontend Pages to Create

### `portal/index.html` — Login Page

Clean, professional login form. Match the color scheme from css/style.css (dark navy #1E3A5F, accent blue #2E75B6).

Elements:
- Client Machinery logo/wordmark at top
- "Client Portal" subtitle
- Email input
- Password input
- "Sign In" button
- Error message area (hidden by default)
- No signup link (accounts are created by admin only)

On submit:
- POST to /api/portal/login
- Store JWT token in sessionStorage (key: "cm_token")
- Store client name in sessionStorage (key: "cm_client")
- Redirect to /portal/dashboard on success
- Show error message on failure

### `portal/dashboard.html` — Main Dashboard

Header:
- Client Machinery logo
- "Welcome, [Business Name]" 
- Sign out button (clears sessionStorage, redirects to /portal)

Stats row (4 cards):
- Total Leads Uploaded
- Contacted
- Replied
- Booked

Each card: large number, label underneath, colored border top (use accent blue for all)

Lead Upload Section:
- Tab switcher: "Upload CSV" | "Add Manually"
- CSV tab: drag and drop area + file picker button + "Upload Leads" button
  - Show preview of first 3 rows after file selected
  - Show success message with count after upload
- Manual tab: form with First Name, Last Name, Email, Phone, Service fields + "Add Lead" button

Recent Activity Feed:
- Last 10 events from activity log
- Each item: icon + description + timestamp
- Icons: upload arrow for CSV uploads, person for manual adds, envelope for emails sent, phone for calls booked

Leads Table (bottom):
- Columns: Name, Email, Phone, Service, Date Added, Status
- Last 20 leads
- Clean table with alternating row colors

On page load:
- Check sessionStorage for token — if missing redirect to /portal
- Fetch /api/portal/dashboard with Bearer token
- Fetch /api/portal/leads with Bearer token
- Populate all stats and table

### `portal/css/portal.css`
- Match existing brand colors from css/style.css
- Mobile responsive (single column on small screens)
- Clean card shadows: box-shadow: 0 2px 8px rgba(0,0,0,0.08)
- Stat cards: white background, 1px border, rounded corners (8px)
- Table: clean borders, hover highlight on rows

---

## Environment Variables to Add

Add these to Render environment variables and local .env:

```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}  # Full JSON as string
PORTAL_JWT_SECRET=<random 32 char string>
```

---

## Admin: How to Create Client Accounts

Add a simple admin script `backend/create_client.py`:

```python
# Run from command line to create a new client account
# Usage: python create_client.py

import sqlite3
from werkzeug.security import generate_password_hash
from database import get_db

def create_client(name, business_name, email, password, sheet_id, niche):
    db = get_db()
    db.execute(
        "INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche) VALUES (?, ?, ?, ?, ?, ?)",
        (name, business_name, email, generate_password_hash(password), sheet_id, niche)
    )
    db.commit()
    print(f"Client created: {business_name} ({email})")

if __name__ == "__main__":
    create_client(
        name=input("Client name: "),
        business_name=input("Business name: "),
        email=input("Email: "),
        password=input("Password: "),
        sheet_id=input("Google Sheet ID: "),
        niche=input("Niche (e.g. plumbing, trucking): ")
    )
```

---

## Google Sheets Setup (One Time)

1. Go to console.cloud.google.com
2. Create a new project named "Client Machinery Portal"
3. Enable Google Sheets API
4. Create a Service Account
5. Download the JSON key file
6. Copy the entire JSON content into GOOGLE_SERVICE_ACCOUNT_JSON env variable
7. For each client's Google Sheet: share the sheet with the service account email (it looks like xxx@xxx.iam.gserviceaccount.com)

---

## What Happens When a Client Uploads Leads

1. Client logs into portal at clientmachinery.com/portal
2. Uploads CSV or adds lead manually
3. Portal writes lead to SQLite (for dashboard stats)
4. Portal appends lead to client's Google Sheet via Sheets API
5. Make.com picks up new row in Google Sheet within 15 minutes
6. Lead gets scored by Claude (Agent 1)
7. Pain point and first line generated (Agent 2)
8. Email sequence starts automatically
9. Dashboard stats update in real time as client refreshes

---

## Build Order

Do these in order:

1. `backend/database.py` — SQLite setup and helpers
2. `backend/requirements.txt` — add new dependencies
3. `backend/auth.py` — login/logout/JWT Blueprint
4. `backend/sheets.py` — Google Sheets append helper
5. `backend/portal.py` — dashboard, upload, leads Blueprint
6. `backend/app.py` — register blueprints, serve portal pages
7. `portal/index.html` — login page
8. `portal/dashboard.html` — dashboard page
9. Test locally: python backend/app.py
10. Push to GitHub
11. Render redeploys automatically

---

## Testing Checklist

- [ ] Login with wrong password shows error
- [ ] Login with correct credentials redirects to dashboard
- [ ] Refresh on dashboard does not log out
- [ ] CSV upload with 5 leads shows success count
- [ ] Leads appear in table after upload
- [ ] Stats update after upload
- [ ] Leads appear in Google Sheet within 15 minutes
- [ ] Sign out clears session and redirects to login
- [ ] Mobile view looks clean on iPhone screen

---

## Notes

- Keep it simple. No React, no build tools, no npm. Plain HTML + CSS + JS only.
- All API calls use fetch() with Authorization: Bearer <token> header
- Error handling on every API call — show user-friendly messages not raw errors
- The portal URL is clientmachinery.com/portal
- Accounts are admin-created only — no self-signup
- Every client only sees their own data (filter all queries by client_id from JWT)
