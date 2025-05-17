# app.py
import streamlit as st
from backend.api import (
    register_patient, create_visit_entry, transcribe_audio,
    summarize_case, save_emr_entry, get_all_patients
)
from utils.export_tools import generate_emr_pdf
import json
import os
import time

st.set_page_config(page_title="Smart EMR", layout="centered")
st.title("🩺 AI-Enabled EMR System")

# Tabs
tabs = ["Register Patient", "Start Visit & Consultation"]
selected_tab = st.sidebar.radio("Navigation", tabs)

if selected_tab == "Register Patient":
    st.header("Patient Registration")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0, max_value=120)
    sex = st.selectbox("Sex", ["Male", "Female", "Other"])
    mobile = st.text_input("Mobile Number")
    if st.button("Register"):
        pid = register_patient(name, age, sex, mobile)
        st.success(f"✅ Patient Registered with ID: {pid}")

elif selected_tab == "Start Visit & Consultation":
    st.header("Doctor Consultation")

    patients = get_all_patients()
    patient_choices = [f"{p['name']} ({p['patient_id']})" for p in patients]
    selected_patient = st.selectbox("Select Patient", patient_choices)
    patient_id = selected_patient.split("(")[-1].replace(")", "")

    visit_type = st.selectbox("Visit Type", ["OPD", "Inpatient", "Follow-up"])

    if st.button("Start Visit"):
        visit_id = create_visit_entry(patient_id, visit_type)
        st.session_state["visit_id"] = visit_id
        st.session_state["patient_id"] = patient_id
        st.success(f"🔹 Visit Started: {visit_id}")

    if "visit_id" in st.session_state:
        st.subheader("Upload Consultation Data")
        audio_file = st.file_uploader("Upload .wav Audio (optional)", type=["wav"])
        lab_file = st.file_uploader("Upload Lab Report PDF (optional)", type=["pdf"])
        manual_input = st.text_area("Or type your consultation notes manually")
        prescription = st.text_area("Prescription (optional)")

        if st.button("🧠 Process Consultation"):
            start_time = time.time()

            transcript = ""
            if audio_file is not None:
                transcript = transcribe_audio(audio_file)
            elif manual_input:
                transcript = manual_input
            else:
                st.warning("❗ Please provide audio or manual input.")

            if transcript:
                summary, red_flags = summarize_case(transcript, lab_file)
                elapsed = time.time() - start_time

                st.success("✅ AI Summary Generated")
                st.markdown(f"🕒 Generated in {elapsed:.2f} seconds")
                st.markdown("### Clinical Reasoning Summary")
                st.write(summary)

                if red_flags:
                    alert_text = ", ".join([str(d) for d in red_flags]) if isinstance(red_flags, list) else str(red_flags)
                    st.error(f"🚨 Rare Disease Triggered:\n{alert_text}")
                else:
                    st.info("No rare disease alerts triggered.")

                st.markdown("### 👨‍⚕️ Was this summary helpful?")
                feedback = st.radio("Feedback", ["👍 Yes", "👎 No"])

                # Save and Export
                patient_file = f"data/patients/{st.session_state['patient_id']}.json"
                with open(patient_file) as f:
                    patient_data = json.load(f)

                emr_entry = {
                    "timestamp": st.session_state.get("visit_id"),
                    "summary": summary,
                    "red_flags": red_flags,
                    "prescription": prescription,
                    "feedback": feedback
                }

                save_emr_entry(st.session_state['patient_id'], st.session_state['visit_id'], emr_entry)
                pdf_path = generate_emr_pdf(
                    patient_data,
                    st.session_state['visit_id'],
                    summary,
                    red_flags,
                    prescription
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "📄 Download EMR Summary (PDF)",
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )
