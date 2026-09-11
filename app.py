"""
India Data Analyst Job Market Dashboard

Started this as a one-off notebook to answer a question I had: what do DA job
postings in India actually ask for, and is that different from the generic
"learn SQL and Python" advice you see everywhere. Turned it into a live app
so it doesn't go stale after one pull.

Pulls from the Adzuna API, does some regex skill-matching on job descriptions,
and throws it in a little in-memory SQLite db so I could actually practice
writing SQL instead of just doing everything in Pandas.
"""

import re
import sqlite3
import time

import pandas as pd
import requests
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="India Data Analyst Job Market",
    page_icon="📊",
    layout="wide",
)

# these are the skills I'm checking for -- built this list by first running a
# word-frequency count on ~1000 descriptions and seeing what actually showed up,
# rather than just guessing. still probably missing some.

SKILLS = {
    'SQL': r'\bsql\b',
    'Python': r'\bpython\b',
    'Excel': r'\bexcel\b',
    'Power BI': r'\bpower\s?bi\b',
    'Tableau': r'\btableau\b',
    'R': r'\br\b(?!\.a)',
    'SAS': r'\bsas\b',
    'SPSS': r'\bspss\b',
    'Machine Learning': r'\bmachine learning\b',
    'AWS': r'\baws\b',
    'Azure': r'\bazure\b',
    'ETL': r'\betl\b',
    'Big Data': r'\bbig data\b',
    'Data Warehousing': r'\bdata warehous',
    'Dashboards': r'\bdashboard',
    'Reporting': r'\breporting\b',
    'Statistics': r'\bstatistic',
    'Alteryx': r'\balteryx\b',
    'Qlik': r'\bqlik',
    'Google Analytics': r'\bgoogle analytics\b',
}

RESULTS_PER_PAGE = 50


# ---------------------------------------------------------------------------
# Data pulling (cached so we don't hit the API on every interaction)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_jobs(app_id: str, app_key: str, what: str, country: str, num_pages: int) -> pd.DataFrame:
    """Grab job postings from Adzuna page by page and flatten into a DataFrame.
    Cached for an hour so clicking around the filters doesn't spam the API."""
    all_jobs = []

    for page in range(1, num_pages + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": RESULTS_PER_PAGE,
            "what": what,
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            break  # bad key or rate limited, just stop instead of crashing

        results = response.json().get("results", [])
        if not results:
            break  # ran out of pages

        all_jobs.extend(results)
        time.sleep(0.3)  # don't hammer their API

    clean_jobs = []
    for job in all_jobs:
        clean_jobs.append({
            "id": job.get("id"),
            "title": job.get("title"),
            "description": job.get("description") or "",
            "company": job.get("company", {}).get("display_name"),
            "location": job.get("location", {}).get("display_name"),
            "category": job.get("category", {}).get("label"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "salary_is_predicted": job.get("salary_is_predicted"),
            "created": job.get("created"),
            "redirect_url": job.get("redirect_url"),
        })

    df = pd.DataFrame(clean_jobs)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="id")

    for name, pattern in SKILLS.items():
        df[name] = df["description"].str.contains(pattern, flags=re.IGNORECASE, regex=True, na=False)

    return df


def load_to_sqlite(df: pd.DataFrame) -> sqlite3.Connection:
    # in-memory db, wiped every time -- just wanted a real SQL layer to query against
    conn = sqlite3.connect(":memory:")
    df.to_sql("jobs", conn, if_exists="replace", index=False)
    return conn


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("⚙️ Controls")

# Keys come from Streamlit secrets only -- never shown or editable in the UI.
# Keeps this safe to share as a public link without exposing my API credentials.
app_id = st.secrets.get("ADZUNA_APP_ID", "") if hasattr(st, "secrets") else ""
app_key = st.secrets.get("ADZUNA_APP_KEY", "") if hasattr(st, "secrets") else ""

search_term = st.sidebar.text_input("Job search term", value="data analyst")
num_pages = st.sidebar.slider("Pages to fetch (50 jobs/page)", min_value=2, max_value=20, value=10)

refresh = st.sidebar.button("🔄 Fetch / Refresh live data", type="primary")

st.sidebar.caption(
    "Results are cached for an hour so I'm not re-hitting the API on every click. "
    "Hit refresh if you want the latest postings."
)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

st.title("📊 India Data Analyst Job Market")
st.caption(
    "Pulled live from the [Adzuna API](https://developer.adzuna.com/). "
    "I built this because I wanted real numbers instead of another generic "
    "'top skills for data analysts' blog post. Skill detection is just regex "
    "matching on the job description text, so treat the counts as roughly right, not exact."
)

if not app_id or not app_key:
    st.error(
        "Adzuna API keys aren't configured for this app. "
        "(If this is your deployment: add ADZUNA_APP_ID and ADZUNA_APP_KEY "
        "under Settings → Secrets in Streamlit Cloud, then reboot the app.)"
    )
    st.stop()

if refresh or "jobs_df" not in st.session_state:
    with st.spinner(f"Pulling live postings from Adzuna ({num_pages * RESULTS_PER_PAGE} max)..."):
        df = fetch_jobs(app_id, app_key, search_term, "in", num_pages)
        st.session_state["jobs_df"] = df
        st.session_state["fetched_at"] = pd.Timestamp.now()

df = st.session_state.get("jobs_df", pd.DataFrame())

if df.empty:
    st.error("No data returned. Check your API credentials and try again.")
    st.stop()

st.caption(f"Last fetched: {st.session_state['fetched_at'].strftime('%Y-%m-%d %H:%M:%S')} · {len(df)} unique postings loaded")

conn = load_to_sqlite(df)

# --- Filters ---------------------------------------------------------------

col_f1, col_f2 = st.columns(2)
with col_f1:
    all_cities = sorted(df.loc[df["location"] != search_term.title(), "location"].dropna().unique().tolist())
    selected_cities = st.multiselect("Filter by city", options=all_cities)
with col_f2:
    selected_skills = st.multiselect("Filter: must mention skill", options=list(SKILLS.keys()))

filtered = df.copy()
if selected_cities:
    filtered = filtered[filtered["location"].isin(selected_cities)]
for skill in selected_skills:
    filtered = filtered[filtered[skill] == True]

st.markdown(f"**{len(filtered)} postings** match current filters (of {len(df)} total).")

# --- KPI row -----------------------------------------------------------

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total postings", len(filtered))
k2.metric("Unique companies", filtered["company"].nunique())
k3.metric("Unique cities", filtered["location"].nunique())
salary_disclosed = filtered["salary_min"].notna().sum()
k4.metric("Salary disclosed", f"{salary_disclosed} ({salary_disclosed/len(filtered)*100:.0f}%)" if len(filtered) else "0")

st.divider()

# --- Skill demand chart -----------------------------------------------------

st.subheader("Most In-Demand Skills")
skill_counts = pd.Series({s: int(filtered[s].sum()) for s in SKILLS}).sort_values(ascending=False)
skill_pct = (skill_counts / max(len(filtered), 1) * 100).reset_index()
skill_pct.columns = ["skill", "pct"]

chart = alt.Chart(skill_pct).mark_bar(color="#2E5A87").encode(
    x=alt.X("pct:Q", title="% of postings mentioning skill"),
    y=alt.Y("skill:N", sort="-x", title=None),
    tooltip=["skill", alt.Tooltip("pct:Q", format=".1f")],
).properties(height=450)
st.altair_chart(chart, use_container_width=True)

# --- City concentration chart ----------------------------------------------

st.subheader("Where Are the Jobs?")
city_counts = filtered[filtered["location"] != search_term.title()]["location"].value_counts().head(12).reset_index()
city_counts.columns = ["city", "postings"]

city_chart = alt.Chart(city_counts).mark_bar(color="#C0392B").encode(
    x=alt.X("postings:Q"),
    y=alt.Y("city:N", sort="-x", title=None),
    tooltip=["city", "postings"],
).properties(height=350)
st.altair_chart(city_chart, use_container_width=True)

# --- SQL-powered top companies ----------------------------------------------

st.subheader("Top Hiring Companies (via SQL query)")
query = """
    SELECT company, COUNT(*) as num_postings
    FROM jobs
    WHERE company IS NOT NULL
    GROUP BY company
    ORDER BY num_postings DESC
    LIMIT 10
"""
top_companies = pd.read_sql(query, conn)
st.dataframe(top_companies, use_container_width=True, hide_index=True)

# --- Raw data / export -------------------------------------------------

with st.expander("View raw filtered data"):
    st.dataframe(
        filtered[["title", "company", "location", "created", "salary_min", "salary_max", "redirect_url"]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download filtered data as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="india_data_analyst_jobs.csv",
        mime="text/csv",
    )

st.caption(
    "Data via the Adzuna API (they aggregate from company career pages and job boards, "
    "so this isn't the entire Indian job market, just what Adzuna has indexed). "
    "Salary numbers are only shown when an employer actually disclosed them -- "
    "most Indian postings in this dataset didn't."
)
