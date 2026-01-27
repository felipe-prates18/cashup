CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  is_active BOOLEAN DEFAULT 1,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS banks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  account_type TEXT NOT NULL,
  initial_balance REAL DEFAULT 0,
  is_active BOOLEAN DEFAULT 1,
  bank_id INTEGER,
  FOREIGN KEY(bank_id) REFERENCES banks(id)
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category_type TEXT NOT NULL,
  parent_id INTEGER,
  FOREIGN KEY(parent_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS cost_centers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transaction_type TEXT NOT NULL,
  date TEXT NOT NULL,
  value REAL NOT NULL,
  category_id INTEGER NOT NULL,
  account_id INTEGER NOT NULL,
  payment_method TEXT NOT NULL,
  description TEXT NOT NULL,
  client_supplier TEXT,
  document_number TEXT,
  notes TEXT,
  invoice_number TEXT,
  document_path TEXT,
  tax_id TEXT,
  created_at TEXT,
  FOREIGN KEY(category_id) REFERENCES categories(id),
  FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS titles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title_type TEXT NOT NULL,
  client_supplier TEXT NOT NULL,
  due_date TEXT NOT NULL,
  value REAL NOT NULL,
  status TEXT DEFAULT 'Pendente',
  account_id INTEGER,
  payment_method TEXT,
  notes TEXT,
  transaction_id INTEGER,
  FOREIGN KEY(account_id) REFERENCES accounts(id),
  FOREIGN KEY(transaction_id) REFERENCES transactions(id)
);

CREATE TABLE IF NOT EXISTS reconciliation_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT,
  date TEXT NOT NULL,
  description TEXT NOT NULL,
  value REAL NOT NULL,
  status TEXT DEFAULT 'Pendente',
  matched_transaction_id INTEGER,
  FOREIGN KEY(matched_transaction_id) REFERENCES transactions(id)
);

CREATE TABLE IF NOT EXISTS action_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id INTEGER,
  created_at TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
