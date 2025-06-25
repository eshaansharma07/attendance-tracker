import streamlit as st
import json
import datetime
import pandas as pd
import requests
from PIL import Image
import io

st.set_page_config(page_title="Smart Attendance Tracker with AI", layout="wide")

# -------------------- Constants -------------------- #
OCR_API_KEY = "K81789618588957"  # Replace with your actual key
OCR_URL = "https://api.ocr.space/parse/image"

# -------------------- Load or Initialize Data -------------------- #
def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

def load_timetable():
    try:
        with open("timetable.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_timetable(timetable):
    with open("timetable.json", "w") as f:
        json.dump(timetable, f, indent=4)

# -------------------- App Logic -------------------- #
data = load_data()
timetable = load_timetable()
today = datetime.datetime.now().strftime("%A")

st.title("📉 Smart Attendance Tracker with AI Skip Prediction")

# -------------------- Attendance Actions -------------------- #
if today in timetable:
    st.subheader(f"📅 Today is: {today}")
    for subject in timetable[today]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"### {subject}")
        with col2:
            if st.button(f"✅ Attended {subject}"):
                data[subject]["attended"] += 1
                data[subject]["history"].append({"date": str(datetime.date.today()), "status": "Present"})
                save_data(data)
        with col3:
            if st.button(f"❌ Missed {subject}"):
                data[subject]["missed"] += 1
                data[subject]["history"].append({"date": str(datetime.date.today()), "status": "Absent"})
                save_data(data)
else:
    st.info("No subjects scheduled for today.")

# -------------------- Add Subject -------------------- #
st.sidebar.header("➕ Add Subject")
subject_name = st.sidebar.text_input("Subject name")
target = st.sidebar.slider("Minimum Attendance %", 50, 100, 75)
if st.sidebar.button("Add Subject"):
    if subject_name:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": []}
        save_data(data)
        st.sidebar.success(f"Added {subject_name}")

# -------------------- Remove Subject -------------------- #
st.sidebar.header("🗑 Remove Subject")
if data:
    remove_subj = st.sidebar.selectbox("Select subject", list(data.keys()))
    if st.sidebar.button("Remove Subject"):
        data.pop(remove_subj)
        save_data(data)
        st.sidebar.warning(f"Removed {remove_subj}")

# -------------------- Timetable Editor -------------------- #
st.sidebar.header("🗓 Timetable Editor")
day = st.sidebar.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
subject_for_day = st.sidebar.text_input("Add subject to " + day)
if st.sidebar.button("Add to Timetable"):
    if day not in timetable:
        timetable[day] = []
    timetable[day].append(subject_for_day)
    save_timetable(timetable)
    st.sidebar.success(f"Added {subject_for_day} to {day}")

# -------------------- Export Data -------------------- #
st.subheader("📊 Export Attendance Data")
if st.button("Download CSV"):
    records = []
    for subject, stats in data.items():
        total = stats["attended"] + stats["missed"]
        percentage = (stats["attended"] / total) * 100 if total > 0 else 0
        skip_possible = int((stats["attended"] / stats["target"] * 100 - 100) * total / 100) if stats["target"] else 0
        records.append({
            "Subject": subject,
            "Attended": stats["attended"],
            "Missed": stats["missed"],
            "Percentage": round(percentage, 2),
            "Target": stats["target"],
            "Classes you can skip": max(skip_possible, 0)
        })
    df = pd.DataFrame(records)
    st.download_button("Download CSV", df.to_csv(index=False), file_name="attendance.csv", mime="text/csv")

# -------------------- OCR Timetable Upload -------------------- #
st.subheader("📷 Upload Timetable Image")
section_options = ["A", "B"]
selected_section = st.selectbox("Select your group/section", section_options)
uploaded_file = st.file_uploader("Upload timetable image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image_bytes = uploaded_file.read()
    st.image(image_bytes, caption="Uploaded Image")

    response = requests.post(
        OCR_URL,
        files={"filename": image_bytes},
        data={"apikey": OCR_API_KEY, "language": "eng"},
    )

    result = response.json()
    try:
        extracted_text = result["ParsedResults"][0]["ParsedText"]
        st.text_area("🧾 Extracted Text", extracted_text, height=200)

        if selected_section in extracted_text:
            st.success(f"Timetable for Group {selected_section} detected!")
            # TODO: Auto-parse and update timetable.json
        else:
            st.warning(f"Could not find '{selected_section}' in text. Check your image.")
    except:
        st.error("OCR failed. Please try again with a clearer image.")
