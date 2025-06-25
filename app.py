import streamlit as st
import json
import datetime
import pandas as pd
import requests
from PIL import Image
from io import BytesIO

st.set_page_config(page_title="Smart Attendance Tracker", layout="wide")
st.title("\U0001F4C8 Smart Attendance Tracker with AI Skip Prediction")

# Load or initialize data
def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

def load_timetable():
    try:
        with open("timetable.json", "r") as f:
            return json.load(f)
    except:
        return {"Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": []}

def save_timetable(timetable):
    with open("timetable.json", "w") as f:
        json.dump(timetable, f)

data = load_data()
timetable = load_timetable()

group_short_to_full = {
    "A": "24AML-102 GROUP A",
    "B": "24AML-102 GROUP B",
    "24AML6-A": "24AML6-A"
}

# Sidebar: Add/Remove Subjects
st.sidebar.header("➕ Add Subject")
subject_name = st.sidebar.text_input("Subject name")
target = st.sidebar.slider("Minimum Attendance %", 50, 100, 75)
if st.sidebar.button("Add Subject"):
    if subject_name:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": []}
        save_data(data)
        st.sidebar.success(f"Added {subject_name}")

st.sidebar.header("➖ Remove Subject")
subject_to_remove = st.sidebar.selectbox("Select Subject", list(data.keys()))
if st.sidebar.button("Remove Subject"):
    if subject_to_remove in data:
        del data[subject_to_remove]
        save_data(data)
        st.sidebar.success(f"Removed {subject_to_remove}")

# Sidebar: Timetable Editor
st.sidebar.header("🕒 Timetable Editor")
day = st.sidebar.selectbox("Select Day", list(timetable.keys()))
subject_for_day = st.sidebar.text_input("Add subject to " + day)
if st.sidebar.button("Add to Timetable"):
    if subject_for_day:
        timetable[day].append(subject_for_day)
        save_timetable(timetable)
        st.sidebar.success(f"Added {subject_for_day} to {day}")

# Main section
today = datetime.datetime.now().strftime("%A")
st.subheader(f"📅 Today is: {today}")

today_subjects = timetable.get(today, [])
if today_subjects:
    for subject in today_subjects:
        if subject in data:
            attended = data[subject]["attended"]
            missed = data[subject]["missed"]
            total = attended + missed
            percentage = (attended / total * 100) if total > 0 else 0
            target = data[subject]['target']

            st.markdown(f"### {subject} — {percentage:.2f}% attendance")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Attend {subject}"):
                    data[subject]['attended'] += 1
                    data[subject]['history'].append((str(datetime.date.today()), 'attended'))
                    save_data(data)
                    st.experimental_rerun()
            with col2:
                if st.button(f"❌ Miss {subject}"):
                    data[subject]['missed'] += 1
                    data[subject]['history'].append((str(datetime.date.today()), 'missed'))
                    save_data(data)
                    st.experimental_rerun()

            if percentage >= target:
                can_skip = (data[subject]['attended'] - target/100 * total) / (1 - target/100) if target < 100 else 0
                st.info(f"You can skip {int(can_skip)} classes and still meet the {target}% target.")
            else:
                need_attend = (target/100 * total - data[subject]['attended']) / (1 - target/100) if target < 100 else 0
                st.warning(f"You need to attend {int(need_attend)+1} more classes to meet the {target}% target.")
        else:
            st.warning(f"{subject} not found in subjects list.")
else:
    st.info("No subjects scheduled for today.")

# Export
st.subheader("📤 Export Attendance Data")
if st.button("Download CSV"):
    df = pd.DataFrame.from_dict(data, orient='index')
    csv = df.to_csv().encode('utf-8')
    st.download_button("Download Attendance CSV", csv, "attendance.csv", "text/csv")

# Upload timetable image and extract using OCR.space
st.subheader("\U0001F4F7 Upload Timetable Image")
st.markdown("### Select your group/section")
selected_group = st.selectbox("Select", list(group_short_to_full.keys()))
full_group_name = group_short_to_full[selected_group]

uploaded_image = st.file_uploader("Upload timetable photo", type=["png", "jpg", "jpeg"])
if uploaded_image:
    st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
    image_bytes = uploaded_image.read()

    api_key = "K81789618588957"
    url_api = "https://api.ocr.space/parse/image"
    result = requests.post(
        url_api,
        files={"filename": image_bytes},
        data={"apikey": api_key, "language": "eng"},
    )

    result = result.json()
    if result['IsErroredOnProcessing']:
        st.error("OCR failed: " + result.get('ErrorMessage', [''])[0])
    else:
        extracted_text = result["ParsedResults"][0]["ParsedText"]
        st.text_area("📝 Extracted Text", extracted_text, height=250)

        if f" {selected_group} " not in extracted_text and selected_group not in extracted_text:
            st.warning(f"Could not find group '{selected_group}' in text. Check your image.")
        else:
            st.success(f"Timetable matched for group: {full_group_name}")
            # Here you would parse text and update timetable.json accordingly
            # Placeholder: just print extracted text
            timetable = timetable  # <- Update based on parsed OCR logic
            save_timetable(timetable)
            st.info("Parsed timetable saved (placeholder).")
