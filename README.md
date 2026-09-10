# India Data Analyst Job Market Dashboard

I built this to figure out something I actually wanted to know for myself: what do
data analyst job postings in India actually ask for, and does that match what
everyone online tells beginners to learn? Most "top skills" lists you find online
are US-based or just recycled from other blog posts, so I decided to pull real,
live postings and check for myself.

It started as a one-time notebook analysis, then I turned it into a small live
Streamlit app so I (and anyone else) can re-run it whenever and see current
numbers instead of a snapshot from whenever I happened to run the script.

## Try it

`streamlit run app.py` after installing requirements — or use the deployed link
if I've put one up (check the top of this README once it's live).

## What it actually does

- Pulls live job postings from the [Adzuna API](https://developer.adzuna.com/) — you search "data analyst" jobs in India, and it goes and grabs up to a few hundred/thousand postings depending on how many pages you ask for
- Goes through every job description and checks for mentions of ~19 different skills (SQL, Python, Excel, Power BI, etc.) using regex — nothing fancy, just pattern matching on the raw text
- Dumps everything into a little SQLite database in memory so I could practice writing actual SQL queries instead of just doing everything in Pandas
- Lets you filter by city or by skill and see the numbers update
- You can download whatever you're looking at as a CSV

## Why I did it this way

Honestly my first version of this was just a Jupyter notebook — pull data once,
make a couple of charts, done. But that felt kind of static and boring for a
portfolio piece, so I rebuilt it as an app where the data can actually be
refreshed. It's a small thing but it changes the project from "here's a chart I
made once" to "here's a tool that answers this question whenever you ask it."

## Things I found that were actually interesting

- SQL and Excel show up in a LOT of postings, but that doesn't mean they pay
  more — if anything the postings that mention them skew slightly lower, probably
  because they're just baseline/expected skills rather than a differentiator
- Bangalore alone had roughly a quarter of all postings in my sample. Hyderabad
  and Mumbai were next but nowhere close
- Most Indian postings just don't list a salary at all (way more than I expected)
  — so I stopped trying to force a salary analysis and just reported that fact
  instead, since pretending the data supports something it doesn't felt worse
  than admitting the gap

## Stuff that's not perfect about this

- The skill detection is just keyword matching, so if a posting says "structured
  query language" instead of "SQL" it won't get counted. I know this undercounts
  some things.
- Adzuna doesn't cover every job board out there, so this isn't "the whole Indian
  job market," it's just what Adzuna has indexed
- The "R" skill detection is a bit shaky since it's matching a single letter —
  I added a rough regex fix for it but it's probably still noisier than the rest

## Built with

Python, Streamlit, Pandas, SQLite, Regex, Altair, the Adzuna REST API

## Running it yourself

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# put your own Adzuna App ID + Key in that file
streamlit run app.py
```

You'll need your own free Adzuna API key from developer.adzuna.com — takes like
5 minutes to sign up.
