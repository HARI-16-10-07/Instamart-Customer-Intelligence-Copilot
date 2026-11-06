
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"

print("\nPART B VALIDATION")
print("=" * 60)


# --------------------------------------------------
# 1. Check required output files
# --------------------------------------------------

required_files = [
    "customer_segments.csv",
    "lapse_dataset.csv",
    "lapse_model.joblib",
    "retention_list.csv",
]

for filename in required_files:
    filepath = OUTPUTS / filename
    assert filepath.exists(), f"Missing file: {filename}"
    print(f"PASS: {filename} exists")


# --------------------------------------------------
# 2. Validate customer segments
# --------------------------------------------------

segments = pd.read_csv(OUTPUTS / "customer_segments.csv")

required_segment_columns = {
    "customer_id",
    "recency",
    "frequency",
    "monetary",
    "segment_id",
    "segment_name",
    "is_premium",
}

assert required_segment_columns.issubset(segments.columns), (
    "Required customer segment columns are missing"
)

assert segments["customer_id"].is_unique, (
    "Duplicate customer IDs found in customer segments"
)

assert segments["segment_name"].notna().all(), (
    "Missing segment names found"
)

assert segments["monetary"].notna().all(), (
    "Missing monetary values found"
)

# Convert Premium flags safely into True/False
premium_flags = (
    segments["is_premium"]
    .astype(str)
    .str.strip()
    .str.lower()
    .map({
        "1": True,
        "true": True,
        "0": False,
        "false": False,
    })
)

assert premium_flags.notna().all(), (
    "Invalid Premium flag values"
)

segments["is_premium"] = premium_flags

# Calculate mean monetary value and customer count
# for every segment
segment_profiles = segments.groupby(
    ["segment_id", "segment_name"]
).agg(
    customer_count=("customer_id", "count"),
    mean_monetary=("monetary", "mean"),
)

# Identify the segment with the highest mean monetary value
highest_monetary_segment = (
    segment_profiles["mean_monetary"].idxmax()
)

highest_monetary_segment_id = highest_monetary_segment[0]
highest_monetary_segment_name = highest_monetary_segment[1]

# Identify segments marked as Premium
premium_segment_ids = segments.loc[
    segments["is_premium"], "segment_id"
].unique()

# Exactly one segment must be marked Premium
assert len(premium_segment_ids) == 1, (
    "Exactly one segment must be marked Premium"
)

# Premium must be the segment with the highest mean monetary value
assert premium_segment_ids[0] == highest_monetary_segment_id, (
    "Premium is not the segment with the highest mean monetary value"
)

# Verify every customer in the highest-monetary segment
# is Premium, and no other customer is Premium
expected_premium_flags = (
    segments["segment_id"] == highest_monetary_segment_id
)

assert segments["is_premium"].equals(expected_premium_flags), (
    "Premium flags do not match the highest-monetary segment"
)

premium_count = int(segments["is_premium"].sum())

assert premium_count == int(
    segment_profiles.loc[
        highest_monetary_segment,
        "customer_count"
    ]
)

print(f"\nSegment records: {len(segments)}")

print("\nSEGMENT PROFILES:")
print(segment_profiles)

print(f"\nPremium customers: {premium_count}")
print(f"Premium segment: {highest_monetary_segment_name}")

print(
    "Highest mean monetary value:",
    round(
        segment_profiles.loc[
            highest_monetary_segment,
            "mean_monetary"
        ],
        2
    )
)

print("PASS: Premium is exactly the highest-monetary segment")
print("PASS: Customer segments validated")


# --------------------------------------------------
# 3. Validate lapse dataset
# --------------------------------------------------

lapse_data = pd.read_csv(OUTPUTS / "lapse_dataset.csv")

assert "customer_id" in lapse_data.columns
assert "lapsed" in lapse_data.columns

assert lapse_data["customer_id"].is_unique, (
    "Duplicate customer IDs found in lapse dataset"
)

assert lapse_data["lapsed"].isin([0, 1]).all(), (
    "Invalid lapse target values"
)

assert not lapse_data.isnull().any().any(), (
    "Missing values found in lapse dataset"
)

print(f"\nLapse dataset records: {len(lapse_data)}")
print(f"Lapsed customers: {(lapse_data['lapsed'] == 1).sum()}")
print(f"Not lapsed customers: {(lapse_data['lapsed'] == 0).sum()}")
print("PASS: Lapse dataset validated")


# --------------------------------------------------
# 4. Validate saved model
# --------------------------------------------------

model = joblib.load(OUTPUTS / "lapse_model.joblib")

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
    "tenure_days",
]

assert all(
    column in lapse_data.columns
    for column in feature_columns
), "Required model features are missing"

predictions = model.predict_proba(
    lapse_data[feature_columns]
)

assert predictions.shape == (len(lapse_data), 2), (
    "Unexpected model probability output shape"
)

assert ((predictions >= 0) & (predictions <= 1)).all(), (
    "Invalid probability values"
)

assert abs(predictions.sum(axis=1) - 1).max() < 1e-6, (
    "Predicted class probabilities do not sum to 1"
)

print("\nPASS: Saved model loaded successfully")
print("PASS: Model probability predictions validated")


# --------------------------------------------------
# 5. Validate retention list
# --------------------------------------------------

retention = pd.read_csv(OUTPUTS / "retention_list.csv")

required_retention_columns = {
    "customer_id",
    "lapse_probability",
    "actually_lapsed",
}

assert required_retention_columns.issubset(
    retention.columns
), "Required retention list columns are missing"

assert len(retention) <= 10, (
    "Retention list contains more than 10 customers"
)

assert retention["customer_id"].is_unique, (
    "Duplicate customers found in retention list"
)

assert retention["lapse_probability"].between(0, 1).all(), (
    "Invalid lapse probabilities"
)

assert retention["actually_lapsed"].isin([0, 1]).all(), (
    "Invalid actual lapse labels"
)

assert retention["lapse_probability"].is_monotonic_decreasing, (
    "Retention list is not sorted by descending lapse probability"
)

# Every retention customer must belong to the Premium segment
premium_customer_ids = set(
    segments.loc[
        segments["is_premium"],
        "customer_id"
    ]
)

assert retention["customer_id"].isin(
    premium_customer_ids
).all(), (
    "Non-Premium customer found in retention list"
)

# Every retention customer must belong to the lapse cohort
assert retention["customer_id"].isin(
    lapse_data["customer_id"]
).all(), (
    "Retention customer not found in lapse dataset"
)

# Verify actual lapse labels against the lapse dataset
expected_labels = lapse_data.set_index(
    "customer_id"
)["lapsed"]

for _, row in retention.iterrows():
    expected_label = expected_labels.loc[row["customer_id"]]

    assert row["actually_lapsed"] == expected_label, (
        f"Incorrect actual lapse label for {row['customer_id']}"
    )

actual_lapsed_count = (
    retention["actually_lapsed"] == 1
).sum()

print(f"\nRetention list records: {len(retention)}")
print(f"Actually lapsed customers in list: {actual_lapsed_count}")
print("PASS: Retention list validated")


# --------------------------------------------------
# 6. Final result
# --------------------------------------------------

print("\n" + "=" * 60)
print("ALL PART B CHECKPOINTS PASSED")
print("=" * 60)
