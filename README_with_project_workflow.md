# Instamart Customer Intelligence & Support Copilot

## Overview

This project builds an integrated customer intelligence and support copilot for Swiggy Instamart using synthetic customer, product, order and support-ticket data.

The project is divided into four connected parts:

1. **Part A – Data Foundation:** Clean and validate raw data, store trusted data in SQLite, and perform SQL and exploratory analysis.
2. **Part B – Customer Intelligence:** Perform RFM analysis, customer segmentation and lapse prediction.
3. **Part C – Support Ticket Intelligence:** Protect personal information, classify support tickets and route them using customer segments.
4. **Part D – Policy Q&A and Refund Agent:** Retrieve answers from policy documents and implement a tool-using refund agent with validation and guardrails.

All monetary values are in INR. The supplied `mock_llm.py` provides deterministic offline LLM behaviour, so the project does not require a live GPT API or API key.

## Reproduction

Clone the repository:

```bash
git clone https://github.com/HARI-16-10-07/Instamart-Customer-Intelligence-Copilot.git
cd Instamart-Customer-Intelligence-Copilot
```

Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```
If any error raised then execute this cmd after that activate .venv

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the synthetic input data and run the integrated project:

```bash
python generate_data.py
python run_project.py
```

The project uses SQLite for its database. Generated datasets, model outputs, evaluation results and agent logs are stored in the `data/` and `outputs/` directories.

## Project Execution Workflow and Output Locations

Run the project from the repository root (the folder containing `generate_data.py`, `run_project.py`, `requirements.txt` and `src/`).

### 1. Open the project folder and activate the environment

In Windows PowerShell:

```powershell
cd "C:\Users\Hariharasudhan\Desktop\Instamart_Customer_Copilot"
.\venv\Scripts\Activate.ps1
```

If the virtual environment has not been created yet:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution for this session, run the following command and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Install the project dependencies (normally required only for the initial setup):

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Generate the synthetic input data

```powershell
python generate_data.py
```

This creates the synthetic input datasets used by the project. The project uses the `data/` directory for data files.

### 3. Execute the integrated project

```powershell
python run_project.py
```

This is the documented integrated execution command. It runs the project workflow. Allow the command to finish and check the terminal for execution messages or validation results.

### 4. Where to inspect the results

After execution, inspect the following confirmed files and folders in the repository:

| Project part | What to inspect | Location |
|---|---|---|
| Part A – Data Foundation | Cleaned data, SQLite database and validation/analysis outputs | `data/` and `outputs/` |
| Part B – Customer Intelligence | Segmentation and lapse-prediction results; the K-Means comparison output | `outputs/` (including `kmeans_comparison.csv`) |
| Part C – Support Ticket Intelligence | Ticket-level classification, processing status, customer segment, priority, route and token usage | `outputs/triage_results.csv` |
| Part D – Policy Q&A and Refund Agent | Agent execution logs and simulated refund ledger | `outputs/agent_runs.jsonl`, `outputs/agent_runs_backup.jsonl`, `outputs/refund_ledger.jsonl` |
| Part D – Checkpoint/resume | Saved agent checkpoint files | `state/` (scenario checkpoint files such as `S1_RESUME_DEMO.json` or `S*.json`) |

For Part C, the input ticket file is `data/raw/tickets.csv`. To test another complaint, add a row using the same columns and format as the existing records, then execute the project workflow again and inspect the corresponding ticket in `outputs/triage_results.csv`. This project processes tickets from the CSV workflow; it does not provide a live customer-facing text-entry screen.

### 5. Run individual modules only when you need to inspect a part separately

The following individual commands have been used for the corresponding module checks:

```powershell
# Part A – audit the raw data
python -m src.audit_raw_data

# Part A – clean the raw data
python -m src.clean_data

# Part A – create sqlite database
python -m src.create_database

# Part A – execute the sql queries
python -m src.run_sql_analysis

# Part A – Validating Part A
python -m src.validate_part_a
```
Where to inspect the results:
- data/raw/ – original generated datasets.
- data/clean/ – cleaned orders.csv and products.csv.
- data/instamart.db – SQLite database.
- sql/queries.sql – SQL queries.
- outputs/ – generated analysis or validation outputs, if produced by the scripts.

```powershell
# Part B - Calculates RFM values and creates customer segments
python -m src.build_customer_segments

# Part B - Prepares the customer dataset for lapse prediction
python -m src.prepare_lapse_data

# Part B - Trains and evaluates the lapse-prediction models
python -m src.train_lapse_models

# Part B - Generates the customer retention list from the customer intelligence results
python -m src.create_retention_list

# Part B - Validates Part B requirements
python -m src.validate_part_b
```
Where to inspect the results:
- data/instamart.db – customer and segmentation data.
- outputs/ – model evaluation results, prediction results and retention list, according to the filenames produced by the scripts.
- src/ – model training and preparation code.

```powershell
# Part C - Redacts sensitive information, classifies tickets, assigns priority and routes tickets using customer information from Part B
python -m src.triage_tickets
``` 
Where to inspect the results:
- data/raw/tickets.csv – input customer complaints.
- outputs/ – processed ticket results, including predicted categories, priorities and routing information.

```powershell
# Part D – 	Implements policy retrieval and policy question answering
python -m src.policy_rag

# Part D – run the refund agent and its scenarios
python -m src.refund_agent
```

Where to inspect the results:
- data/policies/ – policy documents used for retrieval.
- data/raw/agent_scenarios.csv – agent test scenarios.
- data/raw/policy_eval.csv – policy retrieval evaluation data.
- state/ – saved agent checkpoints, including the resume demonstration.
- outputs/ – generated evaluation and agent results, if saved there.
```

# Swiggy Customer Intelligence Project

## Table of Contents

- [How to Run](#how-to-run)
- [Part A – Data Foundation](#part-a--data-foundation)
- [Part B – Customer Intelligence](#part-b--customer-intelligence)
- [Part C – Support Ticket Intelligence](#part-c--support-ticket-intelligence)
- [Part D – Policy Q&A and Refund Agent](#part-d--policy-qa-and-refund-agent)
- [Limitations](#limitations)
- [Next Steps](#next-steps)

---

## How to Run

For the complete integrated workflow, use `python generate_data.py` followed by `python run_project.py` as shown below.

```bash
python generate_data.py
python run_project.py
```

---

## Part A – Data Foundation

### Raw data audit

The raw datasets were audited for missing values, duplicates, invalid values, inconsistent categories and data types.

| Dataset | Rows | Columns | Important audit findings |
|---|---:|---:|---|
| `customers.csv` | 1,200 | 5 | 61 missing ages; 30 missing genders |
| `products.csv` | 40 | 4 | No missing values |
| `orders.csv` | 13,084 | 9 | 53 missing order amounts; 2,541 missing delivery times |
| `tickets.csv` | 164 | 5 | No missing values |
| `policy_eval.csv` | 14 | 3 | 2 missing expected facts |
| `agent_scenarios.csv` | 7 | 5 | No missing values |

Additional raw-data quality checks identified:

- 119 exact duplicate order rows.
- 656 pending orders.
- 120 nonnumeric or missing order-amount values in the separate amount-quality check.
- 106 negative delivery times.
- 24 distinct raw city spellings.
- 10 distinct nonblank gender spellings.
- 6 customer ages outside the 10–100 range.

### Cleaning rules and changes

The following cleaning rules were applied to the raw datasets. Counts represent the values or rows affected by each operation.

| Dataset | Cleaning rule / checkpoint | Values/rows affected |
|---|---|---:|
| Customers | Rows retained | 1,200 |
| Customers | City values standardised | 476 |
| Customers | Gender values standardised | 950 |
| Customers | Blank ages identified | 61 |
| Customers | Invalid ages identified | 6 |
| Customers | Missing and invalid ages filled | 67 |
| Customers | Blank gender values identified | 30 |
| Products | Rows retained | 40 |
| Products | Product cleaning changes | 0 |
| Orders | Invalid or missing timestamps identified | 0 |
| Orders | Exact duplicate rows removed | 119 |
| Orders | Duplicate order IDs resolved | 656 |
| Orders | Order status values standardised | 0 |
| Orders | Pending orders removed separately | 0 |
| Orders | Missing order amounts filled | 112 |
| Orders | Negative delivery times corrected | 105 |
| Orders | Missing completed-order delivery times filled | 774 |

Customer city values were stripped and standardised, and gender values were normalised. Age values were converted to numeric values; ages outside the 10–100 range were treated as invalid, and missing or invalid ages were filled using the corresponding city median.

Order timestamps were parsed, exact duplicate rows were removed, and duplicate order IDs were resolved by retaining the latest record. Order statuses were standardised, and pending orders were handled by the cleaning process. Missing order amounts were imputed using product price, quantity and discount. Negative delivery times were treated as missing, and missing delivery times for completed orders were filled using product-category medians. Missing delivery times for cancelled orders were retained.

> **Count clarification:** The raw audit identified 656 pending orders, while the cleaning log reported zero pending orders removed separately. The 656 figure in the table refers to duplicate order IDs resolved, not pending orders removed.

### Database and validation

Cleaned data was loaded into a SQLite database.

**Final cleaned data:**

| Dataset | Final rows |
|---|---:|
| Customers | 1,200 |
| Products | 40 |
| Orders | 12,309 |

The cleaned orders contain 11,110 completed orders and 1,199 cancelled orders. Completed-order revenue is **INR 2,998,668.80**. There are no missing completed-order amounts or completed-order delivery times.

Part A validation: **18/18 checks passed.**

### SQL analysis and EDA

SQL analysis covered customer spending, city and category revenue, product prices, customers without completed orders, customer spending comparisons, top customers by city and cumulative daily revenue.

Key results:

- 30 high-spend customers were identified.
- 30 city-category groups were analysed.
- Bengaluru–Electronics was the highest-revenue city-category group at INR 233,909.45.
- 11 products were priced above the average catalogue price.
- 25 customers had no completed orders.
- 550 customers had completed spending above the average of INR 2,552.06.
- Total cumulative completed-order revenue was INR 2,998,668.80.

EDA on completed orders showed a mean order amount of INR 269.91 and a median of INR 135. The distribution was right-skewed, with skewness of 4.61. The IQR upper fence was INR 645.30, identifying 897 upper outliers. Order amount had a weak negative correlation with discount percentage (-0.095) and a weak positive correlation with quantity (0.087). These correlations do not establish causation.

---

## Part B – Customer Intelligence

### RFM analysis and customer segmentation

RFM features were calculated using:

- **Recency:** Days since the customer's most recent completed order.
- **Frequency:** Number of completed orders.
- **Monetary:** Total completed-order spending.

K-Means clustering was evaluated for cluster counts from 2 to 8 using inertia and silhouette score. Four clusters were selected.

PCA explained 85.2% of the variance in the first two components.

| Segment | Customers | Average recency | Average frequency | Average monetary value (INR) |
|---|---:|---:|---:|---:|
| Regular | 436 | 28.86 | 3.77 | 1,057.62 |
| Premium | 138 | 24.12 | 6.77 | 7,129.70 |
| Loyal | 419 | 8.77 | 19.40 | 3,410.02 |
| At Risk | 182 | 109.04 | 2.20 | 685.99 |

Segment-based actions include relevant engagement offers for Regular customers, exclusive rewards for Premium customers, loyalty rewards for Loyal customers and personalised win-back offers for At Risk customers.

### Lapse prediction

A lapse dataset was prepared using customer activity before the cutoff date of **2025-09-01**. The later period was used to determine the lapse target label. The dataset contained 1,156 customers: 443 lapsed and 713 not lapsed.

The data was split into 924 training records and 232 test records. Logistic Regression and Random Forest were evaluated against a baseline model.

**Data leakage prevention:**

- Only completed and cancelled orders before **2025-09-01** were used to calculate customer features.
- Completed orders from September 2025 were used only to determine the lapse target label. No order data from **2025-09-01 onwards** entered the model features.
- Customer activity features included recency, frequency, monetary value, average discount, cancellation rate, average delivery time and favourite category. Customer attributes included city, age, gender and tenure.
- Customer segment labels generated in the RFM segmentation task were not included as model features.
- `StandardScaler` and `OneHotEncoder` were fitted within the training-only cross-validation pipelines. Test rows were not used to fit preprocessing transformations; they were transformed using the fitted training preprocessing pipeline for evaluation.
- **No encoder, scaler or resampler was fitted or applied using test rows.** Preprocessing was fitted only within the training folds, and oversampling was restricted to the training split.
- Oversampling was performed only on the training data. The original test set remained untouched for final evaluation.

| Model | Test accuracy | Precision | Recall | F1-score |
|---|---:|---:|---:|---:|
| Baseline | 0.6164 | — | — | 0.0000 |
| Logistic Regression | 0.7284 | 0.6444 | 0.6517 | 0.6480 |
| Random Forest | 0.7371 | 0.6591 | 0.6517 | 0.6554 |
| Oversampled Logistic Regression | 0.7155 | 0.5891 | 0.8539 | 0.6972 |

Random Forest was selected based on its higher cross-validation F1-score among the standard evaluated models. The test set was reserved for final model evaluation. Oversampled Logistic Regression achieved a higher test F1-score and recall, with lower precision and accuracy.

The leading Random Forest feature importances were frequency (0.2796), monetary value (0.2712) and recency (0.1151).

A retention shortlist of 10 customers was generated. One customer in that shortlist was labelled as actually lapsed.

---

## Part C – Support Ticket Intelligence

The ticket pipeline processes support tickets using four categories:

- Billing
- Delivery
- Technical
- Fraud

It includes:

- Input-length checks and token-budget handling.
- Redaction of email addresses, phone numbers and order IDs before classification.
- Zero-shot and few-shot classification.
- JSON/category validation and keyword fallback.
- Retry handling for transient errors.
- Priority assignment and routing using the predicted category and customer segment.
- Human review for empty, over-length, invalid or otherwise unprocessable tickets.

### Privacy protection

Before classification, the pipeline applies pattern-based redaction to the following information:

| Information redacted | Count |
|---|---:|
| Email addresses | 55 |
| Phone numbers | 91 |
| Order IDs | 132 |
| **Total redactions** | **278** |

No remaining matches to the targeted email, phone-number and order-ID patterns were found after redaction.

This is targeted pattern-based redaction; it does not guarantee detection of every possible form of personal information.

### Classification results

There were 164 input tickets:

- 156 tickets were ready for processing.
- 4 tickets were skipped because they were empty.
- 4 tickets were flagged because they exceeded the input-length limit.

The zero-shot and few-shot classification results were:

| Measure | Zero-shot | Few-shot |
|---|---:|---:|
| Tokens used | 13,768 | 24,532 |
| Classified tickets | 147 | 147 |
| Accuracy | 85.71% | 100% |
| Tokens per classified ticket | 93.66 | 166.88 |

Accuracy was calculated on the 147 classified tickets, not all 164 input tickets.

### Few-shot prompt token cost

The few-shot prompt required more tokens than the zero-shot prompt.

| Cost comparison | Tokens |
|---|---:|
| Zero-shot total | 13,768 |
| Few-shot total | 24,532 |
| Additional tokens used by few-shot | 10,764 |
| Zero-shot tokens per classified ticket | 93.66 |
| Few-shot tokens per classified ticket | 166.88 |
| Additional tokens per classified ticket | 73.22 |

Few-shot classification used approximately **78.18% more tokens per classified ticket** than zero-shot classification.

The additional prompt cost was accompanied by an increase in measured classification accuracy from 85.71% to 100% on the classified tickets. These results are from the supplied deterministic mock LLM and synthetic evaluation dataset; they do not establish the same performance or cost for a live language model.

### Output validation and human review

The pipeline validates model responses before accepting them for routing. It uses JSON parsing and category checks, with a keyword fallback when JSON parsing fails.

The validation process is:

1. **JSON validation:** The response is parsed as JSON, and the predicted category is checked against the allowed categories: billing, delivery, technical and fraud.
2. **Keyword fallback:** If JSON parsing fails, the pipeline searches the response for category keywords. The fallback is accepted only when exactly one allowed category is identified.
3. **Invalid output:** If neither validation method produces an acceptable category, the ticket is marked invalid and sent for human review.
4. **Empty or over-length input:** Empty tickets and tickets exceeding the input-length limit are not classified and are sent for human review.

The final few-shot processing results were:

| Processing status | Tickets | Handling |
|---|---:|---|
| Valid JSON classification | 135 | Accepted after JSON and allowed-category validation |
| Keyword-fallback classification | 12 | Accepted after exactly one allowed category was identified |
| Invalid output | 9 | Sent for human review |
| Empty input | 4 | Sent for human review |
| Over-length input | 4 | Sent for human review |
| **Total** | **164** | |

Therefore:

- **147 tickets were classified:** 135 through JSON validation and 12 through keyword fallback.
- **17 tickets were sent for human review:** 9 invalid, 4 empty and 4 over-length.

> **Important validation distinction:** JSON and keyword checks validate the response structure and whether an allowed category can be identified. They do not independently verify whether the predicted category is semantically correct for the customer's actual issue. Classification accuracy is evaluated separately against the labelled evaluation data.

### Token-budget demonstration

A token-budget demonstration used a budget of 6,000 tokens.

| Measure | Result |
|---|---:|
| Token budget | 6,000 |
| Tokens used | 5,995 |
| Tickets classified | 64 |
| Tickets not processed because the budget was exhausted | 88 |
| Valid JSON outputs | 59 |
| Keyword-fallback outputs | 5 |
| Invalid outputs | 4 |
| Empty tickets | 4 |
| Over-length tickets | 4 |

The demonstration stopped processing when the token budget was exhausted. Tickets not processed because of the budget limit were not treated as successfully classified.

### Priority assignment and routing

The final few-shot output contains 164 ticket records.

Routing results:

| Route | Tickets |
|---|---:|
| `support_queue` | 102 |
| `security_team` | 34 |
| `premium_desk` | 11 |
| `human_review` | 17 |
| **Total** | **164** |

Priority results:

| Priority | Tickets |
|---|---:|
| `NORMAL` | 119 |
| `HIGH` | 45 |
| **Total** | **164** |

The routing process uses the predicted category and customer segment. Fraud tickets are routed to the security team with high priority. Premium customers with non-fraud issues are routed to the premium desk with high priority. Other valid tickets are routed to the support queue with normal priority. Empty, over-length and invalid tickets are routed to human review.

The final output includes ticket ID, customer ID, processing status, category, customer segment, priority, route and tokens used.

### Retry handling

The pipeline includes retry handling for transient errors. A total of 19 transient errors were recovered during execution.

---

## Part D – Policy Q&A and Refund Agent

### Policy knowledge base and retrieval

Five policy documents were used:

- Refund policy
- Delivery policy
- Escalation policy
- Payment policy
- Privacy policy

The documents were split into overlapping text chunks using a chunk size of 40 words and an overlap of 10 words. The resulting knowledge base contained 15 chunks.

TF-IDF vectorisation and cosine similarity were used to retrieve the top three relevant chunks for a query.

### Retrieval evaluation

| Evaluation | Expected documents matched | Expected facts matched | Unanswerable fallback |
|---|---:|---:|---:|
| With overlap | 12/12 | 12/12 | 2/2 |
| Without overlap | 12/12 | 10/12 | 2/2 |

The no-overlap evaluation missed two expected facts involving the 45-minute and 48-hour details, demonstrating the effect of chunk boundaries on retrieval.

### Refund tools and agent

The refund agent uses five tools:

| Tool | Purpose |
|---|---|
| `get_order` | Retrieves order details for verification. |
| `search_policy` | Retrieves relevant information from the policy knowledge base. |
| `calculate_refund` | Calculates the refund amount according to the applicable rules. |
| `issue_refund` | Executes the simulated refund after validation. |
| `escalate_to_human` | Escalates cases that require human approval. |

The refund rules implemented include:

- Only completed orders are eligible for a refund.
- A completed order delivered in more than 45 minutes qualifies for a full late-delivery refund.
- A completed order delivered in 45 minutes or less does not qualify for a late-delivery refund.
- Refunds above INR 1,000 require human approval.

The agent validates order status, delivery time, refund amount and tool arguments before issuing a refund. It also supports escalation, iteration limits, token limits, time limits and checkpoint/resume.

### Seven scenario results

| Scenario | Outcome | LLM calls | Tokens | Validation |
|---|---|---:|---:|---|
| S1 | `REFUND` – INR 128.25 | 5 | 1,807 | PASS |
| S2 | `REFUND` – INR 135.00 | 5 | 1,807 | PASS |
| S3 | `ESCALATE` | 5 | 1,797 | PASS |
| S4 | `DENIED` | 4 | 1,333 | PASS |
| S5 | `DENIED` | 3 | 883 | PASS |
| S6 | `NOT_FOUND` | 2 | 436 | PASS |
| S7 | `FALLBACK_MAX_ITERATIONS` | 6 | 4,092 | PASS |

All seven scenario records passed their recorded validation checks. The seven scenarios used 30 LLM calls and 12,155 tokens in total.

### Guardrail demonstrations

The agent was tested with token and time limits to verify that it stops execution safely when a configured limit is reached.

| Demonstration | Configured limit | Expected status | Actual result |
|---|---|---|---|
| Token-limit test | 200 tokens | `FALLBACK_TOKEN_LIMIT` | 221 tokens; 0 tool calls |
| Timeout test | 0 seconds | `FALLBACK_TIMEOUT` | 0 tool calls |

The token-limit demonstration returned `FALLBACK_TOKEN_LIMIT` after reaching 221 estimated tokens, without executing any tools. The timeout demonstration returned `FALLBACK_TIMEOUT` without executing any tools.

These tests demonstrate that the agent can return controlled fallback outcomes instead of continuing beyond the configured execution limits.

### Crash-and-resume demonstration

A checkpoint/resume test was performed using scenario S1.

The execution was deliberately interrupted after the first two tool actions. The agent saved its execution state and resumed from the checkpoint.

| Measure | Result |
|---|---|
| Scenario | S1 |
| Simulated interruption | After 2 tool actions |
| Resumption | Continued from the saved checkpoint |
| Repeated completed tool actions | None |
| Final outcome | `REFUND` |
| Final refund amount | INR 128.25 |
| Total LLM calls | 5 |
| Total tokens | 1,807 |

The crash-and-resume execution used the following verified tool sequence:

| Order | Tool | Execution stage |
|---:|---|---|
| 1 | `get_order` | Before simulated interruption |
| 2 | `search_policy` | Before simulated interruption |
| 3 | `calculate_refund` | After resumption |
| 4 | `issue_refund` | After resumption |

The execution log verified the complete sequence as `get_order` → `search_policy` → `calculate_refund` → `issue_refund`. The `escalate_to_human` tool is available to the agent but was not executed in this S1 demonstration. The checkpoint/resume mechanism preserved completed tool observations, and no completed tool action was repeated after resumption.

The resumed S1 execution completed successfully with a refund outcome of INR 128.25, using five LLM calls and 1,807 tokens.

### ReAct approach

The agent uses a ReAct-style approach: it reasons about the current request, selects a tool, observes the result and continues until it reaches an outcome or a guardrail.

Unlike a plan-and-execute approach, which prepares a plan before carrying out its steps, ReAct interleaves reasoning and actions. This project implements the ReAct-style tool loop.

---

## Limitations

- The datasets are synthetic and do not represent real Swiggy customer records.
- `mock_llm.py` provides deterministic offline responses; results are not generated by a live language model.
- Privacy redaction checks the targeted email, phone-number and order-ID patterns; it does not guarantee detection of every possible form of personal information.
- Classification accuracy is calculated on tickets that were classified, not on all 164 input records.
- Output validation checks response format and allowed-category identification; it does not independently establish semantic correctness.
- The retention shortlist contains 10 customers, of whom one was labelled as actually lapsed.
- The Premium flag in the retention list is a **post-hoc whole-window label** derived from RFM segmentation using the full order period. It was not used as a feature in the lapse prediction model. Because it uses information from the full order window, including information after the historical cutoff, it is not a leakage-free prospective prediction. Therefore, the retention list is **illustrative** and should not be interpreted as a fully leakage-free prospective retention recommendation.
- Refund actions are simulated in the local project; no real payments or customer-support actions are performed.

---

## Next Steps

- Evaluate the models and ticket classifier on additional representative datasets.
- Improve policy retrieval for facts that may be split across chunk boundaries.
- Extend privacy checks and test additional input variations.
- Evaluate the agent with additional scenarios and policy edge cases.