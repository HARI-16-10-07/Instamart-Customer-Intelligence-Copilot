
from pathlib import Path

import pandas as pd
import numpy as np
import joblib
from sklearn.base import clone
from sklearn.utils import resample
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)


# --------------------------------------------------
# 1. PATHS AND SETTINGS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = PROJECT_ROOT / "outputs" / "lapse_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

RANDOM_STATE = 42


# --------------------------------------------------
# 2. LOAD LAPSE DATASET
# --------------------------------------------------

dataset = pd.read_csv(DATA_PATH)

print("Dataset shape:", dataset.shape)

X = dataset.drop(columns=["customer_id", "lapsed"])
y = dataset["lapsed"]

numeric_features = [
    "recency",
    "frequency",
    "monetary",
    "avg_discount",
    "cancellation_rate",
    "avg_delivery",
    "age",
    "tenure_days"
]

categorical_features = [
    "city",
    "gender",
    "favorite_category"
]


# --------------------------------------------------
# 3. TRAIN-TEST SPLIT
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=y
)

print("\nTRAINING ROWS:", len(X_train))
print("TEST ROWS:", len(X_test))

print("\nTRAINING CLASS DISTRIBUTION:")
print(y_train.value_counts().sort_index())

print("\nTEST CLASS DISTRIBUTION:")
print(y_test.value_counts().sort_index())


# --------------------------------------------------
# 4. PREPROCESSING PIPELINE
# --------------------------------------------------

numeric_transformer = StandardScaler()

categorical_transformer = OneHotEncoder(
    drop="first",
    handle_unknown="ignore"
)

preprocessor = ColumnTransformer(
    transformers=[
        ("numeric", numeric_transformer, numeric_features),
        ("categorical", categorical_transformer, categorical_features)
    ]
)


# --------------------------------------------------
# 5. BASELINE MODEL
# --------------------------------------------------

# Baseline predicts that every customer will not lapse.

baseline_predictions = [0] * len(y_test)

baseline_accuracy = accuracy_score(
    y_test,
    baseline_predictions
)

baseline_f1 = f1_score(
    y_test,
    baseline_predictions,
    zero_division=0
)

print("\nBASELINE MODEL")
print("Accuracy:", round(baseline_accuracy, 4))
print("Lapsed-class F1:", round(baseline_f1, 4))


# --------------------------------------------------
# 6. LOGISTIC REGRESSION GRID SEARCH
# --------------------------------------------------

logistic_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000))
    ]
)

logistic_parameters = {
    "classifier__C": [0.01, 0.1, 1, 10, 100]
}

logistic_search = GridSearchCV(
    estimator=logistic_pipeline,
    param_grid=logistic_parameters,
    scoring="f1",
    cv=5,
    n_jobs=-1,
    refit=True
)

print("\nTRAINING LOGISTIC REGRESSION...")
logistic_search.fit(X_train, y_train)

print("Best Logistic Regression parameters:")
print(logistic_search.best_params_)

print(
    "Best Logistic Regression CV F1:",
    round(logistic_search.best_score_, 4)
)


# --------------------------------------------------
# 7. RANDOM FOREST GRID SEARCH
# --------------------------------------------------

random_forest_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(random_state=RANDOM_STATE)
        )
    ]
)

random_forest_parameters = {
    "classifier__n_estimators": [100],
    "classifier__max_depth": [3, 5, 8],
    "classifier__min_samples_leaf": [5, 10, 20]
}

random_forest_search = GridSearchCV(
    estimator=random_forest_pipeline,
    param_grid=random_forest_parameters,
    scoring="f1",
    cv=5,
    n_jobs=-1,
    refit=True
)

print("\nTRAINING RANDOM FOREST...")
random_forest_search.fit(X_train, y_train)

print("Best Random Forest parameters:")
print(random_forest_search.best_params_)

print(
    "Best Random Forest CV F1:",
    round(random_forest_search.best_score_, 4)
)


# --------------------------------------------------
# 8. EVALUATE BOTH MODELS ON UNTOUCHED TEST DATA
# --------------------------------------------------

models = {
    "Logistic Regression": logistic_search.best_estimator_,
    "Random Forest": random_forest_search.best_estimator_
}

evaluation_results = []

print("\nTEST SET EVALUATION")
print("=" * 60)

for model_name, model in models.items():

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    )

    evaluation_results.append({
        "model": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    })

    print(f"\n{model_name}")
    print("Accuracy:", round(accuracy, 4))
    print("Lapsed-class precision:", round(precision, 4))
    print("Lapsed-class recall:", round(recall, 4))
    print("Lapsed-class F1:", round(f1, 4))
    print("Confusion matrix:")
    print(matrix)


# --------------------------------------------------
# 9. COMPARE MODEL RESULTS
# --------------------------------------------------

evaluation_df = pd.DataFrame(evaluation_results)

evaluation_df.to_csv(
    OUTPUT_DIR / "lapse_model_comparison.csv",
    index=False
)

print("\nMODEL COMPARISON")
print(evaluation_df.to_string(index=False))


# --------------------------------------------------
# 10. CHECK TRAIN-ONLY SCALING
# --------------------------------------------------

best_logistic = logistic_search.best_estimator_

fitted_scaler = (
    best_logistic
    .named_steps["preprocessor"]
    .named_transformers_["numeric"]
)

frequency_index = numeric_features.index("frequency")

training_frequency_mean = fitted_scaler.mean_[frequency_index]
full_cohort_frequency_mean = dataset["frequency"].mean()

print("\nSCALING LEAKAGE CHECK")
print(
    "Training-only frequency mean:",
    round(training_frequency_mean, 4)
)
print(
    "Full-cohort frequency mean:",
    round(full_cohort_frequency_mean, 4)
)

# --------------------------------------------------
# 11. OVERSAMPLING EXPERIMENT
# --------------------------------------------------

print("\nOVERSAMPLING EXPERIMENT")
print("=" * 60)

# Combine training features and labels temporarily.
training_data = X_train.copy()
training_data["lapsed"] = y_train.values

# Separate majority and minority classes.
majority_class = training_data[
    training_data["lapsed"] == 0
]

minority_class = training_data[
    training_data["lapsed"] == 1
]

# Duplicate minority-class rows with replacement.
minority_oversampled = resample(
    minority_class,
    replace=True,
    n_samples=len(majority_class),
    random_state=42
)

# Combine original majority and oversampled minority rows.
balanced_training_data = pd.concat(
    [majority_class, minority_oversampled],
    ignore_index=True
)

X_train_balanced = balanced_training_data.drop(
    columns=["lapsed"]
)

y_train_balanced = balanced_training_data["lapsed"]

print("Original training distribution:")
print(y_train.value_counts().sort_index())

print("\nBalanced training distribution:")
print(y_train_balanced.value_counts().sort_index())


# Refit the best Logistic Regression configuration.
oversampled_logistic = clone(logistic_search.best_estimator_)

oversampled_logistic.fit(
    X_train_balanced,
    y_train_balanced
)

# Evaluate on the original, untouched test data.
oversampled_predictions = oversampled_logistic.predict(X_test)

oversampled_precision = precision_score(
    y_test,
    oversampled_predictions,
    zero_division=0
)

oversampled_recall = recall_score(
    y_test,
    oversampled_predictions,
    zero_division=0
)

oversampled_f1 = f1_score(
    y_test,
    oversampled_predictions,
    zero_division=0
)

print("\nOVERSAMPLED LOGISTIC REGRESSION")
print("Precision:", round(oversampled_precision, 4))
print("Recall:", round(oversampled_recall, 4))
print("F1:", round(oversampled_f1, 4))

print("\nBEFORE VS AFTER OVERSAMPLING")
print(
    "Original Logistic Regression recall:",
    round(
        evaluation_df.loc[
            evaluation_df["model"] == "Logistic Regression",
            "recall"
        ].iloc[0],
        4
    )
)
print("Oversampled recall:", round(oversampled_recall, 4))
oversampled_accuracy = accuracy_score(
    y_test,
    oversampled_predictions
)

oversampled_matrix = confusion_matrix(
    y_test,
    oversampled_predictions,
    labels=[0, 1]
)
print("Accuracy:", round(oversampled_accuracy, 4))
print("Confusion matrix:")
print(oversampled_matrix)

# --------------------------------------------------
# 12. RANDOM FOREST FEATURE IMPORTANCE
# --------------------------------------------------

print("\nTOP 5 RANDOM FOREST FEATURES")
print("=" * 60)

best_random_forest = random_forest_search.best_estimator_

rf_preprocessor = best_random_forest.named_steps["preprocessor"]
rf_classifier = best_random_forest.named_steps["classifier"]

rf_feature_names = rf_preprocessor.get_feature_names_out()

feature_importance = pd.DataFrame({
    "feature": rf_feature_names,
    "importance": rf_classifier.feature_importances_
})

feature_importance = feature_importance.sort_values(
    "importance",
    ascending=False
)

print(feature_importance.head(5).to_string(index=False))

feature_importance.to_csv(
    OUTPUT_DIR / "lapse_feature_importance.csv",
    index=False
)


# --------------------------------------------------
# 13. LOGISTIC REGRESSION COEFFICIENT INTERPRETATION
# --------------------------------------------------

print("\nTOP 3 LOGISTIC REGRESSION COEFFICIENTS")
print("=" * 60)

logistic_preprocessor = (
    best_logistic.named_steps["preprocessor"]
)

logistic_classifier = best_logistic.named_steps["classifier"]

logistic_feature_names = (
    logistic_preprocessor.get_feature_names_out()
)

coefficients = pd.DataFrame({
    "feature": logistic_feature_names,
    "coefficient": logistic_classifier.coef_[0]
})

coefficients["absolute_coefficient"] = (
    coefficients["coefficient"].abs()
)

top_coefficients = coefficients.sort_values(
    "absolute_coefficient",
    ascending=False
).head(3)

print(
    top_coefficients[
        ["feature", "coefficient"]
    ].to_string(index=False)
)


# --------------------------------------------------
# 14. SAVE SELECTED MODEL
# --------------------------------------------------

# Select the model with the higher test-set F1 score.

best_model_name = evaluation_df.loc[
    evaluation_df["f1"].idxmax(),
    "model"
]

if best_model_name == "Random Forest":
    selected_model = best_random_forest
else:
    selected_model = best_logistic

model_path = OUTPUT_DIR / "lapse_model.joblib"

joblib.dump(selected_model, model_path)

print("\nSelected model:", best_model_name)
print("Selected model test F1:",
      round(evaluation_df["f1"].max(), 4))
print("Saved:", model_path)

# --------------------------------------------------
# 15. RELOAD AND VERIFY MODEL
# --------------------------------------------------

reloaded_model = joblib.load(model_path)

original_predictions = selected_model.predict(X_test)

reloaded_predictions = reloaded_model.predict(X_test)

predictions_match = np.array_equal(
    original_predictions,
    reloaded_predictions
)

print("\nMODEL RELOAD VERIFICATION")
print("Original and reloaded predictions match:", predictions_match)

assert predictions_match, "Model reload verification failed!"

print("MODEL RELOAD CHECK PASSED")

print("\nMODEL TRAINING AND EVALUATION COMPLETED")
