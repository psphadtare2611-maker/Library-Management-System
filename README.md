# Library Management System

A professional desktop application to manage a personal home library — track the
books you own, the friends who borrow them, and the complete borrowing history so
you always know **who has which book and since when**.

---

## Features

- Add, update, remove, and search books
- Register borrowers (friends)
- Issue books and return books
- Track complete borrowing history
- Generate reports (currently borrowed, overdue, most-borrowed, per-borrower)

## Tech Stack

- **Python** — core language
- **Tkinter** — desktop GUI
- **SQL Server** — relational database
- **pyodbc** — Python ↔ SQL Server connectivity
- **OOP + layered MVC** — clean, maintainable architecture

---

## Architecture (layered MVC)

```
ui/  ──►  services/  ──►  database/ (repositories)  ──►  SQL Server
 │            │                    │
 └── views    └── business rules   └── SQL + entities (models/)
```

- **config/**    — settings and the database connection string
- **database/**  — connection handling, schema, and repositories (all SQL lives here)
- **models/**    — plain data classes (Book, Borrower, Transaction)
- **services/**  — business logic and rules (issue/return, reports)
- **ui/**        — Tkinter screens and reusable widget components
- **utils/**     — validators, date helpers, custom exceptions
- **reports/**   — report generation and exported files
- **assets/**    — icons and images

---

## Project Structure

```
Library Management System/
├── main.py                # Application entry point
├── requirements.txt
├── README.md
├── .gitignore
├── config/                # Settings & connection config
├── database/              # Connection, schema, repositories (SQL)
├── models/                # Entity classes
├── services/              # Business logic
├── ui/                    # Tkinter screens
│   └── components/        # Reusable widgets
├── utils/                 # Validators, helpers, exceptions
├── reports/               # Report generation + exports
└── assets/                # Icons and images
```

---

## Setup (once the code is implemented)

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Configure your SQL Server connection in `config/settings.py`.
3. Create the database tables using `database/schema.sql`.
4. Run the app:
   ```
   python main.py
   ```

---

## Status

🚧 Project scaffolding stage — folder structure and file stubs are in place.
Functionality is implemented in phases (see the development roadmap).
