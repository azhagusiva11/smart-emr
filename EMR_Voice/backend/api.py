# backend/api.py
import os
import json
import tempfile
import fitz  # PyMuPDF
import openai

# Load full rare disease symptom matrix from file
json_path = os.path.join(os.path.dirname(__file__), "../data/rare_disease_matrix.json")
with open(json_path, "r", encoding="utf-8") as f:
    rare_disease_matrix = json.load(f)

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def register_patient(name, age, sex, mobile):
    pid = f"PID{str(abs(hash(name + mobile)))[0:8]}"
    patient = {
        "patient_id": pid,
        "name": name,
        "age": age,
        "sex": sex,
        "mobile": mobile,
        "visits": {}
    }
    os.makedirs("data/patients", exist_ok=True)
    with open(f"data/patients/{pid}.json", "w") as f:
        json.dump(patient, f)
    return pid

def create_visit_entry(patient_id, visit_type):
    visit_id = f"VISIT{str(abs(hash(patient_id + visit_type)))[0:8]}"
    file_path = f"data/patients/{patient_id}.json"
    with open(file_path) as f:
        patient = json.load(f)
    patient["visits"][visit_id] = {"visit_type": visit_type, "entries": []}
    with open(file_path, "w") as f:
        json.dump(patient, f)
    return visit_id

def get_all_patients():
    patients = []
    for file in os.listdir("data/patients"):
        if file.endswith(".json"):
            with open(os.path.join("data/patients", file)) as f:
                patient = json.load(f)
                patients.append(patient)
    return patients

def transcribe_audio(audio_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name
    audio_file.seek(0)
    transcript = openai.audio.transcriptions.create(
        model="whisper-1",
        file=open(tmp_path, "rb")
    )
    return transcript.text

def extract_text_from_pdf(lab_file):
    if lab_file is None:
        return ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(lab_file.read())
        tmp_path = tmp.name
    doc = fitz.open(tmp_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

def detect_rare_disease_with_gpt_match(transcript, gpt_summary):
    matched = []
    lowered = transcript.lower() + " " + gpt_summary.lower()
    for disease, symptoms in rare_disease_matrix.items():
        symptom_count = sum(1 for sym in symptoms if sym.lower() in lowered)
        name_found = disease.lower() in lowered
        if symptom_count >= 3 or name_found:
            matched.append(f"{disease} (matched {symptom_count} symptoms)")
    return ", ".join(matched) if matched else None

def summarize_case(notes, lab_file=None):
    lab_text = extract_text_from_pdf(lab_file)
    full_input = f"Clinical Notes: {notes}\n\nLab Report: {lab_text}"

    prompt = f"""
You are MedHelperBot, assisting an internal medicine resident. Use evidence-based references (UpToDate, Harrison’s) and structure your answer clearly.

Patient Case:
{full_input}

---
Format your response as:

**Definition & Key Concerns**
Brief summary of what the case likely represents

**Differential Diagnosis**
Ranked DDx (most to least likely) with reasoning

**Can’t-Miss Diagnosis**
Critical high-risk condition that must be ruled out

**Suggested Investigations**
Tests needed next for confirmation

**Management Plan**
Evidence-based first steps (include drug names/doses if relevant)

**Reference Insight**
Mention relevant guidelines or data (e.g., UTD 2023)
---
    """

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    summary = response.choices[0].message.content.strip()
    red_flags = detect_rare_disease_with_gpt_match(full_input, summary)
    return summary, red_flags

def save_emr_entry(patient_id, visit_id, entry):
    path = f"data/patients/{patient_id}.json"
    with open(path) as f:
        patient = json.load(f)
    patient["visits"][visit_id]["entries"].append(entry)
    with open(path, "w") as f:
        json.dump(patient, f, indent=2)
