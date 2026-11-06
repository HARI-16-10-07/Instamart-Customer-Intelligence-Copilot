
from pathlib import Path
import sqlite3

import pandas as pd


# --------------------------------------------------
# 1. PROJECT SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = PROJECT_ROOT / "data" / "instamart.db"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_DATE = pd.Timestamp("2025-09-01")
SEPTEMBER_END = pd.Timestamp("2025-10-01")


# --------------------------------------------------
# 2. LOAD DATA FROM SQLITE
# --------------------------------------------------

connection = sqlite3.connect(DATABASE_PATH)

customers = pd.read_sql_query(
    "SELECT * FROM customers",
    connection
)

orders = pd.read_sql_query(
    "SELECT * FROM orders",
    connection
)

products = pd.read_sql_query(
    "SELECT product_id, category FROM products",
    connection
)

connection.close()

orders["order_ts"] = pd.to_datetime(orders["order_ts"])
customers["signup_date"] = pd.to_datetime(
    customers["signup_date"]
)

print("Customers loaded:", len(customers))
print("Orders loaded:", len(orders))


# --------------------------------------------------
# 3. IDENTIFY THE HISTORICAL COHORT
# --------------------------------------------------

# Only completed and cancelled orders before
# 1 September 2025 are considered.

pre_cutoff_orders = orders[
    (orders["order_ts"] < CUTOFF_DATE)
    & (orders["status"].isin(["completed", "cancelled"]))
].copy()

# A customer belongs to the cohort if they had
# at least one completed order before the cutoff.

eligible_customers = pre_cutoff_orders[
    pre_cutoff_orders["status"] == "completed"
]["customer_id"].unique()

cohort = customers[
    customers["customer_id"].isin(eligible_customers)
].copy()

print("\nEligible customer cohort:", len(cohort))


# --------------------------------------------------
# 4. CREATE THE LAPSE TARGET
# --------------------------------------------------

# Completed orders during September 2025.

september_orders = orders[
    (orders["order_ts"] >= CUTOFF_DATE)
    & (orders["order_ts"] < SEPTEMBER_END)
    & (orders["status"] == "completed")
]

active_in_september = set(
    september_orders["customer_id"].unique()
)

# Lapsed = 1 if the customer had no completed
# order during September 2025.

cohort["lapsed"] = (
    ~cohort["customer_id"].isin(active_in_september)
).astype(int)


# --------------------------------------------------
# 5. CALCULATE PRE-CUTOFF ORDER FEATURES
# --------------------------------------------------

# Separate completed and cancelled orders.

completed_orders = pre_cutoff_orders[
    pre_cutoff_orders["status"] == "completed"
].copy()

cancelled_orders = pre_cutoff_orders[
    pre_cutoff_orders["status"] == "cancelled"
].copy()


# Merge product category into completed orders.

completed_orders = completed_orders.merge(
    products,
    on="product_id",
    how="left"
)


# RFM FEATURES

rfm_features = completed_orders.groupby(
    "customer_id"
).agg(
    last_completed_order=("order_ts", "max"),
    frequency=("order_id", "nunique"),
    monetary=("order_amount", "sum")
).reset_index()

# Recency = cutoff date - last completed order date.

rfm_features["recency"] = (
    CUTOFF_DATE - rfm_features["last_completed_order"]
).dt.days


# AVERAGE DISCOUNT

# Calculate average discount using completed orders only.

discount_features = completed_orders.groupby(
    "customer_id"
).agg(
    avg_discount=("discount_pct", "mean")
).reset_index()


# CANCELLATION RATE

# Denominator = all final-status orders:
# completed + cancelled.

order_counts = pre_cutoff_orders.groupby(
    "customer_id"
).agg(
    total_orders=("order_id", "nunique")
).reset_index()

cancel_counts = cancelled_orders.groupby(
    "customer_id"
).agg(
    cancelled_orders=("order_id", "nunique")
).reset_index()

cancellation_features = order_counts.merge(
    cancel_counts,
    on="customer_id",
    how="left"
)

cancellation_features["cancelled_orders"] = (
    cancellation_features["cancelled_orders"].fillna(0)
)

cancellation_features["cancellation_rate"] = (
    cancellation_features["cancelled_orders"]
    / cancellation_features["total_orders"]
)


# AVERAGE DELIVERY TIME

# Only completed pre-cutoff orders are used.

delivery_features = completed_orders.groupby(
    "customer_id"
).agg(
    avg_delivery=("delivery_minutes", "mean")
).reset_index()


# FAVORITE CATEGORY

# Category with the highest number of completed orders.
# Alphabetical order resolves ties.

category_counts = (
    completed_orders.groupby(
        ["customer_id", "category"]
    )
    .size()
    .reset_index(name="category_order_count")
)

favorite_category = (
    category_counts.sort_values(
        ["customer_id", "category_order_count", "category"],
        ascending=[True, False, True]
    )
    .drop_duplicates("customer_id")
    [["customer_id", "category"]]
    .rename(columns={"category": "favorite_category"})
)


# --------------------------------------------------
# 6. COMBINE ALL FEATURES
# --------------------------------------------------

feature_tables = [
    rfm_features,
    discount_features,
    cancellation_features[
        ["customer_id", "cancellation_rate"]
    ],
    delivery_features,
    favorite_category
]

dataset = cohort[
    ["customer_id", "city", "age", "gender", "signup_date", "lapsed"]
].copy()

for feature_table in feature_tables:
    dataset = dataset.merge(
        feature_table,
        on="customer_id",
        how="left"
    )

# Tenure is calculated at the historical cutoff.

dataset["tenure_days"] = (
    CUTOFF_DATE - dataset["signup_date"]
).dt.days

dataset = dataset.drop(columns=["signup_date"])


# --------------------------------------------------
# 7. CHECK MISSING VALUES
# --------------------------------------------------

feature_columns = [
    "recency",
    "frequency",
    "monetary",
    "avg_discount",
    "cancellation_rate",
    "avg_delivery",
    "favorite_category",
    "city",
    "age",
    "gender",
    "tenure_days"
]

print("\nMISSING VALUES IN FEATURES:")
print(dataset[feature_columns].isnull().sum())
assert dataset[feature_columns].isnull().sum().sum() == 0, (
    "Missing values detected in lapse features!"
)

print("PASS: No missing values in feature columns.")
print("\nLAPSE CLASS DISTRIBUTION:")
print(dataset["lapsed"].value_counts().sort_index())

print("\nLAPSE PERCENTAGE:")
print(
    (dataset["lapsed"].value_counts(normalize=True) * 100)
    .sort_index()
    .round(2)
)


# --------------------------------------------------
# 8. SAVE THE DATASET
# --------------------------------------------------

output_columns = [
    "customer_id",
    "recency",
    "frequency",
    "monetary",
    "avg_discount",
    "cancellation_rate",
    "avg_delivery",
    "favorite_category",
    "city",
    "age",
    "gender",
    "tenure_days",
    "lapsed"
]

dataset[output_columns].to_csv(
    OUTPUT_DIR / "lapse_dataset.csv",
    index=False
)


# --------------------------------------------------
# 9. FINAL SUMMARY
# --------------------------------------------------

print("\nDATASET SHAPE:", dataset.shape)
print("TOTAL COHORT CUSTOMERS:", len(dataset))
print("LAPSED CUSTOMERS:", int(dataset["lapsed"].sum()))
print(
    "NOT LAPSED CUSTOMERS:",
    int((dataset["lapsed"] == 0).sum())
)

print("\nSaved: outputs/lapse_dataset.csv")
print("\nLAPSE DATASET PREPARATION COMPLETED")
