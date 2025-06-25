import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd

DATA_FILE = "data.json"
TIMETABLE_FILE = "timetable.json"

# ---------- Data Handling ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_timetable():
    if not os.path.exists(TIMETABLE_FILE):
        return {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}
    with open(TIMETABLE_FILE, "r") as f:
        return json.load(f)

def save_timetable(timetable):
    with open(TIMETABLE_FILE, "w") as f:
        json.dump(timetable, f, indent=4)

# ---------- Stats & Prediction ----------
def calculate_stats(subject_data):
    total = subject_data["attended"] + subject_data["missed"]
    if total == 0:
        return 0, 0, 0
    percentage = (subject_data["attended"] / total) * 100
    target = subject_data["target"]
    can_skip = int((subject_data["attended"] / (target / 100)) - total) if percentage >= target else 0
    must_attend = int(((target / 100 * total - subject_data["attended"]) / (1 - target / 100)) + 1) if percentage < target else 0
    return round(percentage, 2), can_skip, must_attend

def ai_can_skip(subject_data):
    a = subject_data["attended"]
    m = subject_data["missed"]
    t = a + m
    target = subject_data["target"]
    new_missed = m + 1
    new_total = a + new_missed
    new_percent = (a / new_total) * 100 if new_total > 0 else 0
    return new_percent >= target, round(new_percent, 2)

def get_today():
    return datetime.now().strftime("%A")

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_week_range():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())  # Monday
    return [start + timedelta(days=i) for i in range(7)]

def get_weekly_summary(subject_data):
    if "history" not in subject_data:
        return 0, 0, 0
    week_dates = [d.strftime("%Y-%m-%d") for d in get_week_range()]
    attended = sum(1 for d in week_dates if subject_data["history"].get(d) == "attended")
    missed = sum(1 for d in week_dates if subject_data["history"].get(d) == "missed")
    total = attended + missed
    percentage = (attended / total) * 100 if total > 0 else 0
    return attended, total, round(percentage, 2)

# ---------- Streamlit App ----------
st.set_page_config(page_title="📈 Smart Attendance Tracker", layout="centered")
st.title("📈 Smart Attendance Tracker with AI Skip Prediction")

data = load_data()
timetable = load_timetable()
today = get_today()
today_date = get_today_date()
today_subjects = timetable.get(today, [])

# ---------- Sidebar: Add Subject ----------
st.sidebar.header("➕ Add Subject")
subject_name = st.sidebar.text_input("Subject name")
target = st.sidebar.slider("Minimum Attendance %", 50, 100, 75)

if st.sidebar.button("Add Subject"):
    if subject_name in data:
        st.sidebar.warning("Subject already exists.")
    elif subject_name.strip() == "":
        st.sidebar.warning("Subject name cannot be empty.")
    else:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": {}}
        save_data(data)
        st.sidebar.success(f"Added {subject_name}")
        st.experimental_rerun()

# ---------- Sidebar: Remove Subject ----------
st.sidebar.header("🗑️ Remove Subject")
if data:
    subject_to_remove = st.sidebar.selectbox("Select subject to remove", list(data.keys()))
    if st.sidebar.button("Remove Subject"):
        del data[subject_to_remove]
        save_data(data)
        st.sidebar.success(f"Removed {subject_to_remove}")
        st.experimental_rerun()

# ---------- Sidebar: Timetable Editor ----------
st.sidebar.header("🕒 Timetable Editor")
selected_day = st.sidebar.selectbox("Select Day", list(timetable.keys()))
current_subjects = timetable[selected_day]
new_subject = st.sidebar.text_input("Add subject to " + selected_day)

if st.sidebar.button("Add to Timetable"):
    if new_subject in data:
        if new_subject not in timetable[selected_day]:
            timetable[selected_day].append(new_subject)
            save_timetable(timetable)
            st.sidebar.success(f"Added {new_subject} to {selected_day}")
            st.experimental_rerun()
        else:
            st.sidebar.warning("Subject already in timetable.")
    else:
        st.sidebar.error("Add the subject first before adding to timetable.")

if current_subjects:
    subject_to_remove_tt = st.sidebar.selectbox("Remove from timetable", current_subjects)
    if st.sidebar.button("Remove from Timetable"):
        timetable[selected_day].remove(subject_to_remove_tt)
        save_timetable(timetable)
        st.sidebar.success(f"Removed {subject_to_remove_tt} from {selected_day}")
        st.experimental_rerun()

# ---------- Main: Today's Subjects ----------
st.subheader(f"🗓️ Today is: {today}")
if today_subjects:
    st.markdown("### 📚 Today's Subjects")
    for subject in today_subjects:
        if subject in data:
            col1, col2, col3 = st.columns(3)
            if col1.button(f"✅ Present - {subject}"):
                data[subject]["attended"] += 1
                data[subject]["history"][today_date] = "attended"
                save_data(data)
                st.experimental_rerun()
            if col2.button(f"❌ Absent - {subject}"):
                data[subject]["missed"] += 1
                data[subject]["history"][today_date] = "missed"
                save_data(data)
                st.experimental_rerun()

            percent, can_skip, must_attend = calculate_stats(data[subject])
            can_skip_ai, sim_skip_percent = ai_can_skip(data[subject])
            weekly_attended, weekly_total, weekly_percent = get_weekly_summary(data[subject])

            col3.metric("Attendance %", f"{percent}%")
            st.write(f"🎯 Target: {data[subject]['target']}%")
            st.write(f"Can Skip: {can_skip} class(es)")
            st.write(f"Must Attend: {must_attend} class(es)")

            if percent >= data[subject]["target"]:
                st.success("✅ On track! 🎉")
                if can_skip_ai:
                    st.info(f"🟢 You can safely skip the next class (→ {sim_skip_percent}%)")
                else:
                    st.warning(f"🟡 Skipping will drop you below target (→ {sim_skip_percent}%)")
            else:
                st.error(f"🔴 Below target! You must attend to recover.")

            st.markdown(f"📅 **Weekly Summary**: {weekly_attended}/{weekly_total} attended (**{weekly_percent}%**)")
            st.markdown("---")
else:
    st.info("No subjects scheduled for today.")

# ---------- CSV Export ----------
st.subheader("📤 Export Attendance Data")

if st.button("📁 Download CSV"):
    csv_data = []
    for subject, info in data.items():
        percent, can_skip, must_attend = calculate_stats(info)
        total = info["attended"] + info["missed"]
        csv_data.append({
            "Subject": subject,
            "Target %": info["target"],
            "Attended": info["attended"],
            "Missed": info["missed"],
            "Total": total,
            "Attendance %": percent,
            "Can Skip": can_skip,
            "Must Attend": must_attend
        })
    df = pd.DataFrame(csv_data)
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), file_name="attendance_report.csv", mime="text/csv")
