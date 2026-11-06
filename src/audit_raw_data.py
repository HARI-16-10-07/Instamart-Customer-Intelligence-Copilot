
from pathlib import Path
import pandas as pd

# Project directory
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


def audit_dataset(file_name):
    """Display shape, data types and missing-value statistics."""

    file_path = RAW_DIR / file_name

    # Preserve empty ticket text as empty strings
    if file_name == "tickets.csv":
        df = pd.read_csv(file_path, keep_default_na=False)
    else:
        df = pd.read_csv(file_path)

    print("\n" + "=" * 75)
    print(f"DATA AUDIT: {file_name}")
    print("=" * 75)

    print("\nDataset shape:")
    print("Rows:", df.shape[0])
    print("Columns:", df.shape[1])

    print("\nColumn data types:")
    print(df.dtypes)

    missing_count = df.isnull().sum()
    missing_percentage = (missing_count / len(df)) * 100

    missing_report = pd.DataFrame({
        "missing_count": missing_count,
        "missing_percentage": missing_percentage.round(2)
    })

    print("\nMissing-value report:")
    print(missing_report.to_string())

    return df


def main():
    print("=" * 75)
    print("INSTAMART - PART A: RAW DATA QUALITY AUDIT")
    print("=" * 75)

    files = [
        "customers.csv",
        "products.csv",
        "orders.csv",
        "tickets.csv",
        "policy_eval.csv",
        "agent_scenarios.csv"
    ]

    datasets = {}

    for file_name in files:
        datasets[file_name] = audit_dataset(file_name)

    # -------------------------------------------------
    # CUSTOMER DATA QUALITY CHECKS
    # -------------------------------------------------
    customers = datasets["customers.csv"]

    print("\n" + "=" * 75)
    print("CUSTOMER DATA QUALITY CHECKS")
    print("=" * 75)

    print("\nBlank age values:",
          customers["age"].isna().sum())

    print("Ages outside 10-100:",
          ((customers["age"] < 10) |
           (customers["age"] > 100)).sum())

    print("Distinct raw city spellings:",
          customers["city"].nunique())

    print("Distinct nonblank gender spellings:",
          customers.loc[
              customers["gender"].notna() &
              (customers["gender"].astype(str).str.strip() != ""),
              "gender"
          ].nunique())

    print("Blank gender values:",
          customers["gender"].isna().sum() +
          (customers["gender"].astype(str).str.strip() == "").sum())

    # -------------------------------------------------
    # ORDER DATA QUALITY CHECKS
    # -------------------------------------------------
    orders = datasets["orders.csv"]

    print("\n" + "=" * 75)
    print("ORDER DATA QUALITY CHECKS")
    print("=" * 75)

    print("\nRaw order rows:", len(orders))

    print("Exact duplicate rows:",
          orders.duplicated().sum())

    print("Pending orders:",
          orders["status"].astype(str).str.strip().str.lower()
          .eq("pending").sum())

    print("Distinct order IDs:",
          orders["order_id"].nunique())

    numeric_amount = pd.to_numeric(
        orders["order_amount"], errors="coerce"
    )

    print("Nonnumeric or missing order amounts:",
      numeric_amount.isna().sum())

    numeric_delivery = pd.to_numeric(
        orders["delivery_minutes"], errors="coerce"
    )

    print("Negative delivery times:",
          (numeric_delivery < 0).sum())

    print("Blank delivery times:",
          orders["delivery_minutes"].isna().sum() +
          (orders["delivery_minutes"].astype(str).str.strip() == "").sum())

    print("\n" + "=" * 75)
    print("RAW DATA AUDIT COMPLETED")
    print("=" * 75)


if __name__ == "__main__":
    main()
