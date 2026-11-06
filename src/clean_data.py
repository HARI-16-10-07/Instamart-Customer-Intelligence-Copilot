
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 1. CLEAN CUSTOMER DATA
# --------------------------------------------------

def clean_customers():

    customers = pd.read_csv(RAW_DIR / "customers.csv")

    print("\nCUSTOMER DATA CLEANING")
    print("-" * 60)

    # Standardize city names
    customers["city"] = (
        customers["city"].astype(str).str.strip().str.title()
    )

    # Standardize gender values
    customers["gender"] = (
        customers["gender"].fillna("").astype(str).str.strip().str.lower()
    )

    gender_mapping = {
        "male": "male",
        "m": "male",
        "man": "male",
        "female": "female",
        "f": "female",
        "woman": "female"
    }

    customers["gender"] = (
        customers["gender"].map(gender_mapping).fillna("unknown")
    )

    # Convert age to numeric
    customers["age"] = pd.to_numeric(
        customers["age"], errors="coerce"
    )

    # Replace ages outside the permitted range with missing values
    invalid_age = (
        (customers["age"] < 10) |
        (customers["age"] > 100)
    )

    customers.loc[invalid_age, "age"] = pd.NA

    # Fill missing ages using the median age of each city
    customers["age"] = customers["age"].fillna(
        customers.groupby("city")["age"].transform("median")
    )

    # Convert signup date to datetime
    customers["signup_date"] = pd.to_datetime(
        customers["signup_date"], errors="coerce"
    )

    # Save cleaned customers
    customers.to_csv(
        CLEAN_DIR / "customers.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    print("Cleaned customer rows:", len(customers))
    print("\nCity counts:")
    print(customers["city"].value_counts())

    print("\nGender counts:")
    print(customers["gender"].value_counts())

    print("\nMissing ages:", customers["age"].isna().sum())
    print(
        "Age range:",
        customers["age"].min(),
        "to",
        customers["age"].max()
    )

    return customers


# --------------------------------------------------
# 2. CLEAN PRODUCT DATA
# --------------------------------------------------

def clean_products():

    products = pd.read_csv(RAW_DIR / "products.csv")

    # Product data has no specified cleaning changes.
    # Save a clean copy for downstream processing.
    products.to_csv(
        CLEAN_DIR / "products.csv",
        index=False
    )

    print("\nPRODUCT DATA")
    print("-" * 60)
    print("Cleaned product rows:", len(products))

    return products


# --------------------------------------------------
# 3. CLEAN ORDER DATA
# --------------------------------------------------

def clean_orders(products):

    orders = pd.read_csv(RAW_DIR / "orders.csv")

    print("\nORDER DATA CLEANING")
    print("-" * 60)

    # Convert order timestamp to datetime
    orders["order_ts"] = pd.to_datetime(
        orders["order_ts"], errors="coerce"
    )

    # Step 1: Remove exact duplicate rows
    exact_duplicates = orders.duplicated().sum()
    orders = orders.drop_duplicates().copy()

    print("Exact duplicate rows removed:", exact_duplicates)

    # Step 2: For duplicate order IDs, keep the latest timestamp
    orders = orders.sort_values(
        "order_ts", ascending=True
    )

    duplicate_ids = orders["order_id"].duplicated().sum()

    orders = orders.drop_duplicates(
        subset="order_id",
        keep="last"
    ).copy()

    print("Duplicate order IDs resolved:", duplicate_ids)

    # Step 3: Remove pending orders
    pending_count = (
        orders["status"].astype(str).str.strip().str.lower()
        .eq("pending").sum()
    )

    orders = orders[
        orders["status"].astype(str).str.strip().str.lower()
        != "pending"
    ].copy()

    orders["status"] = (
        orders["status"].astype(str).str.strip().str.lower()
    )

    print("Pending orders removed:", pending_count)

    # Step 4: Convert order amount to numeric
    orders["order_amount"] = pd.to_numeric(
        orders["order_amount"], errors="coerce"
    )

    # Step 5: Fill missing amounts using product price
    price_lookup = products.set_index("product_id")["price_inr"]

    missing_amount = orders["order_amount"].isna()

    orders.loc[missing_amount, "order_amount"] = (
        orders.loc[missing_amount, "product_id"].map(price_lookup)
        * orders.loc[missing_amount, "quantity"]
        * (
            1 - orders.loc[missing_amount, "discount_pct"] / 100
        )
    ).round(2)

    print("Missing amounts filled:", missing_amount.sum())

    # Step 6: Convert delivery time to numeric
    orders["delivery_minutes"] = pd.to_numeric(
        orders["delivery_minutes"], errors="coerce"
    )

    # Replace negative delivery times with missing values
    negative_delivery = orders["delivery_minutes"] < 0

    print("Negative delivery times corrected:", negative_delivery.sum())

    orders.loc[negative_delivery, "delivery_minutes"] = pd.NA

    # Step 7: Attach product category for delivery-time imputation
    orders = orders.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one"
    )

    # Fill missing delivery times only for completed orders,
    # using the median delivery time of their product category.
    completed_mask = orders["status"] == "completed"

    completed_orders = orders.loc[completed_mask].copy()

    category_medians = (
        completed_orders.groupby("category")["delivery_minutes"]
        .transform("median")
    )

    missing_completed_delivery = (
        completed_orders["delivery_minutes"].isna()
    )

    completed_orders.loc[
        missing_completed_delivery, "delivery_minutes"
    ] = category_medians[missing_completed_delivery]

    orders.loc[completed_mask, "delivery_minutes"] = (
        completed_orders["delivery_minutes"]
    )

    # Remove temporary category column
    orders = orders.drop(columns=["category"])

    # Format timestamp for database compatibility
    orders["order_ts"] = orders["order_ts"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Save cleaned orders
    orders.to_csv(
        CLEAN_DIR / "orders.csv",
        index=False
    )

    print("\nCleaned order rows:", len(orders))
    print("\nFinal order status counts:")
    print(orders["status"].value_counts())

    print(
        "\nMissing order amounts:",
        orders["order_amount"].isna().sum()
    )

    print(
        "Missing completed delivery times:",
        orders.loc[
            orders["status"] == "completed",
            "delivery_minutes"
        ].isna().sum()
    )

    print(
        "Missing cancelled delivery times:",
        orders.loc[
            orders["status"] == "cancelled",
            "delivery_minutes"
        ].isna().sum()
    )

    print(
        "Completed order amount total (INR):",
        round(
            orders.loc[
                orders["status"] == "completed",
                "order_amount"
            ].sum(),
            2
        )
    )

    return orders


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

def main():

    customers = clean_customers()

    products = clean_products()

    orders = clean_orders(products)

    print("\n" + "=" * 60)
    print("DATA CLEANING COMPLETED")
    print("=" * 60)

    # Reference checkpoint validation
    assert len(customers) == 1200
    assert len(products) == 40
    assert len(orders) == 12309

    assert orders["status"].value_counts().to_dict() == {
        "completed": 11110,
        "cancelled": 1199
    }

    assert orders["order_amount"].isna().sum() == 0

    assert orders.loc[
        orders["status"] == "completed",
        "delivery_minutes"
    ].isna().sum() == 0

    assert orders.loc[
        orders["status"] == "cancelled",
        "delivery_minutes"
    ].isna().sum() == 1199

    completed_total = round(
        orders.loc[
            orders["status"] == "completed",
            "order_amount"
        ].sum(),
        2
    )

    assert completed_total == 2998668.80

    print("\nALL CLEANING CHECKPOINTS PASSED")


if __name__ == "__main__":
    main()
