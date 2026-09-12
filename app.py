"""India Data Analyst Job Market Explorer."""
from __future__ import annotations
import html
import re
import sqlite3
import time
from datetime import datetime, timezone
import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="India Data Analyst Job Market", page_icon="📊", layout="wide")
SKILLS = {"SQL":r"\bsql\b","Python":r"\bpython\b","Excel":r"\bexcel\b","Power BI":r"\bpower\s?bi\b","Tableau":r"\btableau\b","R":r"\br\b(?!\.a)","SAS":r"\bsas\b","SPSS":r"\bspss\b","Machine Learning":r"\bmachine learning\b","AWS":r"\baws\b","Azure":r"\bazure\b","ETL":r"\betl\b","Big Data":r"\bbig data\b","Data Warehousing":r"\bdata warehous","Dashboards":r"\bdashboard","Reporting":r"\breporting\b","Statistics":r"\bstatistic","Alteryx":r"\balteryx\b","Qlik":r"\bqlik","Google Analytics":r"\bgoogle analytics\b"}
RESULTS_PER_PAGE = 50
BASE_COLUMNS = ["id","title","description","company","location","category","salary_min","salary_max","salary_is_predicted","created","redirect_url"]

def secret_value(key: str) -> str:
    try:
        return str(st.secrets.get(key, ""))
    except (FileNotFoundError, KeyError):
        return ""

def clean_description(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(value or ""))

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_jobs(app_id: str, app_key: str, what: str, country: str, num_pages: int) -> tuple[pd.DataFrame, str]:
    """Fetch Adzuna pages, deduplicate job IDs, and return an audit note."""
    jobs, fetched_pages = [], 0
    try:
        with requests.Session() as session:
            for page in range(1, num_pages + 1):
                response = session.get(f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}", params={"app_id":app_id,"app_key":app_key,"results_per_page":RESULTS_PER_PAGE,"what":what}, timeout=20)
                response.raise_for_status()
                results = response.json().get("results", [])
                if not results:
                    break
                jobs.extend(results); fetched_pages += 1; time.sleep(0.25)
    except requests.RequestException as exc:
        return pd.DataFrame(columns=BASE_COLUMNS + list(SKILLS)), f"API request failed after {fetched_pages} page(s): {exc}"
    records = [{"id":j.get("id"),"title":j.get("title"),"description":clean_description(j.get("description","")),"company":j.get("company",{}).get("display_name"),"location":j.get("location",{}).get("display_name"),"category":j.get("category",{}).get("label"),"salary_min":j.get("salary_min"),"salary_max":j.get("salary_max"),"salary_is_predicted":j.get("salary_is_predicted"),"created":j.get("created"),"redirect_url":j.get("redirect_url")} for j in jobs]
    df = pd.DataFrame(records, columns=BASE_COLUMNS)
    if df.empty:
        return df, f"No postings returned across {fetched_pages} page(s)."
    raw_rows = len(df); df = df.drop_duplicates(subset="id").copy()
    for skill, pattern in SKILLS.items():
        df[skill] = df["description"].str.contains(pattern, flags=re.IGNORECASE, regex=True, na=False)
    return df, f"Fetched {raw_rows:,} rows across {fetched_pages} page(s); removed {raw_rows-len(df):,} duplicate job IDs."

def sqlite_query(df: pd.DataFrame, query: str) -> pd.DataFrame:
    with sqlite3.connect(":memory:") as conn:
        df.to_sql("jobs", conn, if_exists="replace", index=False)
        return pd.read_sql_query(query, conn)

st.sidebar.header("Controls")
stored_app_id = secret_value("ADZUNA_APP_ID")
stored_app_key = secret_value("ADZUNA_APP_KEY")
app_id, app_key = stored_app_id, stored_app_key
if stored_app_id and stored_app_key:
    st.sidebar.success("API credentials configured securely.")
else:
    with st.sidebar.expander("Set up API credentials", expanded=False):
        st.caption("For local use, prefer .streamlit/secrets.toml. Values entered here remain masked.")
        app_id = st.text_input("Adzuna App ID", type="password", key="manual_app_id")
        app_key = st.text_input("Adzuna App Key", type="password", key="manual_app_key")
search_term = st.sidebar.text_input("Job search term", value="data analyst")
num_pages = st.sidebar.slider("Pages to fetch", 2, 20, 10, help="Up to 50 postings per page.")
refresh = st.sidebar.button("Fetch live data", type="primary")
st.sidebar.caption("Results are cached for one hour. Select Fetch live data to refresh the API snapshot.")

st.title("India Data Analyst Job Market")
st.caption("Live Adzuna API snapshot • regex skill extraction • SQLite aggregation • Streamlit")
st.info("Scope: this app analyses the Adzuna postings collected for this refresh. It is not a complete representation of the India job market.")
if not app_id or not app_key:
    st.info("Add Adzuna credentials in the sidebar or Streamlit secrets, then select Fetch live data."); st.stop()
if refresh or "jobs_df" not in st.session_state:
    with st.spinner("Fetching and validating live job postings..."):
        data, note = fetch_jobs(app_id, app_key, search_term, "in", num_pages)
    st.session_state["jobs_df"], st.session_state["collection_note"], st.session_state["fetched_at_utc"] = data, note, datetime.now(timezone.utc)
df = st.session_state.get("jobs_df", pd.DataFrame(columns=BASE_COLUMNS))
if df.empty:
    st.error(st.session_state.get("collection_note", "No data returned. Check credentials and try again.")); st.stop()
st.caption(f"Last refreshed: {st.session_state['fetched_at_utc'].strftime('%Y-%m-%d %H:%M UTC')} • {len(df):,} unique postings • {st.session_state['collection_note']}")

left_filter, right_filter = st.columns(2)
with left_filter:
    selected_cities = st.multiselect("Filter by listed location", sorted(df["location"].dropna().unique()))
with right_filter:
    selected_skills = st.multiselect("Filter: must mention each selected skill", list(SKILLS))
filtered = df.copy()
if selected_cities: filtered = filtered[filtered["location"].isin(selected_cities)]
for skill in selected_skills: filtered = filtered[filtered[skill]]
if filtered.empty:
    st.warning("No postings match these filters. Adjust the filters to continue."); st.stop()

salary_records = filtered["salary_min"].notna() | filtered["salary_max"].notna()
k1,k2,k3,k4 = st.columns(4)
k1.metric("Filtered postings", f"{len(filtered):,}"); k2.metric("Unique companies", f"{filtered['company'].nunique():,}")
k3.metric("Listed locations", f"{filtered['location'].nunique():,}"); k4.metric("Salary records", f"{salary_records.sum():,} ({salary_records.mean():.0%})")
st.divider()
left,right = st.columns(2)
with left:
    st.subheader("Skill demand")
    skill_data = (pd.Series({s:int(filtered[s].sum()) for s in SKILLS}).sort_values(ascending=False) / len(filtered) * 100).rename_axis("skill").reset_index(name="posting_share")
    st.altair_chart(alt.Chart(skill_data).mark_bar(color="#245B88").encode(x=alt.X("posting_share:Q",title="Postings mentioning skill (%)"),y=alt.Y("skill:N",sort="-x",title=None),tooltip=["skill",alt.Tooltip("posting_share:Q",format=".1f")]).properties(height=460),use_container_width=True)
with right:
    st.subheader("Location concentration")
    city_data = filtered["location"].value_counts().head(12).rename_axis("location").reset_index(name="postings")
    st.altair_chart(alt.Chart(city_data).mark_bar(color="#B64C3B").encode(x=alt.X("postings:Q",title="Postings"),y=alt.Y("location:N",sort="-x",title=None),tooltip=["location","postings"]).properties(height=460),use_container_width=True)

st.subheader("Top hiring companies")
top_companies = sqlite_query(filtered, "SELECT company, COUNT(*) AS postings FROM jobs WHERE company IS NOT NULL AND TRIM(company) <> '' GROUP BY company ORDER BY postings DESC, company LIMIT 10")
st.caption("This SQLite query runs against the currently filtered postings.")
st.dataframe(top_companies, use_container_width=True, hide_index=True)
st.subheader("Salary transparency")
if salary_records.any():
    disclosed = filtered.loc[salary_records,["salary_min","salary_max","salary_is_predicted"]].copy()
    disclosed["salary_midpoint"] = disclosed[["salary_min","salary_max"]].mean(axis=1)
    st.metric("Median advertised salary midpoint", f"₹{disclosed['salary_midpoint'].median():,.0f}")
    st.caption(f"Based on {len(disclosed):,} salary records; {disclosed['salary_is_predicted'].fillna(False).astype(bool).mean():.0%} are API-predicted. Treat this as indicative, not a market benchmark.")
else:
    st.info("No salary fields are available for the active filters. Do not draw salary conclusions from this selection.")
with st.expander("View and export filtered postings"):
    display_cols = ["title","company","location","created","salary_min","salary_max","salary_is_predicted","redirect_url"]
    st.dataframe(filtered[display_cols],use_container_width=True,hide_index=True)
    st.download_button("Download filtered data as CSV",filtered.to_csv(index=False).encode("utf-8"),"india_data_analyst_jobs.csv","text/csv")
st.caption("Limitations: Adzuna is an aggregator; coverage changes. Regex skill matching can miss implicit skills or match ambiguous terms. Salary fields may be absent, predicted, or non-comparable.")
