# Customer Intelligence & Support Copilot

## 1. Overview

This project develops a Customer Intelligence and Support Copilot for Swiggy Instamart using synthetic customer, product, order and support-ticket data.

The project is organized into four connected parts:

- **Part A – Data Foundation:** Audit, clean and standardize raw data, store trusted data in SQLite, and perform SQL and Pandas analysis.
- **Part B – Customer Segments and Lapse Prediction:** Apply RFM analysis, customer segmentation and machine-learning-based lapse prediction.
- **Part C – Support Ticket Triage with Guardrails:** Process support tickets, protect personal information, classify issues and route tickets.
- **Part D – Policy RAG Assistant and Refund Agent:** Retrieve company policy information and implement a tool-using refund agent with safety checks.

The four parts share data and outputs. Part B produces customer segments used by Part C. Part D queries the cleaned database from Part A and uses policy retrieval to support refund decisions.

All monetary values are represented in Indian Rupees (INR). The data is synthetic and intended for academic demonstration.

## 2. Reproduction

### 2.1 Prerequisites

- Python 3.12 or a compatible Python version.
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

```powershell
python -m pip install -r requirements.txt
```

### 2.5 Generate the synthetic data

Run the supplied generator once when setting up a fresh repository:

```powershell
python generate_data.py
```

This generates the raw CSV files and policy documents used by the project.

The supplied `generate_data.py` and `mock_llm.py` files are retained unmodified.

**Important:** Do not rerun the data generator when you want to rebuild the project using the existing raw data, because it regenerates the raw datasets.

### 2.6 Run the complete project

The master runner executes the project stages in dependency order, including the Part A data foundation, Part B customer analysis, Part C ticket triage and Part D policy and agent demonstrations.

```powershell
python run_project.py
```

The runner uses the existing raw data and does not automatically rerun `generate_data.py`. It stops if a required stage fails and runs independent stages in parallel where appropriate.

### 2.7 Individual scripts

Individual scripts can also be executed when testing or debugging a particular component.

**Part A:**

```powershell
python src/audit_raw_data.py
python src/clean_data.py
python src/create_database.py
python src/validate_part_a.py
python src/run_sql_analysis.py
```

**Part B:**

```powershell
python src/build_customer_segments.py
python src/prepare_lapse_data.py
python src/train_lapse_models.py
python src/create_retention_list.py
python src/validate_part_b.py
```

**Part C:**

```powershell
python src/triage_tickets.py
```

**Part D:**

```powershell
python src/policy_rag.py
python src/refund_tools.py
python src/refund_agent.py
```

The master runner is recommended for a complete rebuild because it manages dependencies and the order in which outputs are generated.

## 3. Part A – Data Foundation: Clean, Store and Query

### 3.1 Overview

Part A converts generated raw data into a trusted analytical dataset. It includes raw-data auditing, customer and order cleaning, SQLite database creation, SQL analysis and exploratory analysis using Pandas.

### 3.2 Raw data audit

Six raw CSV files are generated:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `tickets.csv`
- `agent_scenarios.csv`
- `policy_eval.csv`

The audit script examines dataset shapes, data types, missing-value counts and missing-value percentages.

Important raw-data audit results:

| Audit item | Result |
|---|---:|
| Raw order rows | 13,084 |
| Exact duplicate order rows | 119 |
| Pending order rows | 656 |
| Distinct order IDs | 12,309 |
| Non-numeric or missing order amounts | 120 |
| Negative delivery times | 106 |
| Blank delivery times | 2,541 |
| Blank customer ages | 61 |
| Customer ages outside 10–100 | 6 |
| Distinct raw city spellings | 24 |
| Distinct non-blank gender spellings | 10 |
| Blank gender values | 30 |

### 3.3 Customer data cleaning

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

Ages outside the range of 10–100 are treated as missing. Missing ages are filled using the median age of the corresponding city, calculated using `groupby` and `transform`. Signup dates are converted to datetime values.

Final city counts:

| City | Customers |
|---|---:|
| Pune | 227 |
| Delhi | 210 |
| Bengaluru | 197 |
| Chennai | 191 |
| Hyderabad | 191 |
| Mumbai | 184 |
| **Total** | **1,200** |

Final gender counts:

| Gender | Customers |
|---|---:|
| Female | 610 |
| Male | 560 |
| Unknown | 30 |

No missing ages remain, and the cleaned age range is 18–60.

### 3.4 Product data cleaning

The product dataset retains all 40 rows. No product cleaning changes were required because the raw product data passed the relevant missing-value checks.

### 3.5 Order data cleaning

The order-cleaning process applies the following operations:

1. Convert `order_ts` into datetime values.
2. Remove 119 exact duplicate rows.
3. Resolve duplicate order IDs by retaining the record with the latest `order_ts`.
4. Standardize order statuses by removing surrounding whitespace and converting values to lowercase.
5. Remove pending orders remaining after duplicate-ID resolution.
6. Convert order amounts to numeric values and fill missing or invalid amounts using product price, quantity and discount.
7. Treat negative delivery-time values as missing.
8. Fill missing delivery times for completed orders using the median delivery time of the corresponding product category.
9. Keep cancelled-order delivery times missing because cancelled orders were never delivered.

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

Completed-order revenue is **INR 29,98,668.80**.

### 3.6 SQLite database

The cleaned datasets are stored in `data/instamart.db`, an SQLite database containing three tables:

- `customers`
- `products`
- `orders`

The database creation script defines primary keys, foreign keys and applicable constraints, loads the cleaned CSV data and checks foreign-key integrity.

### 3.7 SQL analysis

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

Q2 produces total completed revenue of INR 29,98,668.80. The highest city-category revenue is Bengaluru Electronics at INR 2,33,909.45.

Q5 calculates average completed customer spend of approximately INR 2,552.06.

Q6 demonstrates `RANK()`, `DENSE_RANK()` and `ROW_NUMBER()` window functions. There are eight rows where `RANK()` differs from `ROW_NUMBER()` because tied spending values receive the same rank, while `ROW_NUMBER()` always assigns a distinct sequential number.

Q7 produces a final cumulative revenue of INR 29,98,668.80.

### 3.8 Pandas analysis

The analysis also uses:

- `pivot_table` with margins.
- Named aggregation.
- Descriptive statistics.
- IQR-based outlier detection.
- Correlation analysis.

Results include:

- The Q2 pivot-table grand total matches INR 29,98,668.80.
- Bengaluru completed revenue is INR 5,23,643.40 across 1,894 orders.
- Mumbai completed revenue is INR 4,79,058.50 across 1,613 orders.
- Completed-order amount mean: INR 269.91.
- Median: INR 135.00.
- Skewness: approximately 4.61.
- First quartile: INR 64.80.
- Third quartile: INR 297.00.
- Upper IQR fence: INR 645.30.
- Upper outliers: 897; lower outliers: 0.

The largest absolute correlation is between order amount and discount percentage (approximately -0.095). The correlation between order amount and quantity is approximately +0.087. Both relationships are weak, and correlation does not establish causation.

### 3.9 Exploratory Data Analysis questions

**1. What is this data about?**

The dataset contains synthetic Swiggy Instamart customer, product and order information across six Indian cities. The analysis focuses on completed orders, amounts, quantities, discounts and delivery times.

**2. What do its distributions and statistics look like?**

Completed order amounts have a mean of INR 269.91 and median of INR 135.00, with positive skewness of approximately 4.61. Q1 is INR 64.80 and Q3 is INR 297.00, indicating that most orders have relatively low values.

**3. Are there outliers or anomalies?**

The 1.5 × IQR lower fence is INR -283.50 and the upper fence is INR 645.30. There are no lower outliers and 897 upper outliers. These high-value orders may represent unusually large purchases.

**4. What relationships exist between variables?**

The largest absolute correlation is between order amount and discount percentage (approximately -0.095). Order amount and quantity have a correlation of approximately +0.087. Both relationships are weak; correlation of this size does not establish causation.

### 3.10 Part A validation

The script `src/validate_part_a.py` checks the cleaned datasets, database tables, row counts, data integrity and expected analytical results.

Successful execution prints:

```text
ALL CHECKPOINTS PASSED
```

## 4. Part B – Customer Segments and Lapse Prediction

### 4.1 Overview

Part B uses the clean customer and order datasets from Part A to identify meaningful customer groups and predict which customers are likely to stop ordering.

The two main components are:

- RFM-based customer segmentation using K-means clustering.
- Lapse prediction using Logistic Regression and Random Forest models.

The resulting customer segment file is also used by Part C for support-ticket routing.

### 4.2 RFM analysis

RFM analysis is performed using completed orders only.

The snapshot date is `2025-10-01 00:00:00`.

The three RFM measures are:

- **Recency:** Number of whole days between the snapshot and the customer's most recent completed order.
- **Frequency:** Number of distinct completed orders placed by the customer.
- **Monetary:** Total completed order amount spent by the customer.

RFM results:

| Metric | Result |
|---|---:|
| Customers with completed orders | 1,175 |
| Recency median | 19 days |
| Minimum recency | 0 days |
| Maximum recency | 180 days |
| Mean frequency | 9.46 |
| Maximum frequency | 33 |
| Mean monetary value | INR 2,552.06 |
| Maximum monetary value | INR 14,766.55 |

### 4.3 K-means customer segmentation

The three RFM features are standardized using `StandardScaler` before clustering.

K-means is evaluated for every K from 2 to 8 using:

- `KMeans`
- `n_clusters`
- `n_init=10`
- `random_state=42`
- Inertia
- Silhouette score

The actual model comparison results are:

| K | Inertia | Silhouette Score |
|---:|---:|---:|
| 2 | 1820.7606 | 0.4650 |
| 3 | 1268.2346 | 0.4452 |
| 4 | 743.0711 | 0.5255 |
| 5 | 617.3666 | 0.4805 |
| 6 | 503.1706 | 0.4819 |
| 7 | 408.4605 | 0.4163 |
| 8 | 366.5035 | 0.4123 |

**Selected number of clusters: K = 4**

K=4 was selected because it achieved the highest silhouette score (0.5255) among the tested configurations. The elbow comparison also shows a substantial reduction in inertia from K=3 to K=4, followed by smaller improvements as K increases. Four clusters provide a useful balance between cluster separation and business interpretability, allowing the retention team to work with four actionable customer groups.

Inertia at K=8 is lower than at K=2 because increasing the number of clusters gives K-means more centroids, allowing customers to be closer to their assigned centroid. However, inertia generally decreases as K increases, so the lowest inertia alone cannot identify the best number of clusters. The elbow, silhouette scores and usefulness of the resulting segments must also be considered.

The final K-means model uses:

```python
KMeans(
    n_clusters=4,
    n_init=10,
    random_state=42
)
```

Cluster IDs are arbitrary labels and do not represent customer value or ranking. The clusters are assigned descriptive names based on their RFM profiles.

### 4.4 PCA explained variance

Principal Component Analysis (PCA) is performed using exactly two components on the standardized RFM features: recency, frequency and monetary.

| Component | Explained Variance Ratio |
|---|---:|
| PC1 | 0.634 |
| PC2 | 0.218 |
| **Combined** | **0.852** |

The first principal component explains 63.4% of the variance, while the second explains 21.8%. Together, the two components retain approximately 85.2% of the total variance in the standardized RFM data.

### 4.5 Customer segment profiles

The four segments are named according to their observed RFM characteristics.

| Segment | Customers | Mean Recency | Mean Frequency | Mean Monetary |
|---|---:|---:|---:|---:|
| Regular | 436 | 28.86 days | 3.77 | INR 1,057.62 |
| Premium | 138 | 24.12 days | 6.77 | INR 7,129.70 |
| Loyal | 419 | 8.77 days | 19.40 | INR 3,410.02 |
| At Risk | 182 | 109.04 days | 2.20 | INR 685.99 |
| **Total** | **1,175** | | | |

Business interpretation and recommended actions:

| Segment | Interpretation | Recommended action |
|---|---|---|
| Regular | Customers with moderate or relatively low order activity | Encourage repeat purchases through relevant offers |
| Premium | Customers with the highest average monetary value | Provide personalized offers and prioritize retention |
| Loyal | Customers with frequent and recent purchases | Encourage continued engagement and loyalty |
| At Risk | Customers with high recency and low purchase frequency | Use reactivation campaigns and targeted incentives |

The Premium segment is selected based on its highest mean monetary value. The `is_premium` flag is set to 1 for customers belonging to this segment and 0 for all other customers.

### 4.6 Lapse prediction problem

The lapse prediction task uses the cutoff date `2025-09-01`.

The cohort includes customers with at least one completed order before the cutoff.

A customer is labelled as lapsed if they have no completed order dated from `2025-09-01` through `2025-09-30`.

The model features are constructed using only information available before the cutoff:

- Recency.
- Frequency.
- Monetary.
- Average discount percentage.
- Cancellation rate.
- Average delivery time.
- Favourite product category.
- City.
- Age.
- Gender.
- Customer tenure.

No order dated on or after `2025-09-01` enters the model features. Segment labels from the RFM task are not used as model features.

Cohort results:

| Metric | Result |
|---|---:|
| Eligible customers | 1,156 |
| Lapsed customers | 443 |
| Not-lapsed customers | 713 |
| Lapsed percentage | 38.32% |
| Training rows | 924 |
| Test rows | 232 |

The train-test split uses `test_size=0.2`, `stratify=y` and `random_state=42`.

The baseline model always predicts not lapsed:

- Baseline accuracy: approximately 61.6%.
- Baseline lapsed-class F1: 0.

### 4.7 Preprocessing and leakage prevention

The preprocessing pipeline includes:

- One-hot encoding of nominal features.
- Standardization of numeric features.
- Training-only fitting of preprocessing transformations.

The nominal variables include city, gender and favourite product category. One-hot encoding uses `OneHotEncoder(drop="first")`, which creates k−1 columns for each nominal variable.

The numeric features are standardized using a fitted scaler.

The encoder and scaler are fitted only on the training rows. They are then applied to the test rows without refitting.

No encoder, scaler or resampler saw test rows during fitting. No data from `2025-09-01` onwards entered the model features, and the Part B segment labels were not used as features.

The feature data is checked for missing values before model training.

The learned training-set frequency mean can differ from the full-cohort frequency mean because the scaler is fitted on the training subset rather than the complete cohort.

### 4.8 Model training and hyperparameter tuning

Two classification algorithms are evaluated.

**Logistic Regression**

```python
LogisticRegression(max_iter=1000)
```

The hyperparameter grid is:

```python
C = [0.01, 0.1, 1, 10, 100]
```

Grid search uses:

- `GridSearchCV`
- `cv=5`
- `scoring="f1"`

The selected Logistic Regression configuration uses `C=100`, with a best cross-validation F1 of approximately 0.6506.

**Random Forest**

```python
RandomForestClassifier(
    n_estimators=100,
    random_state=42
)
```

The hyperparameter grid is:

```python
n_estimators = [100]
max_depth = [3, 5, 8]
min_samples_leaf = [5, 10, 20]
```

Grid search uses:

- `GridSearchCV`
- `cv=5`
- `scoring="f1"`

The selected Random Forest configuration uses:

- `n_estimators=100`
- `max_depth=8`
- `min_samples_leaf=10`
- `random_state=42`

Its best cross-validation F1 is approximately 0.6811. The grid contains nine parameter combinations evaluated across five folds, giving 45 fits.

**Final model selection**

The final model is selected by comparing the cross-validation F1 scores of the Logistic Regression and Random Forest models. Random Forest is selected because it achieves the higher cross-validation F1 score (approximately 0.6811 compared with approximately 0.6506 for Logistic Regression). The test set is not used for model selection.

### 4.9 Model evaluation

The tuned models are evaluated on the untouched test set. Precision, recall and F1 are calculated for the positive class, `lapsed`.

**Logistic Regression**

Confusion matrix:

```text
[[111, 32],
 [ 31, 58]]
```

| Metric | Result |
|---|---:|
| Precision | 0.6444 |
| Recall | 0.6517 |
| F1-score | 0.6480 |

**Random Forest**

Confusion matrix:

```text
[[113, 30],
 [ 31, 58]]
```

| Metric | Result |
|---|---:|
| Precision | 0.6591 |
| Recall | 0.6517 |
| F1-score | 0.6554 |

The Random Forest achieves a slightly higher test F1-score and precision than the tuned Logistic Regression model.

The cost of missing a lapsing customer is potentially losing future purchases and retention opportunities. However, wrongly targeting a loyal customer can waste campaign resources and incentives. The selected Random Forest model provides a slightly better balance of precision and recall on the test set than the original Logistic Regression model. The retention team should consider the available campaign budget and the cost of incentives when deciding how many high-risk customers to contact.

### 4.10 Class-balance experiment

The lapsed class is the minority class.

To study the effect of class imbalance, the training set is oversampled by retaining all original training rows and adding randomly selected duplicate lapsed training rows until both classes have equal counts.

Oversampling is performed only on the training data. The original test set remains unchanged.

Balanced training counts:

| Class | Rows |
|---|---:|
| Not lapsed | 570 |
| Lapsed | 570 |

The best Logistic Regression model is refitted on this balanced training data.

Oversampled Logistic Regression results:

Confusion matrix:

```text
[[90, 53],
 [13, 76]]
```

| Metric | Original Logistic Regression | Oversampled Logistic Regression |
|---|---:|---:|
| Precision | 0.6444 | 0.5891 |
| Recall | 0.6517 | 0.8539 |
| F1-score | 0.6480 | 0.6972 |
| Accuracy | 0.7284 | 0.7155 |

Recall increases from approximately 0.6517 to 0.8539, the largest improvement among the reported precision, recall and F1 metrics. This means the oversampled model identifies a larger proportion of customers who are actually lapsing, which is useful for retention campaigns. However, precision decreases, so the retention team may need to contact more customers who would not have lapsed.

The oversampled model demonstrates the trade-off between identifying more at-risk customers and increasing false-positive targeting. It is an experiment and is not the model selected for the final saved prediction model.

### 4.11 Feature interpretation

The Random Forest model's five leading features are:

| Feature | Importance |
|---|---:|
| Frequency | 0.2796 |
| Monetary | 0.2712 |
| Recency | 0.1151 |
| Average delivery time | 0.0613 |
| Cancellation rate | 0.0523 |

Frequency and monetary value are the most influential features in the fitted Random Forest model. This indicates that customer purchasing behaviour contributes substantially to the model's predictions.

The leading Logistic Regression coefficients include:

| Feature | Coefficient | Interpretation |
|---|---:|---|
| Frequency | -1.698 | Higher purchase frequency is associated with lower predicted lapse likelihood |
| Favourite category: Electronics | -1.137 | This category has a negative coefficient relative to the reference category |
| Monetary | -0.449 | Higher spending is associated with lower predicted lapse likelihood |

A negative coefficient indicates a decrease in the model's predicted log-odds of the lapsed class, holding other features constant.

### 4.12 Model persistence and retention list

The selected model is saved using `joblib.dump` to:

```text
outputs/lapse_model.joblib
```

The saved model is loaded using `joblib.load` for subsequent predictions and validation.

The retention list is generated using the saved model in `outputs/lapse_model.joblib`.

It is created by:

1. Recreating the same stratified 80:20 train-test split using `random_state=42`.
2. Identifying Premium customers using the `is_premium` flag from `customer_segments.csv`.
3. Selecting Premium customers belonging to the test set.
4. Calculating predicted lapse probabilities using the saved model.
5. Ranking the selected customers by predicted lapse probability in descending order.
6. Saving the top 10 customers, or all eligible customers if fewer than 10 exist.

The retention list is saved to:

```text
outputs/retention_list.csv
```

It contains the columns:

```text
customer_id, lapse_probability, actually_lapsed
```

The regenerated retention list contains 10 Premium customers, with one customer actually lapsed.

**Important limitation:** The Premium flag is based on whole-window RFM information, including the September period used to define the lapse label. Therefore, the retention list is illustrative and is not a leakage-free evaluation, even though the model's own features use only pre-cutoff orders.

### 4.13 Part B outputs

| Output | Purpose |
|---|---|
| `outputs/customer_segments.csv` | Customer RFM values, segment assignments and Premium flag |
| `outputs/kmeans_comparison.csv` | Inertia and silhouette comparison for K=2 to K=8 |
| `outputs/lapse_dataset.csv` | Prepared customer features and lapse labels |
| `outputs/lapse_model.joblib` | Saved selected lapse prediction model |
| `outputs/retention_list.csv` | Top Premium-segment customers ranked by predicted lapse probability |

The customer segment output contains:

```text
customer_id, recency, frequency, monetary, segment_id, segment_name, is_premium
```

### 4.14 Part B validation

The script `src/validate_part_b.py` checks:

- Required output files.
- Customer segment columns and unique customer IDs.
- Premium flag consistency with the highest-mean-monetary segment.
- Lapse dataset IDs, labels and missing values.
- Saved model loading and predicted probability validity.
- Retention list columns, ordering, customer membership and actual labels.

Successful execution prints:

```text
ALL PART B CHECKPOINTS PASSED
```

## 5. Part C – Support Ticket Triage with Guardrails

### 5.1 Overview

Part C builds a safe and resilient support-ticket triage pipeline using the supplied `mock_llm.py`.

The pipeline processes the 164 tickets in `data/raw/tickets.csv`. It applies input guardrails, removes personal information before model calls, compares zero-shot and few-shot classification, validates model responses, implements retries and token-budget controls, and routes tickets using the customer segments produced in Part B.

### 5.2 Input guardrails

Before any model call, each ticket is checked.

- Empty or whitespace-only tickets receive `skipped_empty`.
- Tickets whose estimated token count exceeds `MAX_INPUT_TOKENS = 400` receive `flagged_long`.
- Neither type of ticket is sent to the model.

The token estimate uses the supplied `mock_llm.est_tokens()` function.

Input guardrail results:

| Status | Tickets |
|---|---:|
| Ready for classification | 156 |
| `skipped_empty` | 4 |
| `flagged_long` | 4 |
| **Total** | **164** |

The four long tickets have an estimated length of 734 tokens.

### 5.3 Privacy protection and PII redaction

Personal information is redacted before ticket text is sent to the model.

The following patterns and placeholders are applied:

| Personal information | Replacement | Substitutions |
|---|---|---:|
| Email | `[EMAIL]` | 55 |
| Phone | `[PHONE]` | 91 |
| Order ID | `[ORDER_ID]` | 132 |
| **Total** | | **278** |

The redacted ticket texts are checked again using all three patterns.

Verification finds zero remaining email addresses, phone numbers or order IDs.

An assertion in the code checks that no personal information remains before a model call. The user message content sent to the model consists of the redacted ticket text.

### 5.4 Zero-shot and few-shot prompts

Two system prompts are implemented.

**Zero-shot prompt**

The zero-shot prompt instructs the model to classify tickets into exactly four allowed categories:

- `billing`
- `delivery`
- `technical`
- `fraud`

It requires a JSON-only response:

```json
{"category": "...", "reason": "..."}
```

It does not contain the `EXAMPLES:` section.

**Few-shot prompt**

The few-shot prompt contains the same classification instructions and allowed categories. It also includes an `EXAMPLES:` section with labelled examples, including a fraud example.

Both prompts are validated through code assertions.

### 5.5 Retry mechanism

The supplied mock model can raise `TransientLLMError`. Every model call is therefore wrapped in a retry function.

The retry configuration is:

| Setting | Value |
|---|---:|
| Maximum retries | 3 |
| Base delay | 0.05 seconds |
| Jitter range | 0.9–1.15 |
| Backoff | Exponential |

The wait before retry number `n` is:

```python
BASE_DELAY * (2 ** n) * random.uniform(0.9, 1.15)
```

Each retry prints a log containing the ticket ID, retry number and wait duration.

`mock_llm.reset()` is called immediately before each full classification run.

For each full run over the 156 eligible tickets:

| Retry result | Count |
|---|---:|
| Transient errors | 19 |
| Recovered errors | 19 |
| Permanent errors | 0 |

All transient errors are recovered successfully.

### 5.6 Output validation

Every model response is validated before a category is accepted.

The pipeline first attempts to parse the response as JSON. If the category is one of the four allowed values, the status is `classified_json`.

If the response is not valid JSON, the pipeline extracts lowercase words using:

```python
re.findall(r"[a-z]+", text.lower())
```

If exactly one allowed category word is present, the result receives `classified_keyword`.

All other outputs, including valid JSON containing an unsupported category, receive `flagged_invalid_output`.

The pipeline never guesses a category for an invalid response.

Validation results for a full comparison run:

| Status | Tickets |
|---|---:|
| `classified_json` | 135 |
| `classified_keyword` | 12 |
| `flagged_invalid_output` | 9 |
| `skipped_empty` | 4 |
| `flagged_long` | 4 |
| **Total** | **164** |

A total of 147 tickets are successfully classified.

### 5.7 Zero-shot and few-shot comparison

The full pipeline is run once with each prompt without a token budget.

| Metric | Zero-shot | Few-shot |
|---|---:|---:|
| Classified tickets | 147 | 147 |
| Accuracy | 85.71% | 100% |
| Total tokens | 13,768 | 24,532 |
| Tokens per classified ticket | 93.66 | 166.88 |

The zero-shot confusion table is:

| Actual category | Predicted billing | Predicted delivery | Predicted technical | Predicted fraud |
|---|---:|---:|---:|---:|
| Billing | 38 | 0 | 0 | 0 |
| Delivery | 0 | 36 | 0 | 0 |
| Technical | 10 | 0 | 29 | 0 |
| Fraud | 11 | 0 | 0 | 23 |

The few-shot prompt uses 10,764 additional tokens compared with the zero-shot prompt. This is an increase of approximately 78.18% in total token usage.

The extra few-shot tokens are worthwhile when classification accuracy is especially important for support operations. Zero-shot classification achieves 85.71% accuracy, while few-shot classification achieves 100% on the same 147 classified tickets. In particular, zero-shot errors include fraud and technical tickets incorrectly classified as billing, which could cause inappropriate routing. For a support workflow where incorrect fraud routing can have significant consequences, the higher few-shot token cost is justified.

### 5.8 Token-budget demonstration

A token budget is checked before every model call.

If the running token total is already greater than or equal to the configured budget, no further model call is made and the ticket receives `budget_exhausted`.

The zero-shot budget demonstration uses:

```python
TOKEN_BUDGET = 6000
```

Latest verified results:

| Metric | Result |
|---|---:|
| Configured budget | 6,000 |
| Actual tokens consumed | 5,995 |
| Tickets marked `budget_exhausted` | 88 |
| Successfully classified | 64 |
| `classified_json` | 59 |
| `classified_keyword` | 5 |
| `flagged_invalid_output` | 4 |
| `skipped_empty` | 4 |
| `flagged_long` | 4 |

The token count remains within the configured budget.

The output is saved to:

```text
outputs/triage_budget_demo.csv
```

### 5.9 Customer-segment-based ticket routing

The final classification run uses the few-shot prompt with a larger token budget.

The pipeline reads:

```text
outputs/customer_segments.csv
```

The customer segment information is merged with ticket results using `customer_id`.

Routing follows these rules in order:

1. Tickets with status `skipped_empty`, `flagged_long`, `flagged_invalid_output` or `budget_exhausted` are sent to `human_review` with `NORMAL` priority.
2. Otherwise, tickets classified as `fraud` are sent to `security_team` with `HIGH` priority.
3. Otherwise, tickets belonging to a customer whose `is_premium` value is true are sent to `premium_desk` with `HIGH` priority.
4. All remaining successfully classified tickets are sent to `support_queue` with `NORMAL` priority.
5. If a customer does not have a row in the segment file, that customer is treated as not premium.

### 5.10 Final routing results

The final output contains 164 tickets.

| Route | Tickets |
|---|---:|
| `support_queue` | 102 |
| `security_team` | 34 |
| `human_review` | 17 |
| `premium_desk` | 11 |
| **Total** | **164** |

Priority distribution:

| Priority | Tickets |
|---|---:|
| HIGH | 45 |
| NORMAL | 119 |
| **Total** | **164** |

Final status distribution:

| Status | Tickets |
|---|---:|
| `classified_json` | 135 |
| `classified_keyword` | 12 |
| `flagged_invalid_output` | 9 |
| `skipped_empty` | 4 |
| `flagged_long` | 4 |
| **Total** | **164** |

### 5.11 Output validation

The final output is saved to:

```text
outputs/triage_results.csv
```

It contains exactly these columns:

```text
ticket_id, customer_id, status, category, segment_name, priority, route, tokens_used
```

Independent validation confirms:

- 164 rows.
- Eight required columns.
- Zero duplicate ticket IDs.
- Zero missing segment names.
- All 34 fraud tickets routed to `security_team`.
- All 17 tickets requiring human review routed to `human_review`.
- All human-review tickets have `NORMAL` priority.
- Blank categories are retained for tickets without a valid classification.

Successfully classified tickets receive rule-validated categories based on the JSON or keyword validation rules. Tickets with empty text, excessive length or invalid model output are not assigned guessed categories and are sent to human review.

### 5.12 Part C output files

| Output | Purpose |
|---|---|
| `outputs/triage_budget_demo.csv` | Zero-shot classification results under the token budget |
| `outputs/triage_results.csv` | Final few-shot classification and customer-based routing |

The implementation prints:

```text
ALL FINAL PART C CHECKS PASSED
```

## 6. Part D – Policy RAG Assistant and Refund Agent

### 6.1 Overview

Part D implements a policy question-answering assistant and a tool-using refund agent.

It uses the policy documents generated by the supplied data generator, the SQLite database created in Part A and the supplied offline `mock_llm.py` interface.

The implementation includes:

- Policy document loading and chunking.
- TF-IDF-based policy retrieval.
- Retrieval-grounded question answering.
- Retrieval evaluation.
- Refund tools.
- ReAct agent execution.
- Safety checks and human escalation.
- Token and iteration limits.
- Checkpoint and resume functionality.

### 6.2 Policy document preparation

Five policy text documents are loaded from `data/policies/`.

The documents cover:

- Refund policy.
- Delivery policy.
- Escalation policy.
- Payment policy.
- Privacy policy.

The text is divided into chunks using:

| Setting | Value |
|---|---:|
| Chunk size | 40 |
| Chunk overlap | 10 |
| Expected chunks | 15 |

The resulting 15 chunks are used as the retrieval knowledge base.

### 6.3 TF-IDF retrieval

The retrieval system uses scikit-learn's `TfidfVectorizer` and cosine similarity.

TF-IDF assigns weights to terms based on their frequency in a document and how uncommon they are across the collection. Cosine similarity compares the query vector with document-chunk vectors to identify relevant policy text.

The retrieval function accepts a question and returns the top three matching chunks.

This implementation provides lexical retrieval. It is useful for matching policy terminology but may not recognize every semantic equivalent or paraphrase.

### 6.4 Retrieval-grounded policy assistant

The `answer(question)` function:

1. Accepts a user question.
2. Retrieves the three most relevant policy chunks.
3. Builds the policy context.
4. Sends the system and user messages to `mock_llm.py`.
5. Returns the generated answer or the configured fallback when sufficient information is unavailable.

The assistant uses exactly two messages for its question-answering call.

The policy assistant is evaluated using the supplied `policy_eval.csv` dataset, containing 14 questions.

Normal retrieval results:

| Evaluation | Result |
|---|---:|
| Expected documents retrieved | 12/12 |
| Expected facts retrieved | 12/12 |
| Unanswerable questions using fallback | 2/2 |

Zero-overlap retrieval results:

| Evaluation | Result |
|---|---:|
| Expected documents retrieved | 12/12 |
| Expected facts retrieved | 10/12 |
| Unanswerable questions using fallback | 2/2 |

The two fact misses in the zero-overlap evaluation concern sentence-splitting behaviour involving the 45-minute and 48-hour policy facts.

### 6.5 Refund-agent tools

Five tools are implemented and registered:

| Tool | Purpose |
|---|---|
| `get_order` | Retrieve order information from the Part A database |
| `search_policy` | Retrieve relevant policy information |
| `calculate_refund` | Calculate a refund using the policy rules |
| `issue_refund` | Validate and record an eligible automatic refund |
| `escalate_to_human` | Validate and record a refund requiring human review |

The tool definitions are registered through `TOOLS_SPEC` and `TOOL_MAP`.

The refund policy used by the tools is:

- Only completed orders are eligible.
- Orders delivered in more than 45 minutes are eligible for a full refund of the order amount.
- Orders delivered in 45 minutes or less receive no refund.
- Refund amounts above INR 1,000 are escalated to a human rather than automatically issued.
- The simulated requests fall within the policy's seven-day request window.

The refund tools independently validate order status, delivery time, refund amount and applicable refund limits before recording an action.

For example, an attempted automatic refund of INR 1,999 is rejected because it exceeds the automatic refund limit. An unnecessary escalation of an otherwise eligible INR 128.25 refund is also rejected.

Refund actions are recorded in the refund ledger.

### 6.6 ReAct refund agent

The agent uses a ReAct-style workflow: it receives a request, selects a tool, observes the result and decides on the next action.

The `run_agent()` function supports:

- Maximum iteration limits.
- Token limits.
- Execution time limits.
- Tool-call tracking.
- Final status reporting.
- Checkpointing and resumption.

The configured agent limits include a maximum of six iterations, a token budget of 6,000 and a time limit of 10 seconds.

The supplied `mock_llm.py` provides deterministic offline behaviour for the agent demonstrations. It does not make live calls to a commercial language model.

### 6.7 Agent scenario evaluation

Seven supplied agent scenarios are executed.

| Scenario | Expected outcome | Result |
|---|---|---|
| S1 | Eligible automatic refund | REFUND |
| S2 | Eligible automatic refund | REFUND |
| S3 | Refund above automatic limit | ESCALATE |
| S4 | Ineligible refund | DENIED |
| S5 | Ineligible refund | DENIED |
| S6 | Order not found | NOT_FOUND |
| S7 | Maximum-iteration guardrail | FALLBACK_MAX_ITERATIONS |

All seven scenarios pass their expected status checks. The evaluation also checks the refund amount against the actual tool observations.

Additional guardrail demonstrations include:

- A low token limit produces `FALLBACK_TOKEN_LIMIT`.
- A zero-second execution limit produces `FALLBACK_TIMEOUT`.
- A repeated-tool scenario reaches the maximum-iteration fallback.

### 6.8 Checkpoint and resume

The agent saves its execution state after tool observations.

The checkpoint contains the information needed to continue the workflow, including:

- Run ID.
- Conversation messages.
- Token usage.
- Completed steps.
- Tool-call history.

The S1 demonstration simulates a crash after two tools have executed. The agent is resumed from the saved checkpoint.

The resumed execution completes the remaining steps and produces the expected INR 128.25 refund. The previously completed tools are not repeated.

### 6.9 ReAct versus plan-and-execute

The project compares ReAct with a plan-and-execute approach.

ReAct was selected because it can choose the next action using the latest tool observation. This is useful for refund processing because eligibility, order status and escalation decisions depend on the results returned by earlier tools.

The measured demonstrations include:

| Scenario | ReAct tool/model calls |
|---|---:|
| S1 | 5 |
| S5 | 3 |
| S6 | 2 |

The comparison considers execution behaviour, tool observations and the need to handle failures and policy restrictions.

### 6.10 Part D validation

The Part D demonstrations check:

- Policy chunk creation.
- Retrieval and fallback behaviour.
- Refund eligibility.
- Tool registration.
- Automatic refund restrictions.
- Human escalation restrictions.
- Agent scenario outcomes.
- Token, timeout and iteration guardrails.
- Checkpoint and resume behaviour.

The implementation uses local synthetic data and the deterministic offline mock interface, so no live LLM API key is required.

## 7. Project Outputs

Important generated outputs include:

| Output | Purpose |
|---|---|
| `data/instamart.db` | SQLite database containing customers, products and orders |
| `data/clean/customers.csv` | Cleaned customer data |
| `data/clean/products.csv` | Cleaned product data |
| `data/clean/orders.csv` | Cleaned order data |
| `outputs/customer_segments.csv` | Customer RFM values, segment assignments and Premium flag |
| `outputs/kmeans_comparison.csv` | K-means inertia and silhouette comparison |
| `outputs/lapse_dataset.csv` | Customer features and lapse labels |
| `outputs/lapse_model.joblib` | Saved lapse prediction model |
| `outputs/retention_list.csv` | Top Premium customers ranked by predicted lapse probability |
| `outputs/triage_budget_demo.csv` | Token-budget classification demonstration |
| `outputs/triage_results.csv` | Final support-ticket classification and routing |
| `outputs/agent_runs.jsonl` | Refund-agent execution records |
| `outputs/refund_ledger.jsonl` | Simulated refund and escalation records |
| `state/` | Agent checkpoint and resume state |

Some output and state files are generated or updated when the pipeline is run.

## 8. Limitations and Next Steps

- The datasets are synthetic and do not represent actual Swiggy customer or transaction records.
- Part A establishes the cleaned data foundation and analytical database for the later project components.
- Correlation analysis identifies statistical relationships but does not establish causal effects.
- The lapse prediction model is trained and evaluated using a historical synthetic dataset; its performance may differ on real customer behaviour.
- The Premium flag is derived from whole-window RFM information, including the September period used to define the lapse label. Therefore, the retention list is illustrative and is not a leakage-free evaluation.
- Part C uses the supplied deterministic offline `mock_llm.py` implementation. Its classification results demonstrate the pipeline's guardrails, retry handling, validation and routing logic rather than the performance of a production language model.
- Part D uses lexical TF-IDF retrieval. It may not identify all semantically equivalent policy questions.
- The refund agent is a simulated academic workflow. It does not issue real refunds or interact with Swiggy's production systems.
- The project uses synthetic scenarios and an offline mock model; production deployment would require secure integrations, monitoring, authentication and further testing.

Future improvements could include:

- Evaluating the lapse model on additional time periods.
- Testing the model with real, appropriately authorized customer data.
- Improving retrieval with semantic embeddings and more comprehensive policy evaluation.
- Integrating a production language model with suitable privacy and security controls.
- Connecting the agent to authorized production systems only after appropriate human approval and safety testing.

## 9. Project Structure

```text
Instamart-Customer-Intelligence-Copilot/
│
├── data/
│   ├── raw/
│   ├── clean/
│   ├── policies/
│   └── instamart.db
│
├── outputs/
│
├── sql/
│   └── queries.sql
│
├── src/
│   ├── audit_raw_data.py
│   ├── clean_data.py
│   ├── create_database.py
│   ├── validate_part_a.py
│   ├── run_sql_analysis.py
│   ├── build_customer_segments.py
│   ├── prepare_lapse_data.py
│   ├── train_lapse_models.py
│   ├── create_retention_list.py
│   ├── validate_part_b.py
│   ├── triage_tickets.py
│   ├── policy_rag.py
│   ├── refund_tools.py
│   └── refund_agent.py
│
├── state/
├── backups/
├── generate_data.py
├── mock_llm.py
├── run_project.py
├── requirements.txt
└── README.md
```

The project structure above lists the principal implementation files and directories. Generated files may be added within `data/`, `outputs/`, `state/` and `backups/` during execution.