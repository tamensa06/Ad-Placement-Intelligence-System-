# Ad Placement Intelligence System
### *Where should a Nigerian fintech brand place its next ad?*

---

## The Problem

Every week, fintech brands like Opay, Cowrywise, and Piggyvest spend money on ads on TikTok, Instagram, X, and Facebook ,hoping to reach Nigerian Gen Z. But most of the time, they're guessing. Which platform? What time of day? What kind of content? Which audience?

This system answers those questions automatically. Every Monday, it pulls fresh data, runs it through a scoring engine, and delivers one clear recommendation:

> *"Best placement this week: TikTok · Short Video · Night (9pm–1am) · Age 18–24 → PIS Score: 87/100"*

No guessing. No manual analysis. Just a weekly answer visualised on a live dashboard.

---

## What I Built

A fully automated data pipeline and dashboard that:

1. **Pulls real Google Trends data** for Nigerian fintech keywords every Monday
2. **Generates realistic platform performance data** modelled on DataReportal Nigeria 2024 benchmarks
3. **Cleans and transforms** the data through a Bronze → Silver → Gold architecture
4. **Scores every ad placement combination** using a custom metric called the **Placement Intelligence Score (PIS)**
5. **Outputs a weekly recommendation** — the single best platform, time block, content type, and audience segment
6. **Visualises results** on an interactive Power BI dashboard
7. **Runs automatically** every Monday via Windows Task Scheduler — zero human intervention

---

## Dashboard

see in Ad Placement Dashboard

The dashboard surfaces the weekly recommendation at a glance, alongside supporting breakdowns:

- **Recommendation banner** — this week's winning placement combination
- **Metric cards** — best platform, time block, content type, and audience segment
- **PIS by platform / time block / content type** — comparative bar charts across all options
- **Weekly PIS trend** — tracks how the top score evolves week to week

Built in Power BI Desktop, connected directly to the Gold layer (`mart_recommendations` and `mart_pis_scores`) in PostgreSQL.

---

## The Signature Metric — Placement Intelligence Score (PIS)

The PIS Score is the heart of the system. It combines three performance dimensions into one number:

```
PIS = (Engagement Score × 0.35) + (Conversion Score × 0.45) + (Cost Efficiency Score × 0.20)
```

**Why these weights?**
- Conversion gets the highest weight (0.45) — sign-ups are what matter most for fintech
- Engagement gets medium weight (0.35) — awareness drives conversion
- Cost efficiency gets the lowest weight (0.20) — results matter more than cost savings

All three metrics are normalised to a 0–100 scale using min-max normalisation before scoring, so they can be compared fairly regardless of their original units.

---

## Architecture — Bronze → Silver → Gold

```
Google Trends API          Platform Data (Simulated)
      ↓                              ↓
   raw_google_trends      raw_platform_performance
         (Bronze Layer — raw, untouched)
                    ↓
        stg_google_trends    stg_platform_performance
         (Silver Layer — cleaned, standardised)
                    ↓
          mart_pis_scores    mart_recommendations
              (Gold Layer — analysis ready)
                    ↓
              Power BI Dashboard
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python (pytrends, pandas, numpy) | Data extraction and generation |
| SQLAlchemy + psycopg2 | Python → PostgreSQL connection |
| PostgreSQL 18 | Data warehouse |
| SQL (CTEs, Window Functions, Stored Procedures) | Data transformation |
| Power BI Desktop | Dashboard and visualisation |
| Windows Task Scheduler | Weekly automation |
| VS Code + Jupyter Notebook | Development environment |
| GitHub | Version control |

---

## Database Schema

### Bronze Layer
- `raw_google_trends` — hourly search interest per keyword per region
- `raw_platform_performance` — engagement, conversion, cost, and impressions per platform combination

### Silver Layer
- `stg_google_trends` — cleaned, deduplicated, standardised trends data
- `stg_platform_performance` — cleaned platform data with null handling and missing value flags

### Gold Layer
- `mart_pis_scores` — PIS score for every platform, content, time, and audience combination per week
- `mart_recommendations` — the single weekly winner with the highest PIS score

---

## Stored Procedures

| Procedure | Purpose |
|-----------|---------|
| `sp_load_stg_full()` | First-time full load of staging layer |
| `sp_load_stg_incremental()` | Weekly incremental load — never drops historical data |
| `sp_load_mart_full()` | First-time full load of mart layer |
| `sp_load_mart_incremental()` | Weekly incremental load of mart layer |

---

## Pipeline Flow

```
Windows Task Scheduler (Every Monday 7am)
            ↓
        pipeline.py
            ↓
1. pull_google_trends()         → pulls fresh data from Google Trends API
2. generate_platform_data()     → generates weekly platform simulation data
3. load_trends_to_postgres()    → loads to raw_google_trends
4. load_platform_to_postgres()  → loads to raw_platform_performance
5. run_stored_procedures()      → calls sp_load_stg_incremental()
                                   then sp_load_mart_incremental()
            ↓
      Power BI dashboard refreshes
```

---

## Project Structure

```
ad_placement_system/
│
├── pipeline.py                          ← master automation script
│
├── notebooks/
│   ├── google_trend_extraction.ipynb    ← Google Trends extraction
│   └── platform_performance_extraction.ipynb  ← platform data generation
│
├── sql/
│   ├── staging/
│   │   ├── full_load/
│   │   │   ├── stg_google_trends_full.sql
│   │   │   └── stg_platform_performance_full.sql
│   │   ├── incremental/
│   │   │   ├── stg_google_trends_incremental.sql
│   │   │   └── stg_platform_performance_incremental.sql
│   │   └── procedures/
│   │       ├── sp_load_stg_full.sql
│   │       └── sp_load_stg_incremental.sql
│   └── mart/
│       ├── mart_pis_scores.sql
│       ├── mart_recommendations.sql
│       └── procedures/
│           ├── sp_load_mart_full.sql
│           └── sp_load_mart_incremental.sql
│
├── dashboard/
│   └── ad_placement_dashboard.pbix
│
├── diagrams/
│   ├── erd.png
│   └── architecture.png
│
└── README.md
```

---

## Key SQL Concepts Used

- **CTEs (Common Table Expressions)** — chained multi-step transformations
- **Window Functions** — `MIN() OVER()`, `MAX() OVER()`, `RANK()`, `ROW_NUMBER()`
- **Min-Max Normalisation** — scaling metrics to 0–100 for fair comparison
- **EXCEPT** — incremental load logic to find only new rows
- **Stored Procedures** — encapsulated transformation logic callable from Python
- **Bronze → Silver → Gold** — medallion architecture for data quality layering

---

## Data Sources

**Google Trends (Real, Automated)**
Pulled via `pytrends` every Monday for the keywords: `opay`, `cowrywise`, `piggyvest`, `send money nigeria`, `mobile banking nigeria` — geography: Nigeria.

**Platform Performance Data (Simulated)**
Generated by a Python script modelled on DataReportal Nigeria 2024 benchmarks. A weekly seed ensures data changes every week but remains reproducible within the same week. Contains realistic 3–5% missing values per column.



## About


This project was built to demonstrate end-to-end data engineering skills: pipeline design, data modelling, SQL transformation, automation, and dashboard delivery. Applied to a real business problem in the Nigerian fintech space.

> *"I didn't just want to analyse data. I wanted to build something that makes a decision."*

---
