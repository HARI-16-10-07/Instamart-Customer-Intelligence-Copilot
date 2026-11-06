import sqlite3
from pathlib import Path
from itertools import combinations

import pandas as pd

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "instamart.db"
SQL_PATH = BASE_DIR / "sql" / "queries.sql"
CLEAN_DIR = BASE_DIR / "data" / "clean"

# --------------------------------------------------
# 2. Read and separate the seven SQL queries
# --------------------------------------------------

sql_text = SQL_PATH.read_text(encoding="utf-8")

statements = []

for raw_statement in sql_text.split(";"):
    cleaned_lines = [
        line for line in raw_statement.splitlines()
        if not line.strip().startswith("--")
    ]

    statement = "\n".join(cleaned_lines).strip()

    if statement:
        statements.append(statement)

assert len(statements) == 7, (
    f"Expected 7 SQL queries, but found {len(statements)}."
)

# --------------------------------------------------
# 3. Execute all seven queries using SQLite
# --------------------------------------------------

connection = sqlite3.connect(DB_PATH)

query_results = {}

try:
    for number, statement in enumerate(statements, start=1):
        result = pd.read_sql_query(statement, connection)
        query_results[number] = result

        print("\n" + "=" * 65)
        print(f"SQL QUERY {number}")
        print("=" * 65)
        print("Rows returned:", len(result))
        print(result.head(10).to_string(index=False))

finally:
    connection.close()

# --------------------------------------------------
# 4. Validate SQL reference results
# --------------------------------------------------

print("\n" + "=" * 65)
print("SQL REFERENCE CHECKS")
print("=" * 65)

assert len(query_results[1]) == 30
print("Q1: 30 customers found.")

assert len(query_results[2]) == 30
print("Q2: 30 city-category combinations found.")

q2 = query_results[2]
revenue_column = next(
    column for column in q2.columns
    if "revenue" in column.lower()
)

assert abs(q2[revenue_column].sum() - 2998668.80) < 0.01
print(f"Q2: Total revenue = INR {q2[revenue_column].sum():,.2f}")

assert len(query_results[3]) == 11
print("Q3: 11 products are above average catalogue price.")

assert len(query_results[4]) == 25
print("Q4: 25 customers have no completed orders.")

assert len(query_results[5]) == 550
print("Q5: 550 customers are above average spend.")

q6 = query_results[6]
print("Q6: City-wise customer ranking query executed.")
print("Q6 columns:", list(q6.columns))

q7 = query_results[7]
assert len(q7) == 183
print("Q7: 183 days of completed-order revenue returned.")

print("\nAll seven SQL queries executed successfully.")

# --------------------------------------------------
# 5. Pandas cross-check: city and category revenue
# --------------------------------------------------

customers = pd.read_csv(CLEAN_DIR / "customers.csv")
products = pd.read_csv(CLEAN_DIR / "products.csv")
orders = pd.read_csv(CLEAN_DIR / "orders.csv")

orders["order_ts"] = pd.to_datetime(orders["order_ts"])

completed = orders[orders["status"] == "completed"].copy()

completed_details = (
    completed
    .merge(customers[["customer_id", "city"]], on="customer_id")
    .merge(products[["product_id", "category"]], on="product_id")
)

pivot = pd.pivot_table(
    completed_details,
    index="city",
    columns="category",
    values="order_amount",
    aggfunc="sum",
    fill_value=0,
    margins=True,
    margins_name="Grand Total"
)

print("\n" + "=" * 65)
print("PANDAS CROSS-CHECK 1: CITY AND CATEGORY REVENUE")
print("=" * 65)
print(pivot.to_string())

grand_total = pivot.loc["Grand Total", "Grand Total"]

assert abs(grand_total - 2998668.80) < 0.01
print(f"\nPandas grand total: INR {grand_total:,.2f}")

# --------------------------------------------------
# 6. Pandas cross-check: city-level aggregation
# --------------------------------------------------

city_summary = (
    completed_details
    .groupby("city")
    .agg(
        total_revenue_inr=("order_amount", "sum"),
        average_order_amount_inr=("order_amount", "mean"),
        completed_order_count=("order_id", "count")
    )
    .reset_index()
)

print("\n" + "=" * 65)
print("PANDAS CROSS-CHECK 2: CITY SUMMARY")
print("=" * 65)
print(city_summary.to_string(index=False))

print("\nBengaluru and Mumbai reference rows:")
print(
    city_summary[
        city_summary["city"].isin(["Bengaluru", "Mumbai"])
    ].to_string(index=False)
)

# --------------------------------------------------
# 7. Completed order amount statistics and outliers
# --------------------------------------------------

amount = completed["order_amount"]

q1 = amount.quantile(0.25)
q3 = amount.quantile(0.75)
iqr = q3 - q1
lower_fence = q1 - (1.5 * iqr)
upper_fence = q3 + (1.5 * iqr)

print("\n" + "=" * 65)
print("COMPLETED ORDER AMOUNT STATISTICS")
print("=" * 65)

print(f"Mean: INR {amount.mean():.2f}")
print(f"Median: INR {amount.median():.2f}")
print(f"Skewness: {amount.skew():.2f}")
print(f"Q1: INR {q1:.2f}")
print(f"Q3: INR {q3:.2f}")
print(f"IQR: INR {iqr:.2f}")
print(f"Lower fence: INR {lower_fence:.2f}")
print(f"Upper fence: INR {upper_fence:.2f}")
print("Values above upper fence:", int((amount > upper_fence).sum()))
print("Values below lower fence:", int((amount < lower_fence).sum()))

# --------------------------------------------------
# 8. Correlation analysis
# --------------------------------------------------

correlation_columns = [
    "order_amount",
    "discount_pct",
    "quantity",
    "delivery_minutes"
]

correlation_data = completed[correlation_columns].corr()

print("\n" + "=" * 65)
print("CORRELATION MATRIX")
print("=" * 65)
print(correlation_data.round(3).to_string())

pairs = []

for first, second in combinations(correlation_columns, 2):
    value = correlation_data.loc[first, second]
    pairs.append((first, second, value))

strongest_pair = max(pairs, key=lambda item: abs(item[2]))

print(
    "\nLargest absolute correlation:",
    strongest_pair[0],
    "and",
    strongest_pair[1],
    "=",
    round(strongest_pair[2], 3)
)

print("\nPART A SQL AND PANDAS ANALYSIS COMPLETED.")