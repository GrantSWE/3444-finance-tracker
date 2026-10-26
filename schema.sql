PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 full_name TEXT NOT NULL,
 email TEXT UNIQUE NOT NULL,
 username TEXT UNIQUE NOT NULL,
 password TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Accounts (
 account_id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 account_name TEXT NOT NULL, account_type TEXT NOT NULL CHECK(account_type IN ('Checking','Savings','Credit Card')),
 balance NUMERIC NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'USD',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Categories (
 category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL,
 category_type TEXT NOT NULL CHECK(category_type IN ('Income','Expense')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(category_name, category_type)
);
CREATE TABLE IF NOT EXISTS Saving_Goals (
 goal_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 goal_name TEXT NOT NULL, target_amt NUMERIC NOT NULL CHECK(target_amt > 0),
 current_amt NUMERIC NOT NULL DEFAULT 0 CHECK(current_amt >= 0), target_date TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Transactions (
 transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE
 title TEXT NOT NULL
 amount NUMERIC NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'USD',
 Transaction_type TEXT check(type IN ('income', 'expense')) NOT NULL,
 category text NOT NULL
 date TEXT NOT NULL
 FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON Transactions(account_id, transaction_date);
CREATE TABLE IF NOT EXISTS Budgets (
 budget_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 category_id INTEGER REFERENCES Categories(category_id) ON DELETE CASCADE,
 budget_name TEXT NOT NULL, amount NUMERIC NOT NULL CHECK(amount > 0),
 period TEXT NOT NULL CHECK(period IN ('weekly','biweekly','monthly','quarterly','yearly')),
 start_date TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS password_resets (
 reset_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS family_permissions (
 permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
 parent_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 child_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
 can_view INTEGER NOT NULL DEFAULT 1 CHECK(can_view IN (0,1)),
 can_add_transactions INTEGER NOT NULL DEFAULT 0 CHECK(can_add_transactions IN (0,1)),
 can_edit_transactions INTEGER NOT NULL DEFAULT 0 CHECK(can_edit_transactions IN (0,1)),
 can_manage_budgets INTEGER NOT NULL DEFAULT 0 CHECK(can_manage_budgets IN (0,1)),
 UNIQUE(parent_user_id, child_user_id), CHECK(parent_user_id <> child_user_id)
);
INSERT OR IGNORE INTO Categories(category_name,category_type) VALUES
('Salary','Income'),('Interest','Income'),('Other Income','Income'),('Food','Expense'),
('Housing','Expense'),('Transportation','Expense'),('Utilities','Expense'),('Healthcare','Expense'),
('Entertainment','Expense'),('Shopping','Expense'),('Other Expense','Expense');
