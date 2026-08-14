import csv
import json
import math
import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
REPO_OWNER = os.getenv("REPO_OWNER", "liquidslr")
REPO_NAME = os.getenv("REPO_NAME", "leetcode-company-wise-problemsPublic")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Page Config
st.set_page_config(page_title="LeetCode Study Roadmap", page_icon="⚡", layout="wide")


# =====================================================================
# Helper Functions
# =====================================================================
@st.cache_data(ttl=3600)
def fetch_company_problems(company_name: str):
    """Fetches questions directly from GitHub CSV files."""
    company_folder = company_name.strip()
    encoded_filename = "5.%20All.csv"

    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{company_folder}/{encoded_filename}"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    response = requests.get(raw_url, headers=headers)
    if response.status_code == 404:
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/master/{company_folder}/{encoded_filename}"
        response = requests.get(raw_url, headers=headers)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    csv_lines = response.text.splitlines()
    return list(csv.DictReader(csv_lines))


def build_mixed_roadmap(problems: list, questions_per_day: int = 3) -> dict:
    """Generates an Easy -> Medium -> Hard mixed daily schedule."""
    easy_pool = [p for p in problems if "EASY" in p.get("Difficulty", "").upper()]
    hard_pool = [p for p in problems if "HARD" in p.get("Difficulty", "").upper()]
    medium_pool = [p for p in problems if p not in easy_pool and p not in hard_pool]

    total_problems = len(problems)
    total_days = math.ceil(total_problems / questions_per_day)
    schedule = {}

    for day in range(1, total_days + 1):
        day_batch = []
        pools = [easy_pool, medium_pool, hard_pool]
        if questions_per_day >= 4:
            pools.append(medium_pool)
        if questions_per_day >= 5:
            pools.append(easy_pool)

        for pool in pools:
            if len(day_batch) < questions_per_day and pool:
                day_batch.append(pool.pop(0))

        while len(day_batch) < questions_per_day:
            if easy_pool:
                day_batch.append(easy_pool.pop(0))
            elif medium_pool:
                day_batch.append(medium_pool.pop(0))
            elif hard_pool:
                day_batch.append(hard_pool.pop(0))
            else:
                break

        # Sort inside the day: Easy -> Medium -> Hard
        def diff_rank(p):
            d = p.get("Difficulty", "").upper()
            return 1 if "EASY" in d else (2 if "MEDIUM" in d else 3)

        day_batch.sort(key=diff_rank)

        schedule[f"Day {day}"] = [
            {
                "id": f"day_{day}_q_{idx}",
                "title": p.get("Title") or p.get("ID") or p.get("Name"),
                "difficulty": p.get("Difficulty", "N/A"),
                "url": p.get("URL") or p.get("Link", "#"),
            }
            for idx, p in enumerate(day_batch, 1)
        ]

    return schedule


# =====================================================================
# Sidebar Configuration
# =====================================================================
st.sidebar.title("🎯 Preparation Setup")
company = st.sidebar.text_input("Enter Company Name", value="Meta")
pace = st.sidebar.slider("Questions per Day", min_value=1, max_value=5, value=3)

# Load / Save Completed State
PROGRESS_FILE = f"{company.lower().strip()}_progress.json"

if "completed_questions" not in st.session_state:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            st.session_state.completed_questions = set(json.load(f))
    else:
        st.session_state.completed_questions = set()


def save_progress():
    with open(PROGRESS_FILE, "w") as f:
        json.dump(list(st.session_state.completed_questions), f)


# =====================================================================
# Main Application Dashboard
# =====================================================================
st.title(f"🚀 {company} LeetCode Roadmap")

if company:
    raw_problems = fetch_company_problems(company)

    if not raw_problems:
        st.error(
            f"Could not find questions for **{company}**. Make sure the folder name exists on GitHub (case-sensitive)."
        )
    else:
        # Build Roadmap
        schedule = build_mixed_roadmap(raw_problems, questions_per_day=pace)

        # Calculate Statistics
        total_questions = sum(len(qs) for qs in schedule.values())
        completed_count = len(
            [
                q_id
                for day in schedule.values()
                for q in day
                if (q_id := q["title"]) in st.session_state.completed_questions
            ]
        )
        progress_percentage = (
            completed_count / total_questions if total_questions > 0 else 0.0
        )

        # Dashboard Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Questions", total_questions)
        m2.metric("Questions Solved", completed_count)
        m3.metric("Remaining", total_questions - completed_count)
        m4.metric("Estimated Days", len(schedule))

        st.progress(progress_percentage)
        st.caption(
            f"**Overall Progress:** {int(progress_percentage * 100)}% completed"
        )
        st.divider()

        # Tabs for Dashboard Views
        tab1, tab2 = st.tabs(["🗓️ Daily Schedule", "📊 All Questions View"])

        # -----------------------------------------------------------------
        # TAB 1: Daily Schedule View
        # -----------------------------------------------------------------
        with tab1:
            st.subheader("Your Daily Action Plan")

            for day_label, questions in schedule.items():
                # Count day completion
                day_completed = sum(
                    1
                    for q in questions
                    if q["title"] in st.session_state.completed_questions
                )

                with st.expander(
                    f"**{day_label}** ({day_completed}/{len(questions)} Completed)"
                ):
                    for q in questions:
                        col1, col2 = st.columns([0.05, 0.95])

                        is_checked = (
                            q["title"] in st.session_state.completed_questions
                        )

                        # Checkbox interaction
                        checked = col1.checkbox(
                                f"Complete {q['title']}",
                                value=is_checked,
                                key=f"cb_{day_label}_{q['title']}",
                                label_visibility="collapsed",
)

                        if checked != is_checked:
                            if checked:
                                st.session_state.completed_questions.add(q["title"])
                            else:
                                st.session_state.completed_questions.discard(
                                    q["title"]
                                )
                            save_progress()
                            st.rerun()

                        # Difficulty Badge Colors
                        # Extract and normalize difficulty
                        diff_raw = q["difficulty"].strip().upper()

                        if "EASY" in diff_raw:
                            display_diff = "Easy"
                            color = "green"
                        elif "HARD" in diff_raw:
                            display_diff = "Hard"
                            color = "red"
                        else:
                            display_diff = "Medium"
                            color = "orange"

                        col2.markdown(
                            f"**{q['title']}** &nbsp;&nbsp; :{color}[**{display_diff}**]",
                            unsafe_allow_html=True,
                        )

        # -----------------------------------------------------------------
        # TAB 2: All Questions View
        # -----------------------------------------------------------------
        with tab2:
            st.subheader(f"All Questions for {company}")

            search_query = st.text_input("🔍 Search questions or topics...")

            for day_label, questions in schedule.items():
                for q in questions:
                    if (
                        search_query.lower() in q["title"].lower()
                        or search_query.lower() in q["difficulty"].lower()
                    ):
                        c1, c2, c3 = st.columns([0.1, 0.65, 0.25])

                        is_done = q["title"] in st.session_state.completed_questions

                        done = c1.checkbox(
                            f"Complete {q['title']}",
                            value=is_done,
                            key=f"all_{q['title']}",
                            label_visibility="collapsed",
                        )

                        if done != is_done:
                            if done:
                                st.session_state.completed_questions.add(q["title"])
                            else:
                                st.session_state.completed_questions.discard(q["title"])
                            save_progress()
                            st.rerun()

                        # Title
                        c2.write(f"**{q['title']}**")

                        # Difficulty
                        diff_raw = q["difficulty"].strip().upper()

                        if "EASY" in diff_raw:
                            display_diff = "Easy"
                            color = "green"
                        elif "HARD" in diff_raw:
                            display_diff = "Hard"
                            color = "red"
                        else:
                            display_diff = "Medium"
                            color = "orange"

                        c3.markdown(f":{color}[**{display_diff}**]")