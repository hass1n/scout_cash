# ⚜️ Scout Sandou2 - Money Management Web Application

A Flask web application designed for Scout group treasury management, tracking **Incomes (واردات)**, **Expenses (مصاريف)**, and live cash box balances across dual currencies: **USD ($)** and **Lebanese Pounds (LBP / ل.ل)**.

---

## 🔐 Login Credentials
Access is strictly restricted to the authorized leadership account:
- **Email:** `sahmarany.hassan11@gmail.com`
- **Password:** `1234`

---

## 🌟 Key Features

1. **Dual Currency Wallets (USD & LBP)**:
   - Separate balances for USD and LBP cash boxes.
   - Real-time calculations:
     - `USD Wallet Balance = Total Income (USD) - Total Expenses (USD)`
     - `LBP Wallet Balance = Total Income (LBP) - Total Expenses (LBP)`

2. **Income & Outcome Tracking**:
   - **Incomes**: Logs amount, currency, **"From Who"** (donor, dues, activity), category, date, and notes.
   - **Expenses**: Logs amount, currency, **"For What"** (supplies, equipment, food, rent), category, date, and notes.

3. **📅 "This Month" One-Click Quick View**:
   - Displays all incomes received this month with source details and total sums.
   - Displays all expenses spent this month with purpose details and total sums.
   - Highlights the net monthly surplus/deficit alongside the current total wallet balance.

4. **Date Range & Multi-Factor Filtering**:
   - Filter transactions between any two dates (`From Date` & `To Date`).
   - Quick preset buttons: `All Time`, `This Month`, `Today`, `This Year`.
   - Filter by Currency (`USD`, `LBP`, or `All`).
   - Filter by Type (`Income`, `Expense`, or `All`).

5. **Split Breakdown Tabs**:
   - **All Transactions**: Master ledger with inline edit and delete actions.
   - **Incomes ("From Who")**: Dedicated ledger focusing on incoming funds.
   - **Expenses ("For What")**: Dedicated ledger focusing on troop expenses.

6. **Export & Print**:
   - Export filtered transactions to CSV format with a single click.
   - Clean, printer-friendly layout for printing or saving to PDF.

7. **English & Arabic Interface**:
   - Switch between English and Arabic from the language control on any page.
   - Arabic mode translates the interface and uses right-to-left layout; English mode uses left-to-right layout.

---

## 🚀 How to Run

1. Open your terminal in this project folder:
   ```bash
   cd c:\Users\lenovo\Desktop\sandou2
   ```

2. (Optional) Re-seed or reset sample transactions:
   ```bash
   python seed_data.py
   ```

3. Run the Flask application:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

5. Sign in with:
   - Email: `sahmarany.hassan11@gmail.com`
   - Password: `1234`

---

## ☁️ Deploying on Render

The repo includes a `render.yaml` Blueprint that creates a web service plus a PostgreSQL database.

1. In the Render dashboard choose **New → Blueprint** and connect this repository.
2. When prompted, enter a strong `ADMIN_PASSWORD` (the `1234` default only applies locally).
3. Render sets `DATABASE_URL` and `SECRET_KEY` automatically.

When `DATABASE_URL` is set the app stores data in PostgreSQL; otherwise it uses the local `scout_finance.db` SQLite file.

---

## 🧪 Running Tests
To run the automated test suite:
```bash
python test_app.py
```
