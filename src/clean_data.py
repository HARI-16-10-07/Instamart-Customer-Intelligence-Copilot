
from pathlib import Path
import pandas as pd


# ==================================================
# PROJECT PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 1. CLEAN CUSTOMER DATA
# ==================================================

def clean_customers():

    customers = pd.read_csv(RAW_DIR / "customers.csv")

    print("\nCUSTOMER DATA CLEANING")
    print("-" * 60)

    # --------------------------------------------------
    # Step 1: Record original values for cleaning counts
    # --------------------------------------------------

    original_city = customers["city"].copy()
    original_gender = customers["gender"].copy()

    blank_age_count = customers["age"].isna().sum()

    blank_gender_count = (
        customers["gender"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    # --------------------------------------------------
    # Step 2: Standardize city names
    # --------------------------------------------------

    customers["city"] = (
        customers["city"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    city_changed_count = (
        original_city.astype(str) != customers["city"]
    ).sum()

    # --------------------------------------------------
    # Step 3: Standardize gender values
    # --------------------------------------------------

    customers["gender"] = (
        customers["gender"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
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
        customers["gender"]
        .map(gender_mapping)
        .fillna("unknown")
    )

    gender_changed_count = (
        original_gender.fillna("").astype(str)
        != customers["gender"]
    ).sum()

    # --------------------------------------------------
    # Step 4: Convert age to numeric
    # --------------------------------------------------

    customers["age"] = pd.to_numeric(
        customers["age"],
        errors="coerce"
    )

    # Replace ages outside the permitted range with missing values

    invalid_age = (
        (customers["age"] < 10) |
        (customers["age"] > 100)
    )

    invalid_age_count = invalid_age.sum()

    customers.loc[invalid_age, "age"] = pd.NA

    # Count all missing ages before imputation

    ages_filled_count = customers["age"].isna().sum()

    # --------------------------------------------------
    # Step 5: Fill missing ages using city median
    # --------------------------------------------------

    customers["age"] = customers["age"].fillna(
        customers.groupby("city")["age"].transform("median")
    )

    # --------------------------------------------------
    # Step 6: Convert signup date to datetime
    # --------------------------------------------------

    customers["signup_date"] = pd.to_datetime(
        customers["signup_date"],
        errors="coerce"
    )

    # --------------------------------------------------
    # Step 7: Display customer cleaning counts
    # --------------------------------------------------

    print("Customer rows retained:", len(customers))
    print("City values standardized:", city_changed_count)
    print("Gender values standardized:", gender_changed_count)
    print("Blank customer ages:", blank_age_count)
    print("Invalid customer ages:", invalid_age_count)
    print("Missing ages filled:", ages_filled_count)
    print("Blank genders:", blank_gender_count)

    print("\nCity counts:")
    print(customers["city"].value_counts())

    print("\nGender counts:")
    print(customers["gender"].value_counts())

    print("\nMissing ages after cleaning:", customers["age"].isna().sum())

    print(
        "Age range:",
        customers["age"].min(),
        "to",
        customers["age"].max()
    )

    # --------------------------------------------------
    # Step 8: Save cleaned customers
    # --------------------------------------------------

    customers.to_csv(
        CLEAN_DIR / "customers.csv",
        index=False,
        date_format="%Y-%m-%d"
    )

    return customers


# ==================================================
# 2. CLEAN PRODUCT DATA
# ==================================================

def clean_products():

    products = pd.read_csv(RAW_DIR / "products.csv")

    print("\nPRODUCT DATA CLEANING")
    print("-" * 60)

    # Product data has no specified cleaning changes.
    # Save a clean copy for downstream processing.

    products.to_csv(
        CLEAN_DIR / "products.csv",
        index=False
    )

    print("Product rows retained:", len(products))
    print("Product cleaning changes: 0")

    return products


# ==================================================
# 3. CLEAN ORDER DATA
# ==================================================

def clean_orders(products):

    orders = pd.read_csv(RAW_DIR / "orders.csv")

    print("\nORDER DATA CLEANING")
    print("-" * 60)

    # --------------------------------------------------
    # Step 1: Convert order timestamp to datetime
    # --------------------------------------------------

    orders["order_ts"] = pd.to_datetime(
        orders["order_ts"],
        errors="coerce"
    )

    invalid_timestamps = orders["order_ts"].isna().sum()

    print("Invalid or missing timestamps:", invalid_timestamps)

    # --------------------------------------------------
    # Step 2: Remove exact duplicate rows
    # --------------------------------------------------

    exact_duplicates = orders.duplicated().sum()

    orders = orders.drop_duplicates().copy()

    print("Exact duplicate rows removed:", exact_duplicates)

    # --------------------------------------------------
    # Step 3: Resolve duplicate order IDs
    # Keep the latest timestamp for each order ID
    # --------------------------------------------------

    orders = orders.sort_values(
        "order_ts",
        ascending=True
    )

    duplicate_ids = orders["order_id"].duplicated().sum()

    orders = orders.drop_duplicates(
        subset="order_id",
        keep="last"
    ).copy()

    print("Duplicate order IDs resolved:", duplicate_ids)

    # --------------------------------------------------
    # Step 4: Remove pending orders
    # --------------------------------------------------

    original_status = orders["status"].astype(str)

    standardized_status = (
    original_status.str.strip().str.lower()
    )

    status_changed_count = (
    original_status != standardized_status
    ).sum()

    orders["status"] = standardized_status

    print("Order status values standardized:", status_changed_count)

    pending_count = (orders["status"] == "pending").sum()

    orders = orders[
        orders["status"] != "pending"
    ].copy()

    print("Pending orders removed separately:", pending_count)

    # --------------------------------------------------
    # Step 5: Convert order amount to numeric
    # --------------------------------------------------

    orders["order_amount"] = pd.to_numeric(
        orders["order_amount"],
        errors="coerce"
    )

    missing_amount = orders["order_amount"].isna()

    missing_amount_count = missing_amount.sum()

    # --------------------------------------------------
    # Step 6: Fill missing amounts using product price
    # Formula: price × quantity × (1 - discount / 100)
    # --------------------------------------------------

    price_lookup = products.set_index("product_id")["price_inr"]

    orders.loc[missing_amount, "order_amount"] = (
        orders.loc[missing_amount, "product_id"].map(price_lookup)
        * orders.loc[missing_amount, "quantity"]
        * (
            1 - orders.loc[missing_amount, "discount_pct"] / 100
        )
    ).round(2)

    print("Missing order amounts filled:", missing_amount_count)

    # --------------------------------------------------
    # Step 7: Convert delivery time to numeric
    # --------------------------------------------------

    orders["delivery_minutes"] = pd.to_numeric(
        orders["delivery_minutes"],
        errors="coerce"
    )

    # --------------------------------------------------
    # Step 8: Replace negative delivery times with missing
    # --------------------------------------------------

    negative_delivery = orders["delivery_minutes"] < 0

    negative_delivery_count = negative_delivery.sum()

    orders.loc[negative_delivery, "delivery_minutes"] = pd.NA

    print("Negative delivery times corrected:", negative_delivery_count)

    # --------------------------------------------------
    # Step 9: Attach product category
    # --------------------------------------------------

    orders = orders.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one"
    )

    # --------------------------------------------------
    # Step 10: Impute missing delivery times
    # Use category median among completed orders only
    # --------------------------------------------------

    completed_mask = orders["status"] == "completed"

    completed_orders = orders.loc[completed_mask].copy()

    missing_completed_delivery = (
        completed_orders["delivery_minutes"].isna()
    )

    missing_completed_delivery_count = (
        missing_completed_delivery.sum()
    )

    category_medians = (
        completed_orders.groupby("category")["delivery_minutes"]
        .transform("median")
    )

    completed_orders.loc[
        missing_completed_delivery,
        "delivery_minutes"
    ] = category_medians[missing_completed_delivery]

    orders.loc[completed_mask, "delivery_minutes"] = (
        completed_orders["delivery_minutes"]
    )

    print(
        "Missing completed delivery times filled:",
        missing_completed_delivery_count
    )

    # Cancelled orders retain missing delivery times.

    # --------------------------------------------------
    # Step 11: Remove temporary category column
    # --------------------------------------------------

    orders = orders.drop(columns=["category"])

    # --------------------------------------------------
    # Step 12: Format timestamp for database compatibility
    # --------------------------------------------------

    orders["order_ts"] = orders["order_ts"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------------------
    # Step 13: Save cleaned orders
    # --------------------------------------------------

    orders.to_csv(
        CLEAN_DIR / "orders.csv",
        index=False
    )

    # --------------------------------------------------
    # Step 14: Display final order cleaning results
    # --------------------------------------------------

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

    completed_total = round(
        orders.loc[
            orders["status"] == "completed",
            "order_amount"
        ].sum(),
        2
    )

    print(
        "Completed order amount total (INR):",
        completed_total
    )

    return orders


# ==================================================
# 4. MAIN EXECUTION AND REFERENCE VALIDATION
# ==================================================

def main():

    customers = clean_customers()

    products = clean_products()

    orders = clean_orders(products)

    print("\n" + "=" * 60)
    print("DATA CLEANING COMPLETED")
    print("=" * 60)

    # --------------------------------------------------
    # Customer checkpoints
    # --------------------------------------------------

    assert len(customers) == 1200

    assert customers["city"].nunique() == 6

    assert customers["gender"].value_counts().to_dict() == {
        "female": 610,
        "male": 560,
        "unknown": 30
    }

    assert customers["age"].isna().sum() == 0

    assert customers["age"].between(18, 60).all()

    # --------------------------------------------------
    # Product checkpoints
    # --------------------------------------------------

    assert len(products) == 40

    # --------------------------------------------------
    # Order checkpoints
    # --------------------------------------------------

    assert len(orders) == 12309

    assert orders["order_id"].nunique() == 12309

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
