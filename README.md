# Customer Intelligence & Support Copilot

## 1. Overview

This project develops a Customer Intelligence and Support Copilot for Swiggy Instamart using synthetic customer, product, order and support-ticket data.

The project is organized into four connected parts:

- **Part A - Data Foundation:** Audit, clean and standardize raw data, store trusted data in SQLite, and perform SQL and Pandas analysis.
- **Part B - Customer Segments and Lapse Prediction:** Apply RFM analysis, customer segmentation and machine-learning-based lapse prediction.
- **Part C - Support Ticket Triage with Guardrails:** Process support tickets, protect personal information, classify issues and route tickets.
- **Part D - Policy RAG Assistant and Refund Agent:** Retrieve company policy information and implement a tool-using refund agent with safety checks.

All monetary values in this project are represented in Indian Rupees (INR). The data is synthetic and is intended for academic demonstration.

## 2. Reproduce

### Prerequisites

- Python 3.12.3 (the version used to test this project).
- Git.
- Windows PowerShell or a compatible terminal.
 
### Clone the repository

```bash
git clone https://github.com/HARI-16-10-07/Instamart-Customer-Intelligence-Copilot.git
cd Instamart-Customer-Intelligence-Copilot
```

### Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Generate the synthetic data

```bash
python generate_data.py
```

This generates the raw CSV files and policy documents used by the project.

### Part A - Current reproduction commands

Run the following commands in order:

```bash
python src/audit_raw_data.py
python src/clean_data.py
python src/create_database.py
python src/validate_part_a.py
python src/run_sql_analysis.py
```

The validation script checks the cleaned data and database against the expected Part A results. Successful validation prints:

```text
ALL CHECKPOINTS PASSED
```

Reproduction instructions for Parts B, C and D will be added when those implementations are completed.

## 3. Part A

### Data Foundation

Part A converts the generated raw data into a trusted analytical dataset.

#### Raw data audit

Six raw CSV files are generated:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `tickets.csv`
- `agent_scenarios.csv`
- `policy_eval.csv`

The audit script examines the shape, data types, missing-value counts and missing-value percentages of the raw tables. The ticket data is read with `keep_default_na=False` to preserve empty ticket text for later processing.

#### Customer data cleaning

The customer dataset retains 1,200 rows.

| Cleaning operation | Result |
|---|---:|
| City values standardized | 476 |
| Gender values standardized | 950 |
| Blank ages identified | 61 |
| Invalid ages identified | 6 |
| Missing ages filled | 67 |
| Blank genders mapped to unknown | 30 |

City names are stripped of surrounding whitespace and standardized using title case. Gender spellings are mapped to `male`, `female` or `unknown`. Blank gender values become `unknown`.

Ages outside the valid range of 10-100 are treated as missing. Missing ages are filled using the median age of the corresponding city, calculated using `groupby` and `transform`. Signup dates are converted to datetime values.

Final city counts:

| City | Customers |
|---|---:|
| Pune | 227 |
| Delhi | 210 |
| Bengaluru | 197 |
| Chennai | 191 |
| Hyderabad | 191 |
| Mumbai | 184 |

Final gender counts are 610 female, 560 male and 30 unknown. No missing ages remain, and the cleaned age range is 18-60.

#### Product data cleaning

The product dataset retains all 40 rows. No product cleaning changes were required.

#### Order data cleaning

The order-cleaning process applies the following operations:

1. Convert `order_ts` into datetime values.
2. Remove 119 exact duplicate rows.
3. Resolve 656 duplicate order IDs by retaining the latest order record.
4. Standardize order statuses by removing surrounding whitespace and converting values to lowercase. No status values required standardization.
5. Remove pending orders remaining after duplicate-ID resolution. No additional pending rows remained to be removed.
6. Convert order amounts to numeric values and fill 112 missing or invalid amounts using product price, quantity and discount.
7. Treat 105 negative delivery-time values as missing after duplicate resolution.
8. Fill 774 missing delivery times for completed orders using the median delivery time of the corresponding product category.
9. Keep cancelled-order delivery times missing.

The cleaned orders dataset contains 12,309 unique order IDs.

| Final order status | Rows |
|---|---:|
| Completed | 11,110 |
| Cancelled | 1,199 |
| **Total** | **12,309** |

Final checks confirm zero missing order amounts, zero missing delivery times among completed orders and 1,199 missing delivery times among cancelled orders.

Completed order revenue is **INR 2,998,668.80**.

#### SQLite database

The cleaned datasets are stored in `data/instamart.db`, an SQLite database containing three tables:

- `customers`
- `products`
- `orders`

The database creation script defines primary keys, foreign keys and applicable constraints, loads the cleaned CSV data and checks foreign-key integrity.

#### SQL analysis

Seven SQL queries are stored in `sql/queries.sql` and executed through Pandas using `pd.read_sql_query`.

| Query | Analysis | Expected result |
|---|---|---:|
| Q1 | High-spending customers with qualifying completed orders | 30 customers |
| Q2 | Revenue by city and product category | 30 groups |
| Q3 | Products priced above average catalogue price | 11 products |
| Q4 | Customers without completed orders | 25 customers |
| Q5 | Customers spending above average | 550 customers |
| Q6 | Customer spending rankings within each city | 1,175 customers |
| Q7 | Daily revenue and cumulative running total | 183 days |

Q2 produces total completed revenue of INR 2,998,668.80. The highest city-category revenue is Bengaluru Electronics at INR 2,33,909.45.

Q5 calculates average completed customer spend of approximately INR 2,552.06.

Q6 demonstrates `RANK()`, `DENSE_RANK()` and `ROW_NUMBER()` window functions. There are eight rows where `RANK()` differs from `ROW_NUMBER()` because of tied spending values.

Q7 produces a final cumulative revenue of INR 2,998,668.80.

#### Pandas analysis

The analysis also uses `pivot_table` with margins, named aggregation, descriptive statistics, outlier detection and correlation analysis.

- The Q2 pivot-table grand total matches INR 2,998,668.80.
- Bengaluru completed revenue is INR 5,23,643.40 across 1,894 orders.
- Mumbai completed revenue is INR 4,79,058.50 across 1,613 orders.
- Completed order amount mean: INR 269.91.
- Median: INR 135.00.
- Skewness: approximately 4.61.
- First quartile: INR 64.80.
- Third quartile: INR 297.00.
- Upper IQR fence: INR 645.30.
- Upper outliers: 897; lower outliers: 0.

The largest absolute correlation is between order amount and discount percentage (approximately -0.095). The correlation between order amount and quantity is approximately +0.087. Both relationships are weak, and correlation does not establish causation.

#### Exploratory Data Analysis questions

1. **What is this data about?**  
   The dataset contains synthetic Swiggy Instamart customer, product and order information across six Indian cities. The analysis focuses on completed orders, amounts, quantities, discounts and delivery times.

2. **What do its distributions and statistics look like?**  
   Completed order amounts have a mean of INR 269.91 and median of INR 135.00, with positive skewness of approximately 4.61. Q1 is INR 64.80 and Q3 is INR 297.00, indicating that most orders have relatively low values.

3. **Are there outliers or anomalies?**  
   The 1.5 x IQR lower fence is INR -283.50 and the upper fence is INR 645.30. There are no lower outliers and 897 upper outliers. These high-value orders may represent unusually large purchases.

4. **What relationships exist between variables?**  
   The largest absolute correlation is between order amount and discount percentage (approximately -0.095). Order amount and quantity have a correlation of approximately +0.087. Both relationships are weak; correlation of this size does not establish causation.

### Part A validation

The script `src/validate_part_a.py` checks the cleaned datasets, database tables, row counts, data integrity and expected analytical results.

Successful execution prints:

```text
ALL CHECKPOINTS PASSED
```


## 4. Part B — Customer Segments and Lapse Prediction

### 4.1 Objective

Part B uses the cleaned customer and order data produced in Part A to identify meaningful customer segments and predict customers who may stop ordering.

The implementation has two main components:

1. RFM-based customer segmentation using K-Means clustering.
2. Customer lapse prediction using Logistic Regression and Random Forest.

The generated customer segments are also used to create a Premium customer retention shortlist.

### 4.2 RFM Analysis

RFM analysis uses three customer behaviour measurements:

- **Recency:** Number of days since the customer's most recent completed order.
- **Frequency:** Number of distinct completed orders placed by the customer.
- **Monetary:** Total amount spent on completed orders.

The snapshot date is fixed at `2025-10-01 00:00:00`.

Only completed orders are included in the RFM calculations.

**RFM dataset summary**

| Measurement | Result |
|---|---:|
| Customers with completed orders | 1,175 |
| Median recency | 19 days |
| Minimum recency | 0 days |
| Maximum recency | 180 days |
| Average frequency | 9.46 orders |
| Maximum frequency | 33 orders |
| Average monetary value | INR 2,552.06 |
| Maximum monetary value | INR 14,766.55 |

### 4.3 Customer Segmentation Using K-Means

The three RFM features are standardized using `StandardScaler` before clustering.

K-Means clustering is evaluated for K values from 2 to 8. Each model uses `n_init=10` and `random_state=42`.

Both inertia and silhouette score are used to evaluate the clustering results.

**K-Means comparison**

| K | Inertia | Silhouette Score |
|---:|---:|---:|
| 2 | 1,820.8 | 0.465 |
| 3 | 1,268.2 | 0.445 |
| 4 | 743.1 | 0.526 |
| 5 | 617.4 | 0.480 |
| 6 | 503.2 | 0.482 |
| 7 | 408.5 | 0.416 |
| 8 | 366.5 | 0.412 |

**Selected cluster count: K = 4**

K=4 is selected because it provides the highest silhouette score among the evaluated values and produces four useful customer groups for business interpretation.

Although K=8 has lower inertia, inertia generally decreases as the number of clusters increases. Therefore, the lowest inertia alone is not sufficient justification for selecting a model.

### 4.4 Customer Segment Profiles

The four clusters are assigned descriptive business names based on their RFM characteristics.

| Segment | Customers | Average Recency (days) | Average Frequency | Average Monetary (INR) |
|---|---:|---:|---:|---:|
| Regular | 436 | 28.86 | 3.77 | 1,057.62 |
| Premium | 138 | 24.12 | 6.77 | 7,129.70 |
| Loyal | 419 | 8.77 | 19.40 | 3,410.02 |
| At Risk | 182 | 109.04 | 2.20 | 685.99 |

**Business interpretation and actions**

- **Premium:** Highest average monetary value. Provide personalized offers, priority support and loyalty rewards.
- **Loyal:** High ordering frequency and recent activity. Encourage repeat purchases through loyalty benefits and relevant product recommendations.
- **Regular:** Moderate purchasing behaviour. Encourage more frequent purchases through targeted promotions and product recommendations.
- **At Risk:** Long time since the last completed order and low purchasing frequency. Use reactivation campaigns and targeted discounts to encourage customers to return.

Cluster numbers are algorithm-generated identifiers and do not represent an inherent ranking.

### 4.5 PCA Analysis

Principal Component Analysis (PCA) is applied to the standardized RFM features to examine how much variance can be represented in two dimensions.

| Component | Explained Variance Ratio |
|---|---:|
| Principal Component 1 | 0.634 |
| Principal Component 2 | 0.218 |
| **Total** | **0.852** |

The first two principal components explain approximately 85.2% of the variance in the standardized RFM data.

### 4.6 Lapse Prediction Dataset Preparation

The lapse prediction dataset is constructed using a cutoff date of `2025-09-01`.

Customers who placed at least one completed order before the cutoff are included in the eligible cohort.

A customer is labelled as lapsed (`1`) if they do not place a completed order during September 2025. Otherwise, the customer is labelled as not lapsed (`0`).

**Dataset summary**

| Measurement | Result |
|---|---:|
| Eligible customers | 1,156 |
| Not lapsed | 713 |
| Lapsed | 443 |
| Lapsed percentage | 38.32% |
| Not-lapsed percentage | 61.68% |

The dataset contains 1,156 customers and 13 columns, including the customer identifier, 11 input features and the target label.

**Features used**

| Feature | Description |
|---|---|
| recency | Days since the last completed order before the cutoff |
| frequency | Number of completed orders before the cutoff |
| monetary | Total completed-order spending before the cutoff |
| avg_discount | Average discount percentage on completed orders |
| cancellation_rate | Cancelled orders divided by all final-status orders |
| avg_delivery | Average delivery time of completed orders |
| favorite_category | Most frequently ordered product category |
| city | Customer city |
| age | Customer age |
| gender | Customer gender |
| tenure_days | Days since signup at the cutoff date |

All input features are constructed using information available before `2025-09-01`. September activity is used only to generate the target label. Customer segment labels are not included as model features.

Missing values in the model features are checked before training.

### 4.7 Training and Testing

The dataset is divided using a stratified 80:20 train/test split with `random_state=42`.

| Dataset | Records |
|---|---:|
| Training | 924 |
| Testing | 232 |
| Total | 1,156 |

**Training class distribution**

| Class | Records |
|---|---:|
| Not lapsed | 570 |
| Lapsed | 354 |

**Testing class distribution**

| Class | Records |
|---|---:|
| Not lapsed | 143 |
| Lapsed | 89 |

A baseline model that predicts every customer as not lapsed achieves 61.64% accuracy but has an F1-score of 0 for the lapsed class. This demonstrates why accuracy alone is insufficient for evaluating the lapse prediction task.

### 4.8 Preprocessing and Model Training

A `ColumnTransformer` and scikit-learn `Pipeline` are used for preprocessing and model training.

- Numerical features are standardized using `StandardScaler`.
- Categorical features are encoded using `OneHotEncoder(drop="first", handle_unknown="ignore")`.
- Preprocessing is fitted only on training data through the model pipelines.
- Grid search and cross-validation use the training data only.

**Logistic Regression**

GridSearchCV evaluates the following C values:

`[0.01, 0.1, 1, 10, 100]`

The maximum iteration count is 1,000, and five-fold cross-validation uses the F1-score.

Best parameter:

`C = 100`

Best cross-validation F1-score: **0.6506**

**Random Forest**

GridSearchCV evaluates:

- `n_estimators = 100`
- `random_state = 42`
- `max_depth = [3, 5, 8]`
- `min_samples_leaf = [5, 10, 20]`

Five-fold cross-validation uses the F1-score, resulting in 45 parameter/fold fits.

Best parameters:

- `max_depth = 8`
- `min_samples_leaf = 10`
- `n_estimators = 100`

Best cross-validation F1-score: **0.6811**

### 4.9 Test-Set Model Evaluation

Both trained models are evaluated on the same untouched test set.

| Metric | Logistic Regression | Random Forest |
|---|---:|---:|
| Accuracy | 0.7284 | 0.7371 |
| Lapsed-class Precision | 0.6444 | 0.6591 |
| Lapsed-class Recall | 0.6517 | 0.6517 |
| Lapsed-class F1-score | 0.6480 | 0.6554 |

**Confusion matrices**

Logistic Regression:

```text
[[111  32]
 [ 31  58]]
```

Random Forest:

```text
[[113  30]
 [ 31  58]]
```

Random Forest is selected as the final model because it achieves a slightly higher test accuracy, precision and F1-score than Logistic Regression, while maintaining the same recall. Its test F1-score is approximately 0.6554, exceeding the required 0.55 threshold.

From a business perspective, false negatives represent customers who are likely to lapse but are not identified for retention activity. False positives represent customers incorrectly identified as likely to lapse, potentially resulting in unnecessary promotional spending. Both types of errors matter, so precision and recall are considered alongside F1-score.

### 4.10 Oversampling Experiment

The original training dataset contains 570 non-lapsed customers and 354 lapsed customers.

To address class imbalance, the minority class is oversampled using replacement with `random_state=42`.

All 354 original minority-class records are retained, and 216 additional samples are drawn with replacement. The resulting training distribution is:

| Class | Before | After |
|---|---:|---:|
| Not lapsed | 570 | 570 |
| Lapsed | 354 | 570 |
| Total | 924 | 1,140 |

Oversampling is performed only on the training data. The test set remains unchanged.

**Before and after oversampling**

| Metric | Original Logistic Regression | Oversampled Logistic Regression |
|---|---:|---:|
| Precision | 0.6444 | 0.5891 |
| Recall | 0.6517 | 0.8539 |
| F1-score | 0.6480 | 0.6972 |
| Accuracy | 0.7284 | 0.7155 |

Oversampled confusion matrix:

```text
[[90 53]
 [13 76]]
```

Recall increases from 0.6517 to 0.8539, an improvement of approximately 20.22 percentage points. F1-score also increases, while precision and accuracy decrease.

This demonstrates that oversampling improves the identification of lapsed customers but also increases false-positive predictions. The original Random Forest remains the selected final model based on the comparison of the two original models.

### 4.11 Feature Importance and Model Interpretation

Random Forest feature importance is used to identify the five most influential features.

| Feature | Importance |
|---|---:|
| Frequency | 0.279589 |
| Monetary | 0.271176 |
| Recency | 0.115149 |
| Average delivery | 0.061286 |
| Cancellation rate | 0.052325 |

Frequency and monetary value have the highest feature importance among the evaluated features.

Logistic Regression coefficients provide additional information about the direction of the learned associations.

| Feature | Coefficient |
|---|---:|
| Frequency | -1.698239 |
| Favorite category: Electronics | -1.136713 |
| Favorite category: Grocery | -0.448673 |

These negative coefficients indicate lower predicted lapse log-odds relative to the relevant reference categories, holding other features constant. They describe model associations and should not be interpreted as proof of causation.

### 4.12 Model Saving and Reload Verification

The selected Random Forest model is saved using `joblib` at:

`outputs/lapse_model.joblib`

The saved model is loaded again, and its predictions are compared with the predictions from the original in-memory model.

The verification result is:

`Original and reloaded predictions match: True`

This confirms that the saved model can be loaded and used to reproduce the same predictions.

### 4.13 Premium Customer Retention List

The retention list is generated by combining the lapse prediction results with the Premium segment.

The script:

1. Recreates the same stratified train/test split.
2. Identifies Premium customers.
3. Selects Premium customers from the test set.
4. Predicts lapse probabilities using the selected Random Forest model.
5. Sorts customers by predicted lapse probability in descending order.
6. Saves up to the top 10 customers.

The generated file is:

`outputs/retention_list.csv`

It contains the required columns:

- `customer_id`
- `lapse_probability`
- `actually_lapsed`

**Retention list summary**

| Measurement | Result |
|---|---:|
| Customers in retention list | 10 |
| Actually lapsed customers | 1 |

The list provides an illustrative shortlist for retention teams. The `actually_lapsed` column is included for evaluation against the September target.

**Important evaluation limitation:** The Premium flag is determined using whole-window RFM data, including September 2025, which overlaps with the lapse-label period. Therefore, the generated Premium retention list is illustrative and is not a leakage-free historical evaluation. The lapse prediction model itself uses only pre-cutoff features.

### 4.14 Part B Output Files

| File | Purpose |
|---|---|
| `outputs/customer_segments.csv` | Customer RFM values, segment assignments and Premium flag |
| `outputs/kmeans_comparison.csv` | K-Means inertia and silhouette comparison |
| `outputs/lapse_dataset.csv` | Prepared customer lapse dataset |
| `outputs/lapse_model.joblib` | Saved selected Random Forest model |
| `outputs/lapse_model_comparison.csv` | Model evaluation comparison |
| `outputs/lapse_feature_importance.csv` | Random Forest feature importance |
| `outputs/retention_list.csv` | Premium customer retention shortlist |

### 4.15 Validation

Run the following command to validate Part B:

```powershell
python src/validate_part_b.py
```

The validation script checks:

- Required Part B output files exist.
- Customer segment records and Premium segment identification are valid.
- Premium is the segment with the highest average monetary value.
- Lapse dataset identifiers and target labels are valid.
- The saved model loads successfully.
- Model probability predictions are valid.
- The retention list contains valid Premium customers from the lapse cohort.
- Retention probabilities and actual lapse labels are valid.

The completed validation run prints:

```text
ALL PART B CHECKPOINTS PASSED
```

Part B is implemented and validated.

## 5. Part C

**Status: Pending implementation.**

This section will document support-ticket preprocessing, privacy redaction, zero-shot and few-shot classification, retry handling, token-budget controls and ticket routing after Part C is implemented and verified.

## 6. Part D

**Status: Pending implementation.**

This section will document policy-document chunking, TF-IDF retrieval, RAG evaluation, refund-agent tools, safety limits, execution checkpoints and resumable agent runs after Part D is implemented and verified.

## 7. Limitations and Next Steps

- The datasets are synthetic and do not represent actual Swiggy customer or transaction records.
- Part A establishes the cleaned data foundation and analytical database for the later project components.
- Correlation analysis identifies statistical relationships but does not establish causal effects.
- Parts B, C and D will be documented after their implementations and evaluation results have been verified.

