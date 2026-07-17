# Olist E-Commerce Marketplace Analytics
### MySQL · Power BI · Python · A/B Testing

---

## Project Overview
End-to-end analytics project on Brazil's largest e-commerce 
dataset (Olist) — covering seller performance scoring, delivery 
SLA analysis, product & category analytics, payment behavior, 
and A/B test statistical analysis.

---

## Problem Statement
An e-commerce marketplace with 100K+ orders had no framework 
to track seller quality, diagnose delivery failures, or validate 
product decisions with experiments.

---

## Tech Stack
| Layer | Tool |
|---|---|
| Data Storage | MySQL |
| Data Processing | Python (pandas, sqlalchemy, scipy) |
| Visualization | Power BI |
| Dataset | Olist Brazilian E-Commerce (9 CSVs, 100K+ orders) |

---

## Dataset
- Source: [Olist E-Commerce Dataset — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- 9 CSV files | 100K+ orders | 2016–2018

---

## Project Structure

├── sql/
│   └── olist_schema.sql
├── python/
│   ├── olist_preprocessing.py
│   └── ab_test_analysis.py
├── dashboard/
│   └── Ecommerce_Project_Report.pdf

---

## Dashboard Pages
| Page | Focus |
|---|---|
| 1 | Executive Overview — GMV, AOV, order status |
| 2 | Delivery & Logistics SLA — on-time %, late by state |
| 3 | Seller Performance — tier scoring, GMV by state |
| 4 | Product & Category Analytics — freight ratio, listing quality |
| 5 | Payment & Customer Behavior — installments, AOV, repeat rate |
| 6 | A/B Test Results — checkout experiment statistical analysis |

---

## Key Findings
- C-tier sellers have **39.27% late delivery rate** — 10x worse than A-tier (3.67%)
- SP state concentrates **70% of seller GMV** — marketplace concentration risk
- **96.8% one-time buyer rate** — critical retention gap
- Simplified checkout hurt cart additions (−9.91%) and purchases (−7.14%) — statistically and practically significant at 95% confidence — **Do Not Launch**

---

## A/B Test Summary
- Test: Simplified one-page checkout vs standard multi-step
- Sample: 47,277 users | Duration: 31 days | Alpha: 0.05
- Method: Two-proportion Z-test (scipy)

| Metric | Control | Treatment | Lift | P-value |
|---|---|---|---|---|
| Cart Add Rate | 23.05% | 20.77% | −9.91% | 0.0000 |
| Purchase Rate | 13.08% | 12.15% | −7.14% | 0.0022 |

---

## How to Run

### Prerequisites
```bash
pip install pandas sqlalchemy pymysql numpy scipy
```

### Steps
1. Set up MySQL database: `olist_ecommerce`
2. Run schema: `sql/olist_schema.sql` in MySQL Workbench
3. Download dataset from Kaggle link above
4. Update credentials in `python/olist_preprocessing.py`
5. Run preprocessing: `python olist_preprocessing.py`
6. Run A/B test: `python ab_test_analysis.py`
7. Connect Power BI to MySQL (localhost)

---

## Author
**Adeeb** | Senior Data Analyst
[LinkedIn](#) | [Portfolio](#)
