import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import requests
import re

# Constants
DATA_FILE = "data.json"
TIMETABLE_FILE = "timetable.json"
OCR_API_KEY = "K81789618588957"

# Data Functions
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

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

# Attendance Calculations
def calculate_stats(subject_data):
    a, m = subject_data["attended"], subject_data["missed"]
    total = a + m
    if total == 0:
        return 0, 0, 0
    percent = (a / total) * 100
    target = subject_data["target"]
    can_skip = int((a / (target / 100)) - total) if percent >= target else 0
    must_attend = int(((target / 100 * total - a) / (1 - target / 100)) + 1) if percent < target else 0
    return round(percent, 2), can_skip, must_attend

def ai_can_skip(subject_data):
    a, m = subject_data["attended"], subject_data["missed"]
    total = a + m + 1
    new_percent = (a / total) * 100 if total > 0 else 0
    return new_percent >= subject_data["target"], round(new_percent, 2)

def get_today():
    return datetime.now().strftime("%A")

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_week_range():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    return [start + timedelta(days=i) for i in range(7)]

def get_weekly_summary(subject_data):
    if "history" not in subject_data:
        return 0, 0, 0
    week_dates = [d.strftime("%Y-%m-%d") for d in get_week_range()]
    attended = sum(1 for d in week_dates if subject_data["history"].get(d) == "attended")
    missed = sum(1 for d in week_dates if subject_data["history"].get(d) == "missed")
    total = attended + missed
    percent = (attended / total) * 100 if total > 0 else 0
    return attended, total, round(percent, 2)

# OCR Function using API
def extract_text_from_image(image):
    buffered = image.convert("RGB")
    buffered.save("temp_img.png")
    with open("temp_img.png", "rb") as f:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": f},
            data={"apikey": OCR_API_KEY, "language": "eng"},
        )
    os.remove("temp_img.png")
    result = response.json()
    if result["IsErroredOnProcessing"]:
        return "OCR failed. Try again."
    return result["ParsedResults"][0]["ParsedText"]

# Streamlit UI
st.set_page_config(page_title="📈 Smart Attendance Tracker", layout="centered")
st.title("📈 Smart Attendance Tracker with AI Skip Prediction")

data = load_data()
timetable = load_timetable()
today = get_today()
today_date = get_today_date()
today_subjects = timetable.get(today, [])

# Sidebar - Add / Remove Subjects
st.sidebar.header("➕ Add Subject")
subject_name = st.sidebar.text_input("Subject name")
target = st.sidebar.slider("Minimum Attendance %", 50, 100, 75)

if st.sidebar.button("Add Subject"):
    if subject_name and subject_name not in data:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": {}}
        save_data(data)
        st.sidebar.success(f"Added {subject_name}")
        st.rerun()

st.sidebar.header("🗑️ Remove Subject")
if data:
    to_remove = st.sidebar.selectbox("Select to remove", list(data.keys()))
    if st.sidebar.button("Remove Subject"):
        del data[to_remove]
        save_data(data)
        st.sidebar.success(f"Removed {to_remove}")
        st.rerun()

# Sidebar - Timetable Editor
st.sidebar.header("🕒 Timetable Editor")
selected_day = st.sidebar.selectbox("Select Day", list(timetable.keys()))
new_subject = st.sidebar.text_input(f"Add subject to {selected_day}")
if st.sidebar.button("Add to Timetable"):
    if new_subject in data and new_subject not in timetable[selected_day]:
        timetable[selected_day].append(new_subject)
        save_timetable(timetable)
        st.sidebar.success(f"Added {new_subject} to {selected_day}")
        st.rerun()

if timetable[selected_day]:
    rm_subject = st.sidebar.selectbox("Remove from timetable", timetable[selected_day])
    if st.sidebar.button("Remove from Timetable"):
        timetable[selected_day].remove(rm_subject)
        save_timetable(timetable)
        st.sidebar.success(f"Removed {rm_subject} from {selected_day}")
        st.rerun()

# Main Section - Today's Classes
st.subheader(f"📅 Today is: {today}")
if today_subjects:
    for subject in today_subjects:
        if subject in data:
            col1, col2, col3 = st.columns(3)
            if col1.button(f"✅ Present - {subject}"):
                data[subject]["attended"] += 1
                data[subject]["history"][today_date] = "attended"
                save_data(data)
                st.rerun()
            if col2.button(f"❌ Absent - {subject}"):
                data[subject]["missed"] += 1
                data[subject]["history"][today_date] = "missed"
                save_data(data)
                st.rerun()
            percent, can_skip, must_attend = calculate_stats(data[subject])
            can_ai_skip, pred_percent = ai_can_skip(data[subject])
            col3.metric("Attendance %", f"{percent}%")
            st.write(f"🎯 Target: {data[subject]['target']}%")
            st.write(f"Can Skip: {can_skip}")
            st.write(f"Must Attend: {must_attend}")
            st.write("🧠 AI Prediction:")
            st.success("Safe to skip ➜ {:.2f}%".format(pred_percent)) if can_ai_skip else st.error("Don't skip ➜ {:.2f}%".format(pred_percent))
            a, t, p = get_weekly_summary(data[subject])
            st.info(f"📊 Weekly: {a}/{t} attended ({p}%)")
            st.markdown("---")
else:
    st.info("No subjects scheduled for today.")

# Export
st.subheader("📤 Export Attendance Data")
if st.button("📁 Download CSV"):
    df = pd.DataFrame([{
        "Subject": k,
        "Target %": v["target"],
        "Attended": v["attended"],
        "Missed": v["missed"],
        "Attendance %": calculate_stats(v)[0]
    } for k, v in data.items()])
    st.download_button("⬇️ Download", df.to_csv(index=False), "attendance.csv", "text/csv")

# Upload Timetable Image (Cloud OCR)
st.subheader("📷 Upload Timetable Image (Auto-detect GROUP B)")
uploaded = st.file_uploader("Upload timetable image (with both Group A & B)", type=["jpg", "jpeg", "png"])

if uploaded:
    img = Image.open(uploaded)
    st.image(img, caption="Uploaded Image", use_column_width=True)
    extracted_text = extract_text_from_image(img)
    st.text_area("🧾 Extracted Text", extracted_text, height=250)

    if "GROUP B" not in extracted_text:
        st.warning("Could not find 'GROUP B' in text. Check your image.")
    else:
        group_b_text = extracted_text.split("B", 1)[1]
        st.markdown("### 📋 Parsed Timetable from GROUP B")

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        parsed = {day: [] for day in days}
        for line in group_b_text.splitlines():
            line = line.strip()
            for day in days:
                if re.match(day, line, re.IGNORECASE):
                    subjects = re.split(r'\s{2,}', line[len(day):].strip())
                    parsed[day] = [s.strip().title() for s in subjects if s.strip()]
        st.json(parsed)

        if st.button("✅ Save as Timetable"):
            save_timetable(parsed)
            st.success("✅ Timetable saved from image!")
            st.rerun()
