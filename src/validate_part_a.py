
from pathlib import Path
import sqlite3

import pandas as pd


# ------------------------------------------------------------
# PROJECT PATHS
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

CUSTOMERS_FILE = ROOT / "data" / "clean" / "customers.csv"
PRODUCTS_FILE = ROOT / "data" / "clean" / "products.csv"
ORDERS_FILE = ROOT / "data" / "clean" / "orders.csv"
DATABASE_FILE = ROOT / "data" / "instamart.db"


# ------------------------------------------------------------
# LOAD CLEANED DATA
# ------------------------------------------------------------

customers = pd.read_csv(CUSTOMERS_FILE)
products = pd.read_csv(PRODUCTS_FILE)
orders = pd.read_csv(ORDERS_FILE)


# ------------------------------------------------------------
# VALIDATION CHECKPOINTS
# ------------------------------------------------------------

checks_passed = 0


def check(condition, description):
    global checks_passed

    assert condition, f"CHECK FAILED: {description}"

    checks_passed += 1
    print(f"PASSED: {description}")


# ------------------------------------------------------------
# 1. CUSTOMER DATA CHECKS
# ------------------------------------------------------------

check(
    len(customers) == 1200,
    "Customer row count is 1200"
)

expected_city_counts = {
    "Pune": 227,
    "Delhi": 210,
    "Bengaluru": 197,
    "Chennai": 191,
    "Hyderabad": 191,
    "Mumbai": 184
}

check(
    customers["city"].value_counts().to_dict() == expected_city_counts,
    "Customer city counts match reference values"
)

expected_gender_counts = {
    "female": 610,
    "male": 560,
    "unknown": 30
}

check(
    customers["gender"].value_counts().to_dict() == expected_gender_counts,
    "Customer gender counts match reference values"
)

check(
    customers["age"].notna().all(),
    "Customer ages contain no missing values"
)

check(
    customers["age"].between(18, 60).all(),
    "All customer ages are between 18 and 60"
)


# ------------------------------------------------------------
# 2. PRODUCT DATA CHECK
# ------------------------------------------------------------

check(
    len(products) == 40,
    "Product row count is 40"
)


# ------------------------------------------------------------
# 3. ORDER DATA CHECKS
# ------------------------------------------------------------

check(
    len(orders) == 12309,
    "Cleaned order row count is 12309"
)

check(
    orders["order_id"].nunique() == 12309,
    "All cleaned order IDs are unique"
)

check(
    set(orders["status"].unique()) == {"completed", "cancelled"},
    "Orders contain only completed and cancelled statuses"
)

check(
    (orders["status"] == "completed").sum() == 11110,
    "Completed order count is 11110"
)

check(
    (orders["status"] == "cancelled").sum() == 1199,
    "Cancelled order count is 1199"
)

check(
    orders["order_amount"].notna().all(),
    "Order amounts contain no missing values"
)

check(
    orders.loc[
        orders["status"] == "completed",
        "delivery_minutes"
    ].notna().all(),
    "Completed orders contain no missing delivery times"
)

check(
    orders.loc[
        orders["status"] == "cancelled",
        "delivery_minutes"
    ].isna().sum() == 1199,
    "All 1199 cancelled orders have missing delivery times"
)

completed_revenue = orders.loc[
    orders["status"] == "completed",
    "order_amount"
].sum()

check(
    round(completed_revenue, 2) == 2998668.80,
    "Completed order revenue matches INR 2,998,668.80"
)


# ------------------------------------------------------------
# 4. SQLITE DATABASE CHECKS
# ------------------------------------------------------------

connection = sqlite3.connect(DATABASE_FILE)

try:
    table_names = {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    }

    check(
        {"customers", "products", "orders"}.issubset(table_names),
        "SQLite database contains customers, products and orders tables"
    )

    database_counts = {}

    for table in ["customers", "products", "orders"]:
        database_counts[table] = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    check(
        database_counts == {
            "customers": 1200,
            "products": 40,
            "orders": 12309
        },
        "SQLite table row counts match cleaned CSV files"
    )

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    check(
        len(foreign_key_errors) == 0,
        "SQLite database has no foreign key violations"
    )

finally:
    connection.close()


# ------------------------------------------------------------
# FINAL VALIDATION RESULT
# ------------------------------------------------------------

print("\n" + "=" * 60)
print(f"CHECKPOINTS PASSED: {checks_passed}")
print("ALL CHECKPOINTS PASSED")
print("=" * 60)
