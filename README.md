# SQL Ops Dashboard

SQL Ops Dashboard is a local portfolio project that presents generated retail
operations data through a Flask application, JSON APIs, relational SQLite
storage, and a responsive browser dashboard.

The project exists to demonstrate a small, inspectable data workflow: structured
records are stored with SQL constraints, analytics views transform transactional
data, Flask transfers numeric results as JSON, and vanilla JavaScript presents
those results without a frontend framework.

## Screenshots

### Dashboard Overview
![Dashboard Overview](screenshots/01-dashboard-overview.png)

### Revenue Analysis
![Revenue Analysis](screenshots/02-revenue-analysis.png)

### Gross Margin by Product
![Gross Margin by Product](screenshots/03-gross-margin-by-product.png)

### Product Ranking and Filters
![Product Ranking and Filters](screenshots/04-product-ranking-and-filters.png)

## Main features

- Summary metrics for recognized revenue, gross margin, valid orders, and active
  products
- Product and category revenue analysis
- Product gross-margin analysis and revenue ranking
- Responsive horizontal bar charts built with HTML and CSS
- Searchable and category-filterable product table
- Loading, empty-data, and API-error states
- Accessible labels, semantic regions, live status updates, and visible keyboard
  focus
- Rebuildable SQLite database with versioned schema, seed, and analytics SQL
- Controlled database error responses and request-scoped connection cleanup
- Automated API, database integrity, foreign-key, static asset, and failure tests

## Technologies

- Python 3.10 or newer
- Flask 3
- SQLite 3
- HTML5
- CSS
- Vanilla JavaScript
- pytest

## Project structure

```text
app/
├── __init__.py          # Application factory and error handling
├── db.py                # Request-scoped SQLite access
├── routes.py            # Page, health, and JSON API routes
├── static/
│   ├── app.js           # Data retrieval, charts, filters, and UI states
│   └── styles.css       # Responsive dashboard presentation
└── templates/
    └── index.html       # Semantic single-page dashboard
data/
└── ops.db               # Ready-to-run demonstration database
screenshots/
├── 01-dashboard-overview.png
├── 02-revenue-analysis.png
├── 03-gross-margin-by-product.png
└── 04-product-ranking-and-filters.png
scripts/
├── __init__.py
└── init_db.py           # Atomic database rebuild utility
sql/
├── schema.sql           # Tables, constraints, relationships, and indexes
├── seed.sql             # Generated demonstration records
└── views.sql            # Reusable analytics views
tests/
├── conftest.py          # Temporary database and Flask fixtures
├── test_app.py          # Page, asset, API, ordering, total, and error tests
└── test_database.py     # Rebuild, integrity, and foreign-key tests
.gitignore
README.md
requirements.txt
requirements-dev.txt
run.py
```

## Database schema

The database uses seven related tables:

- `customers` stores generated customer names and reserved demonstration email
  addresses.
- `suppliers` stores generated supplier records and active status.
- `categories` classifies products.
- `products` references categories and suppliers and stores cost, price, and
  active status.
- `inventory_movements` records inbound, outbound, and adjustment quantities.
- `orders` references customers and restricts status values with a `CHECK`
  constraint.
- `order_items` connects orders to products, validates positive quantities, and
  cascades when an order is deleted.

SQLite foreign-key enforcement is enabled for application and initialization
connections. Indexes cover the foreign-key columns used in joins and the order
status used by analytics filters.

Money is stored as integer cents in transactional tables. API queries convert it
to numeric dollar values at the presentation boundary.

## Analytics views

- `revenue_by_product` aggregates paid and shipped order revenue by product.
- `revenue_by_category` aggregates recognized revenue by category.
- `margin_by_product` calculates revenue, product cost, and gross margin.
- `product_revenue_rank` applies a SQL window function to rank product revenue.
- `dashboard_summary` returns the four top-level dashboard metrics.

`CANCELLED`, `REFUNDED`, and uncompleted `PLACED` orders are excluded from
recognized revenue and margin.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Render the dashboard |
| `GET` | `/health` | Confirm Flask and SQLite availability |
| `GET` | `/api/summary` | Return overview metrics |
| `GET` | `/api/revenue/products` | Return product revenue in descending order |
| `GET` | `/api/revenue/categories` | Return category revenue |
| `GET` | `/api/margins/products` | Return product revenue, cost, and margin |
| `GET` | `/api/rankings/products` | Return ranked product revenue |

API money values are JSON numbers in US dollars, not formatted strings. Currency
formatting is applied in the browser.

## Installation on macOS or Linux

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Install only runtime dependencies with
`python -m pip install -r requirements.txt` when tests are not needed.

## Installation on Windows PowerShell

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If PowerShell blocks local activation scripts, the environment's Python can be
called directly as `.\.venv\Scripts\python.exe`.

## Initialize the database

Rebuild the default database from the three SQL files:

```bash
python scripts/init_db.py
```

An optional output path creates a separate database and any missing parent
directories:

```bash
python scripts/init_db.py data/portfolio-copy.db
```

The utility builds and validates a temporary database before atomically replacing
the requested output file. A failed rebuild leaves the previous database in
place and returns a non-zero exit status.

## Run the application

Start the local server from the repository root:

```bash
python run.py
```

Then open <http://127.0.0.1:5000>. Debug mode is disabled by default. Flask's
development command is also supported:

```bash
flask --app app run --debug
```

The application runs locally and is not currently hosted.

## Run the tests

```bash
python -m pytest -q
```

Tests rebuild and use temporary SQLite databases. They do not modify
`data/ops.db`.

## What this project demonstrates

- Python backend development with an application factory, type hints, logging,
  and focused modules
- Flask routing, template rendering, static file delivery, and JSON APIs
- Relational database design for customers, suppliers, products, inventory, and
  orders
- SQL constraints, foreign keys, cascades, and query-supporting indexes
- SQL views, grouped analytics, gross-margin calculations, and window-function
  ranking
- Data retrieval and transfer from SQLite through Flask to the browser
- Frontend presentation with responsive, accessible HTML, CSS, and vanilla
  JavaScript

## Demonstration data

Every customer, supplier, product, inventory movement, order, and contact address
in this repository is generated demonstration data. Email addresses use reserved
example domains and should not be treated as real contact information.
