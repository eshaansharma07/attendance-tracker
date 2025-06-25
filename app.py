import streamlit as st
import json
import os
from datetime import date
import requests
from PIL import Image
import io
import re

# ---------- CONFIG ---------- #
st.set_page_config(page_title="Smart Attendance Tracker", layout="wide")
DATA_FILE = "data.json"
TIMETABLE_FILE = "timetable.json"
OCR_API_KEY = "K81789618588957"

# ---------- INIT ---------- #
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

def extract_text_from_image(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()
    url = "https://api.ocr.space/parse/image"
    headers = {"apikey": OCR_API_KEY}
    response = requests.post(url, files={"filename": image_bytes}, data={"language": "eng"}, headers=headers)
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        return "Error: " + result.get("ErrorMessage", ["Unknown error"])[0]
    return result["ParsedResults"][0]["ParsedText"]

def calculate_attendance(subject_data):
    attended = subject_data["attended"]
    missed = subject_data["missed"]
    total = attended + missed
    target = subject_data["target"]
    if total == 0:
        return f"🔘 Attendance: 0% | 🎯 Target: {target}%"
    percentage = (attended / total) * 100
    status = f"✅ {percentage:.1f}%" if percentage >= target else f"⚠️ {percentage:.1f}%"
    return f"{status} | 🎯 {target}%"

def prediction_text(attended, missed, target):
    total = attended + missed
    if total == 0:
        return "🔹 Not enough data for prediction."
    current = (attended / total) * 100
    if current < target:
        needed = ((target * total) - (100 * attended)) / (100 - target)
        return f"🔺 You must attend next {int(needed) + 1} class(es) to reach {target}%."
    else:
        can_miss = (attended * 100 - target * total) / target
        return f"🟢 You can miss {int(can_miss)} more class(es) without falling below {target}%."

def export_csv(data):
    import pandas as pd
    rows = []
    for subject, stats in data.items():
        percentage = 0 if (stats["attended"] + stats["missed"]) == 0 else (stats["attended"] / (stats["attended"] + stats["missed"])) * 100
        rows.append({
            "Subject": subject,
            "Attended": stats["attended"],
            "Missed": stats["missed"],
            "Attendance (%)": round(percentage, 2),
            "Target (%)": stats["target"]
        })
    return pd.DataFrame(rows).to_csv(index=False).encode('utf-8')

# ---------- MAIN ---------- #
st.title("📈 Smart Attendance Tracker with AI Skip Prediction")
data = load_data()
timetable = load_timetable()
today = date.today().strftime("%A")

# ---------- SIDEBAR ---------- #
st.sidebar.header("➕ Add Subject")
subject_name = st.sidebar.text_input("Subject name")
target = st.sidebar.slider("Minimum Attendance %", 50, 100, 75)

if st.sidebar.button("Add Subject") and subject_name:
    if subject_name not in data:
        data[subject_name] = {"attended": 0, "missed": 0, "target": target, "history": []}
        save_data(data)
        st.sidebar.success(f"Added {subject_name}")
    else:
        st.sidebar.warning("Subject already exists!")

st.sidebar.header("➖ Remove Subject")
to_remove = st.sidebar.selectbox("Select to remove", list(data.keys()) or [""])
if st.sidebar.button("Remove Subject") and to_remove in data:
    del data[to_remove]
    save_data(data)
    st.sidebar.success(f"Removed {to_remove}")

st.sidebar.header("🗓️ Timetable Editor")
selected_day = st.sidebar.selectbox("Select Day", list(timetable.keys()))
new_subject = st.sidebar.text_input("Add subject to " + selected_day)
if st.sidebar.button("Add to Timetable") and new_subject:
    if new_subject not in timetable[selected_day]:
        timetable[selected_day].append(new_subject)
        save_timetable(timetable)
        st.sidebar.success("Added to timetable!")

# ---------- TODAY'S SCHEDULE ---------- #
st.subheader(f"📅 Today is: {today}")
today_subjects = timetable.get(today, [])

if not today_subjects:
    st.info("No subjects scheduled for today.")
else:
    for subject in today_subjects:
        if subject not in data:
            st.warning(f"Subject '{subject}' not in your subjects list.")
            continue

        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            st.markdown(f"**{subject}** — {calculate_attendance(data[subject])}")
        with col2:
            if st.button(f"✅ Present {subject}"):
                data[subject]["attended"] += 1
                data[subject]["history"].append((str(date.today()), "Present"))
                save_data(data)
                st.rerun()
        with col3:
            if st.button(f"❌ Absent {subject}"):
                data[subject]["missed"] += 1
                data[subject]["history"].append((str(date.today()), "Absent"))
                save_data(data)
                st.rerun()

        st.caption(prediction_text(data[subject]["attended"], data[subject]["missed"], data[subject]["target"]))
        st.markdown("---")

# ---------- EXPORT ---------- #
st.subheader("📤 Export Attendance Data")
st.download_button("Download CSV", data=export_csv(data), file_name="attendance.csv", mime="text/csv")

# ---------- IMAGE UPLOAD FOR TIMETABLE ---------- #
st.subheader("📷 Upload Timetable Image (A/B Sections Only)")
section = st.selectbox("Select your group/section", ["A", "B"])
uploaded = st.file_uploader("Upload timetable image (with selected group visible)", type=["jpg", "jpeg", "png"])

if uploaded and section:
    img = Image.open(uploaded)
    st.image(img, caption="Uploaded Image", use_column_width=True)

    extracted_text = extract_text_from_image(img)
    if not extracted_text.strip():
        st.error("OCR failed or returned empty text. Please try a clearer image.")
    else:
        st.text_area("🧾 Extracted Text", extracted_text, height=250)

        match_text = f" {section} "
        if match_text not in extracted_text:
            st.warning(f"Could not find section '{section}' in text. Check your image.")
        else:
            # Extract text starting from section
            group_text = extracted_text.split(match_text, 1)[1]
            st.markdown(f"### 📋 Parsed Timetable for: Group {section}")

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            parsed = {day: [] for day in days}
            for line in group_text.splitlines():
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
