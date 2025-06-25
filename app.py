import streamlit as st
import json
import datetime
import os
import csv
from PIL import Image
import requests

st.set_page_config(page_title="Smart Attendance Tracker with AI", layout="wide")
st.title("📅 Smart Attendance Tracker with AI Skip Prediction")

# File paths
data_file = "data.json"
timetable_file = "timetable.json"
temp_image_path = "temp_timetable.jpg"

# OCR API Key
OCR_SPACE_API_KEY = "K81789618588957"

# Initialize files if not present
if not os.path.exists(data_file):
    with open(data_file, "w") as f:
        json.dump({}, f)
if not os.path.exists(timetable_file):
    with open(timetable_file, "w") as f:
        json.dump({day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}, f)

# Load data
def load_data():
    with open(data_file, "r") as f:
        return json.load(f)

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

def load_timetable():
    with open(timetable_file, "r") as f:
        return json.load(f)

def save_timetable(timetable):
    with open(timetable_file, "w") as f:
        json.dump(timetable, f, indent=4)

# AI Skip Prediction Logic
def should_skip(attended, missed, target):
    total = attended + missed + 1
    return (attended / total) * 100 >= target

# OCR using OCR.Space

def extract_text_from_image_ocr_space(image_path):
    with open(image_path, 'rb') as image_file:
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': image_file},
            data={'apikey': OCR_SPACE_API_KEY, 'language': 'eng', 'OCREngine': 2}
        )
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        return None, result.get("ErrorMessage", ["Unknown error"])[0]
    parsed_results = result.get("ParsedResults")
    if not parsed_results or not parsed_results[0].get("ParsedText"):
        return None, "No text detected in image."
    return parsed_results[0]["ParsedText"], None

# Main Logic
data = load_data()
timetable = load_timetable()

# Left Sidebar for Subject Management
with st.sidebar:
    st.header("➕ Add Subject")
    subject_name = st.text_input("Subject name")
    target = st.slider("Minimum Attendance %", 50, 100, 75)
    if st.button("Add Subject") and subject_name:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": []}
        save_data(data)
        st.success(f"Added {subject_name}")

    st.markdown("---")
    st.header("➖ Remove Subject")
    if data:
        remove_subject = st.selectbox("Select subject to remove", list(data.keys()))
        if st.button("Remove Subject"):
            del data[remove_subject]
            for day in timetable:
                if remove_subject in timetable[day]:
                    timetable[day].remove(remove_subject)
            save_data(data)
            save_timetable(timetable)
            st.success(f"Removed {remove_subject}")

    st.markdown("---")
    st.header("🛠️ Timetable Editor")
    day = st.selectbox("Select Day", list(timetable.keys()))
    subject_to_add = st.text_input("Add subject to " + day)
    if st.button("Add to Timetable") and subject_to_add:
        if subject_to_add in data:
            timetable[day].append(subject_to_add)
            save_timetable(timetable)
            st.success(f"Added {subject_to_add} to {day}")
        else:
            st.warning("Subject not found")

# Main Page Logic
today = datetime.datetime.today().strftime('%A')
st.subheader(f"📅 Today is: {today}")
if today in timetable and timetable[today]:
    for subject in timetable[today]:
        st.markdown(f"### {subject}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Attend {subject}"):
                data[subject]['attended'] += 1
                data[subject]['history'].append((str(datetime.date.today()), "Attended"))
                save_data(data)
                st.success(f"Marked attended for {subject}")
        with col2:
            if st.button(f"❌ Miss {subject}"):
                data[subject]['missed'] += 1
                data[subject]['history'].append((str(datetime.date.today()), "Missed"))
                save_data(data)
                st.error(f"Marked missed for {subject}")
        # AI Prediction
        if should_skip(data[subject]['attended'], data[subject]['missed'], data[subject]['target']):
            st.info(f"🤖 You can skip this class and still meet your target!")
        else:
            st.warning(f"⚠️ Skipping this class will drop you below your attendance goal.")
else:
    st.info("No subjects scheduled for today.")

# Export Option
st.markdown("---")
st.subheader("📤 Export Attendance Data")
if st.button("Download CSV"):
    with open("attendance_export.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Subject", "Attended", "Missed", "Target %"])
        for subject, stats in data.items():
            writer.writerow([subject, stats['attended'], stats['missed'], stats['target']])
    with open("attendance_export.csv", "rb") as f:
        st.download_button("Download CSV", f, file_name="attendance_data.csv")

# Upload Timetable Image & Extract
st.markdown("---")
st.subheader("📷 Upload Timetable Image")
selected_group = st.selectbox("Select your group/section", ["24AML-102 GROUP A", "24AML-102 GROUP B", "24AML6-A"])
uploaded_image = st.file_uploader("Upload Timetable Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_image:
    with open(temp_image_path, "wb") as f:
        f.write(uploaded_image.getbuffer())
    st.image(temp_image_path, caption="Uploaded Image", use_column_width=True)

    extracted_text, error = extract_text_from_image_ocr_space(temp_image_path)
    if error:
        st.error(f"OCR failed: {error}")
    else:
        st.subheader("📝 Extracted Text")
        st.code(extracted_text)
        match_keyword = selected_group.split()[-1]  # A or B
        if f" {match_keyword}" not in extracted_text:
            st.warning(f"Could not find '{match_keyword}' in text. Check your image.")
        else:
            st.success(f"'{match_keyword}' found in image text.")
            # TODO: You can implement automated timetable parsing logic here
