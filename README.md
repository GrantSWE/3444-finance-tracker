# Financial Tracker

A web based personal finance application being developed for **CSCE 3444 – Software Engineering** by **The Regal Eagles**.

## Team

- Grant Johosky
- Duncan Wrenn
- Johnny Zhou

## Overview

Financial Tracker is designed to help users keep track of their spending, budgets, income, and savings in one place. Users will be able to enter transactions manually and view their financial activity through a simple dashboard.

## Tech Stack

- **Frontend:** HTML, CSS
- **Backend:** Python, Flask
- **Database:** SQLite

Flask will handle the application logic and communication between the user interface and database. SQLite will store account information, transactions, budgets, savings goals, and other application data.

## Planned Features

- User registration and login
- Password recovery
- Add, edit, and remove transactions
- Custom spending categories
- Budget creation and progress tracking
- Income and savings tracking
- Savings goals
- Financial dashboard
- Spending visualizations
- Weekly, bi-weekly, monthly, quarterly, and yearly views
- Parent and child account permissions

## How It Will Work

Users will manually enter financial information such as transactions, income, budgets, and savings goals.

The **Flask backend** will process this information and store it in the **SQLite database**. Transaction data will then be used to calculate and display information such as:

- Total income and expenses
- Net profit
- Budget progress
- Savings progress
- Recent transactions
- Spending summaries and visualizations

Parent accounts will have management access to linked child accounts, while child accounts will have more limited, view-focused permissions.

## Project Status

**Active Development**

The core Flask project structure has been established, and the public homepage, shared layouts, partials, and styling have been implemented. The project repository is now set up for group development.

Current development is focused on building the authentication system, including login and registration, followed by the SQLite database and dashboard functionality.

## Password Recovery Configuration

The password recovery flow sends a one-time link that expires after 15 minutes by default. Copy the values from `.env.example` into your local environment and replace every placeholder before sending real email.

Required production settings:

- `SECRET_KEY`: a long random value used to sign recovery tokens and sessions
- `APP_BASE_URL`: the public application URL, including `https://`
- `MAIL_USERNAME` and `MAIL_PASSWORD`: SMTP credentials (use an app password when required)
- `MAIL_DEFAULT_SENDER`: the address shown in recovery email
- `SESSION_COOKIE_SECURE=true`: required when the deployed site uses HTTPS

For local PowerShell development, set a variable for the current terminal before starting Flask:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-value"
$env:MAIL_USERNAME = "your-email@example.com"
$env:MAIL_PASSWORD = "your-email-app-password"
$env:MAIL_DEFAULT_SENDER = "your-email@example.com"
$env:APP_BASE_URL = "http://127.0.0.1:5000"
python app.py
```

Do not commit real passwords or a production `SECRET_KEY`.

## Tests

Run all token, password-recovery, authentication, dashboard, and transaction regression tests with:

```powershell
python -m unittest discover -s tests -v
```
