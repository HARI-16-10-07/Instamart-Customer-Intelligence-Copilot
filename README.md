# Customer Intelligence & Support Copilot

## 1. Overview

This project develops a Customer Intelligence and Support Copilot for Swiggy Instamart using synthetic customer, product, order and support-ticket data.

The project is organized into four connected parts:

- **Part A – Data Foundation:** Audit, clean and standardize raw data, store trusted data in SQLite, and perform SQL and Pandas analysis.
- **Part B – Customer Segments and Lapse Prediction:** Apply RFM analysis, customer segmentation and machine-learning-based lapse prediction.
- **Part C – Support Ticket Triage with Guardrails:** Process support tickets, protect personal information, classify issues and route tickets.
- **Part D – Policy RAG Assistant and Refund Agent:** Retrieve company policy information and implement a tool-using refund agent with safety checks.

All monetary values in this project are represented in Indian Rupees (INR). The data is synthetic and is intended for academic demonstration.

---

## 2. Reproduce

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

```bash
python -m pip install -r requirements.txt
```

### 2.5 Generate the synthetic data

```bash
python generate_data.py
```

This generates the raw CSV files and policy documents used by the project.

### 2.6 Part A – Data Foundation

Run the following commands in order:

```powershell
python src/audit_raw_data.py
python src/clean_data.py
python src/create_database.py
python src/validate_part_a.py
python src/run_sql_analysis.py
```

### 2.7 Part B – Customer Segments and Lapse Prediction

Run the Part B scripts in the following order:

```powershell
python src/build_customer_segments.py
python src/prepare_lapse_data.py
python src/train_lapse_models.py
python src/create_retention_list.py
python src/validate_part_b.py
```

These scripts generate the customer segmentation, lapse prediction model, retention list and validation results.

### 2.8 Part C – Support Ticket Triage

Run:

```powershell
python src/triage_tickets.py
```

This runs the zero-shot and few-shot comparisons, the token-budget demonstration and the final few-shot ticket-routing pipeline.

The script generates:

```text
outputs/triage_budget_demo.csv
outputs/triage_results.csv
```

### 2.9 Validation

The Part A and Part B validation scripts check the respective outputs against their expected checkpoints.

Part C performs assertions for its final results and prints:

```text
ALL FINAL PART C CHECKS PASSED
```

---

## 3. Part A – Data Foundation: Clean, Store and Query

### 3.1 Overview

Part A converts the generated raw data into a trusted analytical dataset. It includes raw data auditing, customer and order cleaning, SQLite database creation, SQL analysis and exploratory analysis using Pandas.

### 3.2 Raw data audit

Six raw CSV files are generated:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `tickets.csv`
- `agent_scenarios.csv`
- `policy_eval.csv`

The audit script examines the shape, data types, missing-value counts and missing-value percentages of the raw tables.

The ticket data is read with `keep_default_na=False` to preserve empty ticket text for later processing.

Important raw-data audit results:

| Audit item | Result |
|---|---:|
| Raw order rows | 13,084 |
| Exact duplicate order rows | 119 |
| Pending order rows | 656 |
| Distinct order IDs | 12,309 |
| Non-numeric order amounts | 120 |
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

Ages outside the valid range of 10–100 are treated as missing. Missing ages are filled using the median age of the corresponding city, calculated using `groupby` and `transform`. Signup dates are converted to datetime values.

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

The product dataset retains all 40 rows. No product cleaning changes were required.

### 3.5 Order data cleaning

The order-cleaning process applies the following operations:

1. Convert `order_ts` into datetime values.
2. Remove 119 exact duplicate rows.
3. Resolve duplicate order IDs by retaining the record with the latest `order_ts`.
4. Standardize order statuses by removing surrounding whitespace and converting values to lowercase. No status values required standardization.
5. Remove pending orders remaining after duplicate-ID resolution. No additional pending rows remained to be removed.
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

Completed order revenue is **INR 29,98,668.80**.

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

The analysis also uses `pivot_table` with margins, named aggregation, descriptive statistics, outlier detection and correlation analysis.

- The Q2 pivot-table grand total matches INR 29,98,668.80.
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

---

## 4. Part B – Customer Segments and Lapse Prediction

### 4.1 Overview

Part B uses the cleaned customer and order datasets from Part A to identify meaningful customer groups and predict which customers are likely to stop ordering.

The two main components are:

- RFM-based customer segmentation using K-means clustering.
- Lapse prediction using Logistic Regression and Random Forest models.

The resulting customer segment file is also used by Part C for support-ticket routing.

### 4.2 RFM analysis

RFM analysis is performed using completed orders only.

The snapshot date is `2025-10-01 00:00:00`.

The three RFM measures are:

- **Recency:** Number of whole days since the customer's most recent completed order.
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

K-means is evaluated for K values from 2 to 8 using:

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

K=4 was selected because it achieved the highest silhouette score (0.5255) among the tested values of K from 2 to 8. The silhouette score measures how well-separated the clusters are. Although inertia decreases as K increases, K=4 provides the strongest clustering separation among the tested configurations.

The final K-Means model uses:

```python
KMeans(
    n_clusters=4,
    n_init=10,
    random_state=42
)
```

Cluster IDs are arbitrary labels and do not represent customer value or ranking. The clusters are assigned descriptive names based on their RFM profiles.

### 4.4 PCA explained variance

Principal Component Analysis (PCA) was performed using exactly two components on the standardized RFM features: recency, frequency and monetary.

| Component | Explained Variance Ratio |
|---|---:|
| PC1 | 0.634 |
| PC2 | 0.218 |
| **Combined** | **0.852** |

The first principal component explains 63.4% of the variance, while the second explains 21.8%. Together, the two components retain **85.2% of the total variance** in the standardized RFM data.

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

A customer is labelled as lapsed if they have no completed order from `2025-09-01` through `2025-09-30`.

The model features are constructed using only information available before the cutoff:

- Recency
- Frequency
- Monetary
- Average discount percentage
- Cancellation rate
- Average delivery time
- Favourite product category
- City
- Age
- Gender
- Customer tenure

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

The nominal variables include city, gender and favourite product category.

The numeric features are standardized using a fitted scaler.

The encoder and scaler are fitted only on the training rows. They are then applied to the test rows without refitting.

No encoder, scaler or resampler saw test rows during fitting. No data from `2025-09-01` onwards entered the model features, and the Part B segment labels were not used as features.

The feature data is checked for missing values before model training.

The learned training-set frequency mean can differ from the full-cohort frequency mean because the scaler is fitted on the training subset rather than the complete cohort.

### 4.8 Model training and hyperparameter tuning

Two classification algorithms are evaluated.

#### Logistic Regression

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

#### Random Forest

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

Its best cross-validation F1 is approximately 0.6811.

**Final model selection:** The final model was selected by comparing the cross-validation F1 scores of the Logistic Regression and Random Forest models. Random Forest was selected because it achieved the higher cross-validation F1 score (approximately 0.6811 compared with approximately 0.6506 for Logistic Regression). The test set was not used for model selection.

### 4.9 Model evaluation

The tuned models are evaluated on the untouched test set.

The positive class is `lapsed`.

#### Logistic Regression

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

#### Random Forest

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

The cost of missing a lapsing customer is potentially losing future purchases and retention opportunities. However, wrongly targeting a loyal customer can waste campaign resources and incentives. The selected model must therefore balance precision and recall rather than relying only on accuracy.

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

Recall increases from approximately 0.6517 to 0.8539. This means the model identifies a larger proportion of customers who are actually lapsing, which is useful for retention campaigns. However, precision decreases, so the retention team may need to contact more customers who would not have lapsed.

The oversampled model demonstrates the trade-off between identifying more at-risk customers and increasing false-positive targeting.

### 4.11 Feature interpretation

The Random Forest model's five leading features are:

| Feature | Importance |
|---|---:|
| Frequency | 0.2796 |
| Monetary | 0.2712 |
| Recency | 0.1151 |
| Average delivery time | 0.0613 |
| Cancellation rate | 0.0523 |

Frequency and monetary value are the most influential features in the fitted Random Forest model.

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

The model is reloaded using `joblib.load`, and its predictions are compared with the original test predictions.

The reloaded model reproduces the original test predictions exactly.

The retention list is generated using the saved model in `outputs/lapse_model.joblib`.

It is created by:

1. Recreating the same stratified 80:20 train-test split using `random_state=42`.
2. Identifying Premium customers using the `is_premium` flag from `customer_segments.csv`.
3. Selecting Premium customers belonging to the test set.
4. Calculating predicted lapse probabilities using the saved model.
5. Ranking the selected customers by predicted lapse probability in descending order.
6. Saving the top 10 customers.

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

The script `src/validate_part_b.py` checks the generated files, segment assignments, Premium flag, lapse dataset, saved model, probability predictions and retention list.

Successful execution prints:

```text
ALL PART B CHECKPOINTS PASSED
```

---

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

The following regular expressions and placeholders are applied in the specified order:

| Personal information | Regular expression | Replacement | Substitutions |
|---|---|---|---:|
| Email | `[\w.+-]+@[\w-]+\.[\w.]+` | `[EMAIL]` | 55 |
| Phone | `\b[6-9]\d{9}\b` | `[PHONE]` | 91 |
| Order ID | `ORD-\d{6}` | `[ORDER_ID]` | 132 |
| **Total** | | | **278** |

The redacted ticket texts are checked again using all three patterns.

The verification finds zero remaining email addresses, phone numbers or order IDs.

An assertion in the code checks that no personal information remains before a model call. The user message content sent to the model consists of exactly the redacted ticket text, without any additional text.

### 5.4 Zero-shot and few-shot prompts

Two system prompts are implemented.

#### Zero-shot prompt

The zero-shot prompt instructs the model to classify tickets into exactly four allowed categories:

- `billing`
- `delivery`
- `technical`
- `fraud`

It requires a JSON-only response in the following structure:

```json
{"category": "...", "reason": "..."}
```

It does not contain the `EXAMPLES:` section.

#### Few-shot prompt

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

Each retry prints a log containing:

- Ticket ID
- Retry number
- Wait duration

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

Validation results for a full run:

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

The few-shot prompt uses 10,764 additional tokens compared with the zero-shot prompt. This is an increase of approximately 73.22 tokens per classified ticket, or 78.18%.

The extra few-shot tokens are worthwhile when classification accuracy is especially important for support operations. Zero-shot classification achieves 85.71% accuracy, while few-shot classification achieves 100% on the same 147 classified tickets. In particular, the zero-shot errors include fraud and technical tickets incorrectly classified as billing, which could cause inappropriate routing. For a support workflow where incorrect fraud routing can have significant consequences, the higher few-shot token cost is justified.

### 5.8 Token-budget demonstration

A token budget is checked before every model call.

If the running token total is already greater than or equal to the configured budget, no further model call is made and the ticket receives `budget_exhausted`.

The zero-shot budget demonstration uses:

```python
TOKEN_BUDGET = 6000
```

Results:

| Metric | Result |
|---|---:|
| Configured budget | 6,000 |
| Actual tokens consumed | 6,008 |
| Tickets marked `budget_exhausted` | 88 |

The small difference between the configured budget and actual usage occurs because the budget is checked before a call, not during a call. The final response can therefore take the total slightly above the configured limit.

The output is saved to:

```text
outputs/triage_budget_demo.csv
```

### 5.9 Customer-segment-based ticket routing

The final classification run uses the few-shot prompt with:

```python
TOKEN_BUDGET = 100000
```

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

---

## 6. Part D – Policy RAG Assistant and Refund Agent

**Status: Pending implementation.**

This section will document the implementation and evaluation of the Policy RAG Assistant and Refund Agent after the Part D tasks have been completed and verified.

The planned areas to be documented include:

- Policy-document loading and preparation.
- Text chunking and retrieval.
- TF-IDF-based policy retrieval.
- Retrieval-grounded question answering.
- Retrieval evaluation.
- Refund-agent tools and execution.
- ReAct agent workflow.
- Safety checks and refund limits.
- Human escalation and resumable agent runs.
- ReAct and plan-and-execute comparison.

No Part D results or implementation claims are reported until they have been implemented and tested.

---

## 7. Limitations and Next Steps

- The datasets are synthetic and do not represent actual Swiggy customer or transaction records.
- Part A establishes the cleaned data foundation and analytical database for the later project components.
- Correlation analysis identifies statistical relationships but does not establish causal effects.
- The lapse prediction model is trained and evaluated using a historical synthetic dataset; its performance may differ on real customer behaviour.
- The Premium flag is derived from whole-window RFM information, including the September period used to define the lapse label. Therefore, the retention list is illustrative and is not a leakage-free evaluation.
- Part C uses the supplied deterministic offline `mock_llm.py` implementation. Its classification results demonstrate the pipeline's guardrails, retry handling, validation and routing logic rather than the performance of a production language model.
- Part D remains to be implemented and evaluated.

The next development step is to complete Part D, integrate its policy retrieval and refund-agent functionality with the existing data foundation, and validate the complete four-part project.