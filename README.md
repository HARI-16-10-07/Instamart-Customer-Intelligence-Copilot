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

## 4. Part B

**Status: Pending implementation.**

This section will document the RFM analysis, customer segmentation, lapse prediction models, model evaluation, retention list and saved model after Part B is implemented and verified.

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

