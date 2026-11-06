
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA


# --------------------------------------------------
# 1. PROJECT PATHS AND SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "instamart.db"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOT_DATE = pd.Timestamp("2025-10-01")
SELECTED_K = 4


# --------------------------------------------------
# 2. READ COMPLETED ORDERS FROM SQLITE
# --------------------------------------------------

connection = sqlite3.connect(DATABASE_PATH)

orders = pd.read_sql_query(
    """
    SELECT customer_id, order_id, order_ts, order_amount
    FROM orders
    WHERE status = 'completed'
    """,
    connection
)

connection.close()

orders["order_ts"] = pd.to_datetime(orders["order_ts"])

print("Completed orders loaded:", len(orders))


# --------------------------------------------------
# 3. CALCULATE RFM FEATURES
# --------------------------------------------------

rfm = orders.groupby("customer_id").agg(
    last_order_date=("order_ts", "max"),
    frequency=("order_id", "nunique"),
    monetary=("order_amount", "sum")
).reset_index()

rfm["recency"] = (
    SNAPSHOT_DATE - rfm["last_order_date"].dt.normalize()
).dt.days

rfm = rfm[
    ["customer_id", "recency", "frequency", "monetary"]
].copy()

print("\nRFM CUSTOMER COUNT:", len(rfm))
print("\nRFM SUMMARY:")
print(rfm[["recency", "frequency", "monetary"]].describe())


# --------------------------------------------------
# 4. STANDARDIZE RFM FEATURES
# --------------------------------------------------

rfm_features = rfm[
    ["recency", "frequency", "monetary"]
]

scaler = StandardScaler()
scaled_features = scaler.fit_transform(rfm_features)


# --------------------------------------------------
# 5. COMPARE K-MEANS MODELS (K = 2 TO 8)
# --------------------------------------------------

comparison_results = []

print("\nK-MEANS MODEL COMPARISON")
print("-" * 60)

for k in range(2, 9):

    model = KMeans(
        n_clusters=k,
        n_init=10,
        random_state=42
    )

    cluster_labels = model.fit_predict(scaled_features)

    inertia = model.inertia_
    silhouette = silhouette_score(
        scaled_features,
        cluster_labels
    )

    comparison_results.append({
        "k": k,
        "inertia": inertia,
        "silhouette_score": silhouette
    })

    print(
        f"K={k} | "
        f"Inertia={inertia:.1f} | "
        f"Silhouette={silhouette:.3f}"
    )

comparison_df = pd.DataFrame(comparison_results)

comparison_df.to_csv(
    OUTPUT_DIR / "kmeans_comparison.csv",
    index=False
)


# --------------------------------------------------
# 6. TRAIN THE SELECTED K-MEANS MODEL
# --------------------------------------------------

final_model = KMeans(
    n_clusters=SELECTED_K,
    n_init=10,
    random_state=42
)

rfm["segment_id"] = final_model.fit_predict(scaled_features)


# --------------------------------------------------
# 7. INTERPRET THE FOUR SEGMENTS
# --------------------------------------------------

segment_profile = rfm.groupby("segment_id").agg(
    customer_count=("customer_id", "count"),
    avg_recency=("recency", "mean"),
    avg_frequency=("frequency", "mean"),
    avg_monetary=("monetary", "mean")
)

# Identify the clusters using their business characteristics.
remaining_segments = set(segment_profile.index)

premium_segment = segment_profile["avg_monetary"].idxmax()
remaining_segments.remove(premium_segment)

loyal_segment = max(
    remaining_segments,
    key=lambda segment: segment_profile.loc[
        segment, "avg_frequency"
    ]
)
remaining_segments.remove(loyal_segment)

at_risk_segment = max(
    remaining_segments,
    key=lambda segment: segment_profile.loc[
        segment, "avg_recency"
    ]
)
remaining_segments.remove(at_risk_segment)

regular_segment = remaining_segments.pop()

segment_names = {
    premium_segment: "Premium",
    loyal_segment: "Loyal",
    at_risk_segment: "At Risk",
    regular_segment: "Regular"
}

rfm["segment_name"] = rfm["segment_id"].map(segment_names)

rfm["is_premium"] = (
    rfm["segment_id"] == premium_segment
).astype(int)


# --------------------------------------------------
# 8. PCA EXPLAINED VARIANCE
# --------------------------------------------------

pca = PCA(n_components=3)
pca.fit(scaled_features)

print("\nPCA EXPLAINED VARIANCE:")
print(np.round(pca.explained_variance_ratio_, 3))

print(
    "First two components combined:",
    round(pca.explained_variance_ratio_[:2].sum(), 3)
)


# --------------------------------------------------
# 9. SAVE CUSTOMER SEGMENTS
# --------------------------------------------------

output_columns = [
    "customer_id",
    "recency",
    "frequency",
    "monetary",
    "segment_id",
    "segment_name",
    "is_premium"
]

rfm[output_columns].to_csv(
    OUTPUT_DIR / "customer_segments.csv",
    index=False
)


# --------------------------------------------------
# 10. DISPLAY SEGMENT RESULTS
# --------------------------------------------------

print("\nSEGMENT PROFILES")
print(segment_profile)

print("\nSEGMENT NAMES")
print(segment_names)

print("\nCUSTOMERS PER SEGMENT")
print(rfm["segment_name"].value_counts())

print("\nPREMIUM CUSTOMER COUNT:", rfm["is_premium"].sum())

print("\nSaved:")
print("outputs/customer_segments.csv")
print("outputs/kmeans_comparison.csv")

print("\nRFM SEGMENTATION COMPLETED")
