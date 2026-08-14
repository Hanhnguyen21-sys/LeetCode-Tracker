import csv
import json
import math
import os
import requests
from dotenv import load_dotenv
import streamlit as st
load_dotenv()

REPO_OWNER = os.getenv("REPO_OWNER", "liquidslr")
REPO_NAME = os.getenv("REPO_NAME", "leetcode-company-wise-problemsPublic")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@st.cache_data(ttl=3600)

def fetch_company_problems(company_name: str, csv_file_name: str = "5. All.csv"):
    """Fetches questions directly from GitHub CSV files."""
    company_folder = company_name.strip()
    encoded_filename = csv_file_name.replace(" ", "%20")

    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{company_folder}/{encoded_filename}"

    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    response = requests.get(raw_url, headers=headers)

    if response.status_code == 404:
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/master/{company_folder}/{encoded_filename}"
        response = requests.get(raw_url, headers=headers)

    if response.status_code == 404:
        print(f"❌ Could not find folder '{company_folder}' or file '{csv_file_name}'.")
        return []

    response.raise_for_status()
    csv_lines = response.text.splitlines()
    reader = csv.DictReader(csv_lines)
    return list(reader)


def build_mixed_daily_roadmap(problems: list, questions_per_day: int = 3) -> dict:
    """
    Guarantees a true Easy -> Medium -> Hard mix per day by popping 
    one problem from each difficulty pool sequentially for each day.
    """
    easy_pool = []
    medium_pool = []
    hard_pool = []

    # 1. Categorize into strict difficulty pools
    for p in problems:
        diff = p.get("Difficulty", "").strip().upper()
        if "EASY" in diff:
            easy_pool.append(p)
        elif "HARD" in diff:
            hard_pool.append(p)
        else:
            medium_pool.append(p)

    total_problems = len(problems)
    total_days = math.ceil(total_problems / questions_per_day)

    roadmap = {
        "summary": {
            "total_questions": total_problems,
            "questions_per_day": questions_per_day,
            "estimated_days": total_days,
            "difficulty_breakdown": {
                "Easy": len(easy_pool),
                "Medium": len(medium_pool),
                "Hard": len(hard_pool),
            },
        },
        "schedule": {},
    }

    # 2. Build daily schedules by round-robin popping from Easy, Medium, and Hard
    for day in range(1, total_days + 1):
        day_batch = []

        # Target sequence for a standard day (e.g. for 3 questions: [Easy, Medium, Hard])
        # For 4 questions: [Easy, Medium, Hard, Medium]
        pools_to_check = [easy_pool, medium_pool, hard_pool]
        if questions_per_day >= 4:
            pools_to_check.append(medium_pool)  # Add extra Medium for 4 questions
        if questions_per_day >= 5:
            pools_to_check.append(easy_pool)    # Add extra Easy for 5 questions

        for pool in pools_to_check:
            if len(day_batch) < questions_per_day and pool:
                day_batch.append(pool.pop(0))

        # Fallback: If any primary pool ran out early, fill remaining slots from ANY available pool
        while len(day_batch) < questions_per_day:
            if easy_pool:
                day_batch.append(easy_pool.pop(0))
            elif medium_pool:
                day_batch.append(medium_pool.pop(0))
            elif hard_pool:
                day_batch.append(hard_pool.pop(0))
            else:
                break  # All questions used

        # Sort the single day's batch explicitly: Easy (1) -> Medium (2) -> Hard (3)
        def sort_inside_day(prob):
            d = prob.get("Difficulty", "").upper()
            if "EASY" in d:
                return 1
            if "MEDIUM" in d:
                return 2
            return 3

        day_batch.sort(key=sort_inside_day)

        # Record day schedule
        roadmap["schedule"][f"Day_{day}"] = [
            {
                "title": p.get("Title") or p.get("ID") or p.get("Name"),
                "difficulty": p.get("Difficulty", "N/A"),
                "acceptance": p.get("Acceptance", "N/A"),
                "url": p.get("URL") or p.get("Link", "N/A"),
                "status": "Pending",
            }
            for p in day_batch
        ]

    return roadmap

def main():
    print("==================================================")
    print(" 🚀 LeetCode Balanced Daily Roadmap Generator ")
    print("==================================================")

    company_input = input("\nEnter Company Name (e.g., Meta, Apple, Google): ").strip()
    if not company_input:
        print("No company entered. Exiting...")
        return

    problems = fetch_company_problems(company_input, csv_file_name="5. All.csv")
    if not problems:
        return

    print(f"\n✅ Found {len(problems)} total problems for '{company_input}'.")

    try:
        pace_input = input("How many questions per day would you like to solve? (3-5) [Default: 4]: ").strip()
        questions_per_day = int(pace_input) if pace_input else 4
        if questions_per_day < 1:
            questions_per_day = 4
    except ValueError:
        questions_per_day = 4

    roadmap = build_mixed_daily_roadmap(problems, questions_per_day=questions_per_day)
    total_days = roadmap["summary"]["estimated_days"]

    output_filename = f"{company_input.lower().replace(' ', '_')}_roadmap.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(roadmap, f, indent=2)

    print(f"\n🎉 Roadmap generated! Paced across {total_days} days ({questions_per_day} questions/day).")
    print(f"📁 Saved to `{output_filename}`.")

    # Display Preview
    print("\n" + "=" * 50)
    print(f" 🗓️  ROADMAP PREVIEW FOR {company_input.upper()}")
    print("=" * 50)

    for day in ["Day_1", "Day_2"]:
        if day in roadmap["schedule"]:
            print(f"\n📌 {day.replace('_', ' ')}:")
            for idx, q in enumerate(roadmap["schedule"][day], 1):
                print(f"   {idx}. {q['title']} [{q['difficulty']}]")


if __name__ == "__main__":
    main()