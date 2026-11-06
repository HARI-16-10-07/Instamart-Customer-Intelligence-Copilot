import pandas as pd
import joblib

from pathlib import Path
from sklearn.model_selection import train_test_split


# Project paths
ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = ROOT / "outputs" / "lapse_dataset.csv"
SEGMENTS_PATH = ROOT / "outputs" / "customer_segments.csv"
MODEL_PATH = ROOT / "outputs" / "lapse_model.joblib"
OUTPUT_PATH = ROOT / "outputs" / "retention_list.csv"


# Load the prepared dataset, customer segments, and trained model
df = pd.read_csv(DATASET_PATH)
segments = pd.read_csv(SEGMENTS_PATH)
model = joblib.load(MODEL_PATH)


# Separate features and target
X = df.drop(columns=["customer_id", "lapsed"])
y = df["lapsed"]


# Recreate the same test split used during model training
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# Identify Premium customers
premium_flag = (
    segments["is_premium"]
    .astype(str)
    .str.lower()
    .isin(["1", "true", "yes"])
)

premium_ids = segments.loc[premium_flag, ["customer_id"]]


# Get the actual test customers and their true labels
test_customers = df.loc[
    X_test.index,
    ["customer_id", "lapsed"]
].copy()


# Calculate predicted lapse probabilities
test_customers["lapse_probability"] = model.predict_proba(X_test)[:, 1]


# Keep only Premium customers who belong to the test set
retention_list = test_customers.merge(
    premium_ids,
    on="customer_id",
    how="inner"
)


# Rename the actual target column
retention_list = retention_list.rename(
    columns={"lapsed": "actually_lapsed"}
)


# Rank customers by predicted lapse probability
retention_list = retention_list.sort_values(
    by="lapse_probability",
    ascending=False
).head(10)


# Keep only the required columns
retention_list = retention_list[
    ["customer_id", "lapse_probability", "actually_lapsed"]
]


# Save the retention list
retention_list.to_csv(OUTPUT_PATH, index=False)


# Display results
print("\nPREMIUM CUSTOMER RETENTION LIST")
print("=" * 60)

print(retention_list.to_string(index=False))

print("\nCustomers in retention list:", len(retention_list))

print(
    "Actually lapsed customers in list:",
    int(retention_list["actually_lapsed"].sum())
)

print("\nSaved:", OUTPUT_PATH)
print("\nRETENTION LIST GENERATION COMPLETED")