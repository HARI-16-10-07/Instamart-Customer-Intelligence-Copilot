# Customer Intelligence & Support Copilot

## 1. Project Overview

This project develops a **Customer Intelligence & Support Copilot** for Swiggy Instamart using synthetic customer, product, order and support-ticket data.

The project is organized into four connected parts:

- **Part A – Data Foundation:** Audit and clean raw datasets, standardize inconsistent values, create a trusted SQLite database, and perform SQL and Pandas analysis.
- **Part B – Customer Segments and Lapse Prediction:** Apply RFM analysis, K-Means customer segmentation, and machine-learning models to predict customer lapse.
- **Part C – Support Ticket Triage with Guardrails:** Protect personal information, classify support tickets, handle invalid outputs and token limits, and route tickets using customer information from Part B.
- **Part D – Policy RAG Assistant and Refund Agent:** Retrieve information from policy documents and implement an offline tool-using refund agent with validation, safety limits and resumable execution.

All monetary values are represented in Indian Rupees (INR). All datasets are synthetic and fictional and are intended for academic demonstration.

### Important implementation note

The project uses the supplied `mock_llm.py` as a deterministic, offline stand-in for an LLM API. It does not connect to a live GPT service or require an API key. The project demonstrates classification, retrieval, tool execution, validation, token estimation and agent workflows using this offline implementation.

---

## 2. Reproducing the Project

### 2.1 Prerequisites

- Python 3.12.3 (the version used to test this project).
- Git.
- Windows PowerShell or a compatible terminal.

### 2.2 Clone the repository

```bash
git clone https://github.com/HARI-16-10-07/Instamart-Customer-Intelligence-Copilot.git

cd Instamart-Customer-Intelligence-Copilot
```

### 2.3 Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv

.\venv\Scripts\Activate.ps1
```

### 2.4 Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2.5 Generate synthetic data

For a fresh setup, generate the raw datasets and policy documents once:

```bash
python generate_data.py
```

This creates the synthetic raw CSV files and policy documents used by the project.

**Important:** `generate_data.py` regenerates the raw synthetic data. Do not run it unnecessarily when you want to preserve an existing dataset or reproduce results from the current raw files.

### 2.6 Run the complete project

The project includes a master execution script:

```bash
python run_project.py
```

The master runner coordinates the connected project components using the existing raw data. It runs the data foundation, customer segmentation and lapse prediction, ticket triage, policy retrieval and agent workflows in the required order.

The runner does not automatically regenerate the raw data using `generate_data.py`. This prevents an ordinary pipeline run from unexpectedly replacing the existing raw datasets.

### 2.7 Individual validation commands

The following validation scripts can also be run independently after their corresponding implementation steps:

**Part A**

```bash
python src/validate_part_a.py
```

**Part B**

```bash
python src/validate_part_b.py
```

Part C and Part D demonstrations are coordinated through the master runner. Avoid running every Python file indiscriminately: data generators, demonstrations and agent scripts may regenerate files or append execution records.

---

## 3. Part A – Data Foundation

### 3.1 Objective

Part A converts the generated raw data into a trusted analytical dataset.

The work includes:

- Auditing the raw datasets.
- Handling missing values and invalid records.
- Removing duplicate records.
- Standardizing customer and order information.
- Creating an SQLite analytical database.
- Executing SQL queries.
- Performing Pandas analysis and exploratory data analysis.

### 3.2 Raw Data Audit

Six raw CSV files are generated:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `tickets.csv`
- `agent_scenarios.csv`
- `policy_eval.csv`

The audit script examines dataset shapes, data types, missing-value counts and missing-value percentages.

The ticket data is read with `keep_default_na=False` to preserve empty ticket text for later processing.

**Important raw-data findings**

| Raw data finding | Result |
|---|---:|
| Raw order rows | 13,084 |
| Exact duplicate order rows | 119 |
| Pending order rows | 656 |
| Distinct order IDs | 12,309 |
| Nonnumeric or missing order amounts | 120 |
| Negative delivery times | 106 |
| Blank delivery times | 2,541 |
| Customers with blank ages | 61 |
| Customers with ages outside 10–100 | 6 |
| Distinct raw city spellings | 24 |
| Distinct nonblank raw gender spellings | 10 |
| Customers with blank gender | 30 |

### 3.3 Customer Data Cleaning

The customer dataset retains 1,200 rows.

| Cleaning operation | Result |
|---|---:|
| City values standardized | 476 |
| Gender values standardized | 950 |
| Blank ages identified | 61 |
| Invalid ages identified | 6 |
| Missing ages filled | 67 |
| Blank genders mapped to unknown | 30 |

City names are stripped of surrounding whitespace and standardized using title case.

Gender spellings are mapped to `male`, `female` or `unknown`. Blank gender values become `unknown`.

Ages outside the valid range of 10–100 are treated as missing. Missing ages are filled using the median age of the corresponding city, calculated using `groupby` and `transform`.

Signup dates are converted to datetime values.

**Final city counts**

| City | Customers |
|---|---:|
| Pune | 227 |
| Delhi | 210 |
| Bengaluru | 197 |
| Chennai | 191 |
| Hyderabad | 191 |
| Mumbai | 184 |

**Final gender counts**

- Female: 610
- Male: 560
- Unknown: 30

No missing ages remain after cleaning. The cleaned age range is 18–60.

### 3.4 Product Data Cleaning

The product dataset retains all 40 rows.

No product cleaning changes were required.

### 3.5 Order Data Cleaning

The order-cleaning process applies the following operations in sequence:

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

Final checks confirm:

- Zero missing order amounts.
- Zero missing delivery times among completed orders.
- 1,199 missing delivery times among cancelled orders.

Completed order revenue is **INR 2,998,668.80**.

### 3.6 SQLite Database

The cleaned datasets are stored in `data/instamart.db`, an SQLite database containing three tables:

- `customers`
- `products`
- `orders`

The database creation script defines primary keys, foreign keys and applicable constraints, loads the cleaned CSV data and checks foreign-key integrity.

The `order_ts` values are stored as SQLite-compatible text in the format:

```text
YYYY-MM-DD HH:MM:SS
```

### 3.7 SQL Analysis

Seven SQL queries are stored in `sql/queries.sql` and executed through Pandas using `pd.read_sql_query`.

| Query | Analysis | Result |
|---|---|---:|
| Q1 | High-spending customers with qualifying completed orders | 30 customers |
| Q2 | Revenue by city and product category | 30 groups |
| Q3 | Products priced above average catalogue price | 11 products |
| Q4 | Customers without completed orders | 25 customers |
| Q5 | Customers spending above average | 550 customers |
| Q6 | Customer spending rankings within each city | 1,175 customers |
| Q7 | Daily revenue and cumulative running total | 183 days |

**Q1 – High-spending customers**

Uses filtering and aggregation to identify customers whose qualifying completed-order spending exceeds INR 8,000.

**Q2 – Revenue by city and category**

Uses joins across customers, orders and products to calculate revenue by city and product category.

- Total completed revenue: INR 2,998,668.80.
- Highest city-category revenue: Bengaluru Electronics at INR 233,909.45.

**Q3 – Products above average catalogue price**

Uses a scalar subquery to identify products priced above the average catalogue price.

Result: 11 products.

**Q4 – Customers without completed orders**

Uses a LEFT JOIN to identify customers who have not placed a completed order.

Result: 25 customers.

**Q5 – Customers spending above average**

Uses a Common Table Expression (CTE) to calculate customer spending and the average customer spending.

- Average completed customer spend: approximately INR 2,552.06.
- Result: 550 customers above average.

**Q6 – Customer spending rankings**

Uses the window functions `RANK()`, `DENSE_RANK()` and `ROW_NUMBER()` to rank customers within each city.

There are eight rows where `RANK()` differs from `ROW_NUMBER()` because of tied spending values.

**Q7 – Daily revenue and running total**

Uses aggregation and the window function `SUM() OVER (ORDER BY day)` to calculate daily completed revenue and cumulative revenue.

The query produces 183 days, with a final cumulative revenue of INR 2,998,668.80.

### 3.8 Pandas Analysis

The analysis also uses:

- `pivot_table` with margins.
- Grouping and named aggregation.
- Descriptive statistics.
- Outlier detection using the IQR method.
- Correlation analysis.

**Revenue cross-checks**

- The Q2 pivot-table grand total matches INR 2,998,668.80.
- Bengaluru completed revenue is INR 523,643.40 across 1,894 orders.
- Mumbai completed revenue is INR 479,058.50 across 1,613 orders.

**Completed order amount statistics**

| Statistic | Result |
|---|---:|
| Mean | INR 269.91 |
| Median | INR 135.00 |
| Skewness | Approximately 4.61 |
| First quartile | INR 64.80 |
| Third quartile | INR 297.00 |
| Upper IQR fence | INR 645.30 |
| Upper outliers | 897 |
| Lower outliers | 0 |

The largest absolute correlation is between order amount and discount percentage (approximately -0.095).

The correlation between order amount and quantity is approximately +0.087.

Both relationships are weak, and correlation does not establish causation.

### 3.9 Exploratory Data Analysis Questions

**1. What is this data about?**

The dataset contains synthetic Swiggy Instamart customer, product and order information across six Indian cities. The analysis focuses on completed orders, amounts, quantities, discounts and delivery times.

**2. What do its distributions and statistics look like?**

Completed order amounts have a mean of INR 269.91 and median of INR 135.00, with positive skewness of approximately 4.61. Q1 is INR 64.80 and Q3 is INR 297.00, indicating that most orders have relatively low values.

**3. Are there outliers or anomalies?**

The 1.5 × IQR lower fence is INR -283.50 and the upper fence is INR 645.30. There are no lower outliers and 897 upper outliers. These high-value orders may represent unusually large purchases.

**4. What relationships exist between variables?**

The largest absolute correlation is between order amount and discount percentage (approximately -0.095). Order amount and quantity have a correlation of approximately +0.087. Both relationships are weak; correlation of this size does not establish causation.

### 3.10 Part A Validation

The script `src/validate_part_a.py` checks the cleaned datasets, database tables, row counts, data integrity and expected analytical results.

Run:

```bash
python src/validate_part_a.py
```

Successful execution prints:

```text
ALL CHECKPOINTS PASSED
```

Part A is implemented and validated.

---

## 4. Part B – Customer Segments and Lapse Prediction

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

K-Means clustering is evaluated for K values from 2 to 8. Each model uses:

- `n_init=10`
- `random_state=42`

Both inertia and silhouette score are used to evaluate the clustering results.

**K-Means comparison**

| K | Inertia | Silhouette Score |
|---:|---:|---:|
| 2 | 1,820.7606 | 0.4650 |
| 3 | 1,268.2346 | 0.4452 |
| 4 | 743.0711 | 0.5255 |
| 5 | 617.3666 | 0.4805 |
| 6 | 503.1706 | 0.4819 |
| 7 | 408.4605 | 0.4163 |
| 8 | 366.5035 | 0.4123 |

**Selected cluster count: K = 4**

K=4 is selected because it has the highest silhouette score among the evaluated values. It also provides a useful business interpretation through four distinct groups: Regular, Premium, Loyal and At Risk.

The elbow comparison supports this choice: inertia decreases substantially from K=3 (1,268.2346) to K=4 (743.0711), while the reductions become smaller after K=4.

K=8 has lower inertia than K=2 because inertia generally decreases as more clusters are added: individual points can be assigned to more closely located centroids. However, the lowest inertia alone does not identify the best clustering solution. A larger K can create unnecessary segmentation without improving separation or business usefulness. The silhouette score and interpretability therefore matter alongside inertia.

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
| `recency` | Days since the last completed order before the cutoff |
| `frequency` | Number of completed orders before the cutoff |
| `monetary` | Total completed-order spending before the cutoff |
| `avg_discount` | Average discount percentage on completed orders |
| `cancellation_rate` | Cancelled orders divided by all final-status orders |
| `avg_delivery` | Average delivery time of completed orders |
| `favorite_category` | Most frequently ordered product category |
| `city` | Customer city |
| `age` | Customer age |
| `gender` | Customer gender |
| `tenure_days` | Days since signup at the cutoff date |

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

The training-only scaler frequency mean is 8.1147, compared with the full-cohort frequency mean of 8.0285. This difference is expected because the scaler is fitted on the training subset rather than the entire cohort.

**Logistic Regression**

GridSearchCV evaluates the following C values:

```python
[0.01, 0.1, 1, 10, 100]
```

The maximum iteration count is 1,000, and five-fold cross-validation uses the F1-score.

Best parameter:

```text
C = 100
```

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

All 354 original minority-class records are retained, and 216 additional samples are drawn with replacement.

The resulting training distribution is:

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

```text
outputs/lapse_model.joblib
```

The saved model is loaded again, and its predictions are compared with the predictions from the original in-memory model.

The training script reports:

```text
PASS: Reloaded model reproduces test predictions exactly
```

This confirms that the saved model can be loaded and used to reproduce the same test predictions.

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

```text
outputs/retention_list.csv
```

It contains the following columns:

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

### 4.15 Part B Validation

The script `src/validate_part_b.py` checks:

- Required Part B output files exist.
- Customer segment records and Premium segment identification are valid.
- Premium is the segment with the highest average monetary value.
- Lapse dataset identifiers and target labels are valid.
- The saved model loads successfully.
- Model probability predictions are valid.
- The retention list contains valid Premium customers from the lapse cohort.
- Retention probabilities and actual lapse labels are valid.

Run:

```bash
python src/validate_part_b.py
```

The completed validation run prints:

```text
ALL PART B CHECKPOINTS PASSED
```

The latest training and validation runs also confirmed exact prediction reproduction after reloading the saved model.

Part B is implemented and validated.

---

## 5. Part C – Support Ticket Triage with Guardrails

### 5.1 Objective

Part C processes support tickets and prepares them for appropriate routing.

The implementation focuses on:

- Ticket input validation.
- Empty and excessively long ticket handling.
- Personally identifiable information (PII) redaction.
- Zero-shot and few-shot classification.
- Invalid model-output handling.
- Token-budget enforcement.
- Customer-segment-aware routing.
- Ticket priority assignment.

Part C consumes ticket data and uses customer segment information produced by Part B.

**Implementation scope:** The current implementation processes the supplied ticket CSV in a batch workflow. It does not provide a separate live customer text-entry frontend.

### 5.2 Ticket Dataset and Input Guardrails

The generated ticket dataset contains 164 tickets.

Input validation distinguishes between tickets that are ready for classification and tickets that need to be skipped or flagged.

| Input condition | Records |
|---|---:|
| Total tickets | 164 |
| Ready for classification | 156 |
| Empty tickets | 4 |
| Excessively long tickets | 4 |

Empty and excessively long tickets are handled by the input guardrails rather than being treated as ordinary classification requests.

### 5.3 PII Protection

Before classification, the ticket text is processed to redact personal information.

The redaction process identified:

| PII type | Redactions |
|---|---:|
| Email addresses | 55 |
| Phone numbers | 91 |
| Order IDs | 132 |
| **Total** | **278** |

The validation output confirmed that no targeted PII remained in the redacted ticket text.

Redaction helps reduce the exposure of personal information during downstream processing. It does not establish that every possible form of personal information has been removed.

### 5.4 Zero-Shot and Few-Shot Classification

The project compares two classification approaches using the supplied offline `mock_llm.py` implementation.

- **Zero-shot classification:** The classification request is made without providing labelled examples in the prompt.
- **Few-shot classification:** The classification request includes examples to guide the expected output format and classification behaviour.

The evaluation uses the 147 tickets that produced comparable classification results.

**Classification comparison**

| Measurement | Zero-shot | Few-shot |
|---|---:|---:|
| Classified tickets | 147 | 147 |
| Accuracy | 85.71% | 100% |
| Token count | 13,768 | 24,532 |

The few-shot approach achieved higher measured accuracy on this synthetic evaluation set, while using more estimated tokens.

These results describe the generated evaluation data and the deterministic offline model implementation. They should not be interpreted as real-world model accuracy.

### 5.5 Output Validation and Error Handling

Classification output is checked before it is accepted.

The processing workflow accounts for:

- Valid structured classification output.
- Keyword-based fallback classification.
- Invalid model output.
- Empty ticket text.
- Excessively long ticket text.

In the full classification run, the recorded status counts were:

| Processing status | Records |
|---|---:|
| Valid JSON classification | 135 |
| Keyword fallback | 12 |
| Invalid output flagged | 9 |
| Empty tickets | 4 |
| Long tickets flagged | 4 |

The invalid-output and input-guardrail statuses are kept distinct from successfully classified tickets.

### 5.6 Token Estimation and Budget Enforcement

The project uses the supplied `mock_llm.py` token estimator wherever token usage is required.

The estimator is based on whitespace-separated word count multiplied by 1.3 and rounded up.

The token-budget demonstration uses a configured budget of 6,000 tokens. The implementation checks the remaining budget before making another classification call.

**Latest token-budget demonstration**

| Measurement | Result |
|---|---:|
| Configured token budget | 6,000 |
| Actual estimated tokens | 5,995 |
| Budget-exhausted count | 88 |
| Valid JSON classifications | 59 |
| Keyword fallback classifications | 5 |
| Invalid outputs flagged | 4 |
| Empty tickets | 4 |
| Long tickets flagged | 4 |
| Classified tickets | 64 |

The token-budget test completed successfully and printed:

```text
TOKEN BUDGET TEST PASSED
```

The 5,995-token result is the latest corrected demonstration result.

### 5.7 Ticket Routing and Priority

After classification, tickets are routed using the classification results and customer information, including the customer segments produced by Part B.

**Final routing distribution**

| Destination | Tickets |
|---|---:|
| support_queue | 102 |
| security_team | 34 |
| human_review | 17 |
| premium_desk | 11 |
| **Total** | **164** |

**Priority distribution**

| Priority | Tickets |
|---|---:|
| HIGH | 45 |
| NORMAL | 119 |
| **Total** | **164** |

The routing stage connects the support-ticket workflow with the customer intelligence generated in Part B.

### 5.8 Part C Evaluation Summary

The Part C experiments demonstrate:

- Input validation for empty and excessively long tickets.
- PII redaction before classification.
- Comparison of zero-shot and few-shot classification.
- Structured-output validation and fallback handling.
- Token estimation and budget enforcement.
- Routing and priority assignment.
- Use of Part B customer segment information during ticket routing.

The results are based on the synthetic ticket dataset and the offline deterministic model stand-in.

---

## 6. Part D – Policy RAG Assistant and Refund Agent

### 6.1 Objective

Part D implements a policy question-answering workflow and a tool-using refund agent.

The implementation includes:

1. Policy document loading and chunking.
2. TF-IDF-based policy retrieval.
3. Retrieval-augmented policy question answering.
4. Evaluation using answerable and unanswerable questions.
5. Tool definitions and validation.
6. A ReAct-style refund agent.
7. Token and time guardrails.
8. Execution checkpointing and resume support.

The policy assistant and refund agent use the supplied offline `mock_llm.py` implementation. They do not connect to a live GPT API or an actual payment service.

### 6.2 Policy Documents and Chunking

Five policy documents are used as the knowledge base:

- Refund policy.
- Delivery policy.
- Escalation policy.
- Payment policy.
- Privacy policy.

The documents are split into chunks using:

- Chunk size: 40.
- Overlap: 10.

The resulting knowledge base contains 15 chunks.

| Policy document | Chunks |
|---|---:|
| Refund | 4 |
| Delivery | 3 |
| Escalation | 3 |
| Payment | 3 |
| Privacy | 2 |
| **Total** | **15** |

Chunk overlap helps retain context across neighbouring chunks.

### 6.3 TF-IDF Retrieval

The retrieval implementation uses:

- `TfidfVectorizer` from `sklearn.feature_extraction.text`.
- Cosine similarity to compare the query with the policy chunks.
- Top-three retrieval using `retrieve(query, k=3)`.

The retrieval process converts the policy chunks and user question into TF-IDF representations, compares their similarity and returns the three most relevant chunks.

This is a retrieval-based implementation rather than a vector database or embedding API integration.

### 6.4 Retrieval-Augmented Policy Answering

The policy answering function is:

```python
answer(question)
```

For each question, the workflow:

1. Retrieves the three most relevant policy chunks.
2. Prepares the policy context.
3. Sends exactly two messages to `mock_llm`.
4. Returns the resulting policy answer or the configured fallback when the question cannot be answered from the available policy context.

The fallback behaviour is important because the assistant should not invent policy information when the retrieved material does not support an answer.

### 6.5 Policy Retrieval Evaluation

The evaluation dataset, `policy_eval.csv`, contains 14 questions:

- 12 answerable questions.
- 2 unanswerable questions.

The evaluation checks expected source documents, expected facts and fallback behaviour.

**Evaluation with the configured overlap**

| Evaluation check | Result |
|---|---:|
| Expected documents retrieved | 12/12 |
| Expected facts retrieved | 12/12 |
| Unanswerable questions handled with fallback | 2/2 |

**Evaluation with zero overlap**

| Evaluation check | Result |
|---|---:|
| Expected documents retrieved | 12/12 |
| Expected facts retrieved | 10/12 |
| Unanswerable questions handled with fallback | 2/2 |

With zero overlap, two expected facts were missed because of sentence splitting: the 45-minute delivery condition and the 48-hour condition.

The comparison demonstrates why chunk overlap is useful for retaining policy context across chunk boundaries.

### 6.6 Refund Agent Tools

The agent uses five tools:

| Tool | Purpose |
|---|---|
| `get_order` | Retrieve order information |
| `search_policy` | Retrieve relevant policy information |
| `calculate_refund` | Calculate the refund amount according to the policy |
| `issue_refund` | Validate and record an eligible simulated refund |
| `escalate_to_human` | Validate and record an eligible escalation |

The tools are registered through `TOOLS_SPEC` and `TOOL_MAP`.

The agent can request tool execution, receive tool observations and use those observations during its subsequent reasoning steps.

### 6.7 Refund Policy and Validation Rules

The implemented refund rules are:

- Only completed orders are eligible for the refund calculation.
- If delivery time is greater than 45 minutes, the refund amount is 100% of the order amount.
- If delivery time is 45 minutes or less, the refund amount is zero.
- Refund amounts greater than INR 1,000 must be escalated to a human.
- The demonstrated scenarios are within the seven-day policy window.

**Refund validation**

The `issue_refund` tool checks:

1. The order exists.
2. The order is completed.
3. Delivery time is greater than 45 minutes.
4. The refund amount is positive.
5. The requested amount matches the calculated amount within a tolerance of INR 0.01.
6. The refund amount does not exceed INR 1,000.

**Human escalation validation**

The `escalate_to_human` tool checks:

1. The order exists.
2. The order is completed.
3. Delivery time is greater than 45 minutes.
4. The refund amount is greater than INR 1,000.
5. The requested amount matches the calculated amount.

These checks prevent the agent from directly recording an invalid refund or escalation through the implemented tools.

**Important:** These are simulated tool operations. They do not transfer money, contact an actual support team or update a real Swiggy system.

### 6.8 ReAct Agent Execution

The refund agent is executed using:

```python
run_agent(
    user_message,
    scenario_id,
    max_iterations=6,
    token_limit=6000,
    time_limit_seconds=10
)
```

The agent follows a ReAct-style workflow:

1. Receive the user request.
2. Reason about the next required action.
3. Request a tool call when needed.
4. Execute the selected tool.
5. Observe the tool result.
6. Continue until a final result or a configured stopping condition is reached.

The maximum iteration count is six, the default token limit is 6,000, and the default time limit is 10 seconds.

### 6.9 Agent Scenario Evaluation

Seven scenarios are used to evaluate the refund agent.

| Scenario | Final result |
|---|---|
| S1 | REFUND – INR 128.25 |
| S2 | REFUND – INR 135 |
| S3 | ESCALATE – INR 1,999 |
| S4 | DENIED |
| S5 | DENIED |
| S6 | NOT_FOUND |
| S7 | FALLBACK_MAX_ITERATIONS |

The scenarios cover eligible refunds, escalation, denied requests, missing orders and a maximum-iteration fallback.

### 6.10 Token and Time Guardrails

The agent includes token and time limits.

**Token-limit demonstration**

With a token limit of 200, the agent returned:

```text
FALLBACK_TOKEN_LIMIT
```

The recorded token count was 221, and no tools were executed.

**Time-limit demonstration**

With a time limit of zero, the agent returned:

```text
FALLBACK_TIMEOUT
```

No tool calls were executed.

These demonstrations show that the configured guardrails can stop execution before the agent proceeds with tool operations.

### 6.11 Checkpointing and Resume Support

The agent records execution state and supports resuming an interrupted run.

Checkpoint information includes:

- Run identifiers.
- Messages.
- Token usage.
- Execution steps.
- Tool calls and observations.

A checkpoint is saved after each tool observation.

**Resume demonstration**

Scenario S1 was interrupted after two tool calls and then resumed.

The resumed execution completed with:

| Measurement | Result |
|---|---:|
| Final result | REFUND |
| Refund amount | INR 128.25 |
| Total tool calls | 5 |
| Total tokens | 1,807 |

The resumed workflow completed without repeating the previously completed tool calls in the demonstration.

### 6.12 ReAct and Plan-and-Execute Comparison

The project includes a comparison of ReAct and plan-and-execute approaches.

The comparison is documented within the implementation in fewer than 250 words.

Observed ReAct tool-call counts include:

| Scenario | Tool calls |
|---|---:|
| S1 | 5 |
| S5 | 3 |
| S6 | 2 |

ReAct is selected for the implemented workflow because it supports sequential reasoning using the observations returned by tools. The agent can decide its next action based on the result of the previous tool call.

### 6.13 Part D Execution Records

Agent execution records are stored in:

```text
outputs/agent_runs.jsonl
```

The agent also uses checkpoint and state files to support resumable execution.

The latest audit reported 14 records in the execution log, with the latest seven scenario records passing their checks.

The master runner backs up existing agent ledger and state files before running the agent demonstrations, helping preserve previous execution records.

### 6.14 Part D Evaluation Summary

The Part D implementation demonstrates:

- Policy document loading.
- Chunking with overlap.
- TF-IDF retrieval and cosine similarity.
- Top-three policy retrieval.
- Policy question answering with fallback handling.
- Evaluation of answerable and unanswerable questions.
- Five registered agent tools.
- Refund amount calculation and validation.
- Human escalation validation.
- ReAct-style tool execution.
- Token and time guardrails.
- Checkpointing and resume support.
- Evaluation across seven agent scenarios.

The implementation uses synthetic data, local policy documents and simulated tool operations. It does not issue real refunds or connect to an external payment system.

---

## 7. Project Outputs and Validation Summary

The project produces intermediate and final outputs across its four connected parts.

### Part A

- Cleaned customer, product and order datasets.
- SQLite analytical database.
- SQL query results.
- Pandas analysis results.
- Part A validation results.

### Part B

- Customer RFM segments.
- K-Means comparison results.
- Lapse prediction dataset.
- Saved Random Forest model.
- Model comparison and feature-importance results.
- Premium customer retention shortlist.

### Part C

- Ticket classification results.
- Redacted ticket text.
- Classification and fallback status information.
- Token-budget demonstration results.
- Routed tickets and priority assignments.

### Part D

- Policy retrieval and evaluation results.
- Agent execution records.
- Simulated refund and escalation outcomes.
- Agent checkpoint and resume state.

### Validation status

| Part | Validation evidence |
|---|---|
| Part A | Validation script reports `ALL CHECKPOINTS PASSED`. |
| Part B | Validation script reports `ALL PART B CHECKPOINTS PASSED`; model reload reproduces test predictions exactly. |
| Part C | Token-budget demonstration reports `TOKEN BUDGET TEST PASSED`; classification and routing results are recorded. |
| Part D | Policy retrieval evaluation, seven agent scenarios, guardrail demonstrations and resume demonstration have recorded results. |

---

## 8. Limitations and Next Steps

- The datasets are synthetic and do not represent actual Swiggy customer or transaction records.
- The project does not connect to a live Swiggy database or production support system.
- The supplied `mock_llm.py` is a deterministic offline stand-in. No live GPT API integration is implemented.
- Part C currently processes tickets from a CSV batch workflow. A separate interactive customer text-entry frontend is not implemented.
- The ticket classification results are measured on the generated synthetic evaluation data and should not be interpreted as real-world model performance.
- PII redaction covers the targeted email, phone and order-ID patterns. It does not establish that every possible form of personal information is removed.
- The lapse model uses historical synthetic customer behaviour and may not generalize to real customer behaviour.
- The Premium retention shortlist uses a whole-window RFM segment flag that includes September 2025. It is illustrative and is not a leakage-free historical evaluation. The lapse prediction model itself uses only pre-cutoff features.
- The retention shortlist contains 10 customers, of whom 1 was actually lapsed in the evaluated data. It should not be presented as a highly accurate retention list.
- Model performance is evaluated on the generated synthetic dataset and should not be interpreted as real-world business performance.
- Policy retrieval uses TF-IDF and cosine similarity rather than an external embedding service or vector database.
- Refund and escalation tools perform simulated operations. They do not issue actual payments, contact real support staff or update production systems.
- The agent's token estimator is the supplied approximate estimator and should not be interpreted as the exact token count of a commercial LLM.
- Correlation analysis identifies statistical relationships but does not establish causal effects.

Parts A, B, C and D have been implemented with the outputs and evaluation results documented above. The project demonstrates a connected synthetic customer intelligence and support workflow, from raw-data preparation through customer segmentation, ticket triage, policy retrieval and simulated refund-agent execution.