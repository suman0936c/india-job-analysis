# India Data Analyst Job Market Explorer

A live Streamlit application that turns a refreshed **Adzuna API snapshot** of India data-analyst postings into transparent skill, location, company, and salary-availability insights.

**Live app:** https://dojob-analysis.streamlit.app/  
**Business question:** Which job-market signals should an aspiring data analyst use to prioritise skills and job-search locations?

## What this project demonstrates

| Layer | Implementation |
|---|---|
| Live collection | Paginated Adzuna REST API requests with caching, timeout handling, and duplicate-job-ID removal |
| Text mining | Regex skill flags derived from job-description text |
| SQL | SQLite aggregation for top hiring companies, consistent with active filters |
| Product | Interactive Streamlit filters and CSV export |
| Data quality | Refresh timestamp, row/page counts, duplicate-removal note, salary-record rate, and explicit scope statement |

## Data source and scope

Data is fetched live from the [Adzuna Jobs API](https://developer.adzuna.com/). Each refresh is a **time-stamped snapshot of the postings returned by Adzuna** for the supplied search term and country. It is not a census of all India job openings and should not be treated as a permanent dataset.

The app reports the refresh timestamp, pages fetched, raw rows, unique job IDs, and salary-record share. This makes results auditable and prevents stale figures from being presented as current market facts.

## Analysis flow

1. Fetch up to 20 pages of live postings.
2. Normalize fields and remove duplicate job IDs.
3. Strip lightweight HTML from descriptions and apply an explicit regex skill dictionary.
4. Filter by listed location and required skills.
5. Calculate skill prevalence and location concentration.
6. Load the filtered population into SQLite and query top hiring companies.
7. Report salary transparency separately from salary values, because many postings omit compensation.

## Skill matching and limitations

Skill signals are pattern matches in description text, not a machine-learning model. The dictionary is inspectable and easy to revise, but it can miss indirect phrasing or create ambiguous matches, especially for the one-letter R pattern. Adzuna is an aggregator, and salary fields can be absent, predicted, or non-comparable. Treat results as directional decision support.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies with pip install -r requirements.txt.
3. Create the folder .streamlit, then copy the template as .streamlit\secrets.toml.
4. Add your Adzuna credentials and start with streamlit run app.py.

The app reads configured Streamlit secrets without rendering their values in the sidebar. The real secrets file is excluded from Git. Manual entry is only a local fallback and uses masked fields.

## Interview story

**Business question:** What should a data analyst focus on when targeting India roles?  
**Metrics:** skill mention share, location concentration, hiring-company counts, and salary-record availability.  
**Investigation:** live API collection, duplicate-ID QA, transparent description parsing, and filter-consistent SQL.  
**Decision:** use findings to prioritise job-search effort, while keeping claims scoped to the collection timestamp and Adzuna coverage.

## Resume bullets

- Built and deployed a live India data-analyst job-market explorer using paginated Adzuna REST API ingestion, regex text mining, SQLite, Altair, and Streamlit.
- Implemented duplicate-ID validation, timestamped refresh metadata, and filter-consistent SQL aggregation to make live API findings auditable.
- Designed interactive exploration of skill demand, job-location concentration, hiring companies, salary transparency, and downloadable filtered results.

## Repository structure

| File | Purpose |
|---|---|
| app.py | Streamlit application, API collection, skill extraction, SQLite query, and visuals |
| requirements.txt | Runtime dependencies, including Altair 6 for Python 3.14 compatibility |
| secrets.toml.example | Safe template for API credentials |
| .gitignore | Prevents secrets, environments, caches, and exports from being committed |
