import os
from datetime import datetime

import joblib
import pandas as pd
import streamlit as st


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="ML Phishing Email Detector",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ ML Phishing Email Detection + Security Dashboard")
st.write(
    "This app uses a machine learning model to classify email messages as "
    "**Legitimate** or **Phishing** and provides a basic cybersecurity risk explanation."
)


# -----------------------------
# Load model and vectorizer
# -----------------------------
@st.cache_resource
def load_model_files():
    model = joblib.load("phishing_model.pkl")
    vectorizer = joblib.load("tfidf_vectorizer.pkl")
    return model, vectorizer


model, vectorizer = load_model_files()


# -----------------------------
# Suspicious indicator detection
# -----------------------------
def detect_suspicious_indicators(email_text):
    email_text = email_text.lower()

    indicators = {
        "Urgent language": [
            "urgent",
            "immediate action",
            "final warning",
            "within 24 hours",
            "expires today"
        ],
        "Password or credential request": [
            "password",
            "credentials",
            "login details",
            "username"
        ],
        "Account threat": [
            "account locked",
            "account suspended",
            "account will be deleted",
            "account is on hold",
            "access will be disabled"
        ],
        "Suspicious link request": [
            "click here",
            "click this link",
            "login using the link",
            "link below"
        ],
        "Financial request": [
            "banking details",
            "billing information",
            "payment",
            "processing fee"
        ],
        "Prize or reward lure": [
            "won",
            "gift card",
            "free laptop",
            "claim your prize",
            "claim it"
        ],
        "Attachment risk": [
            "open the attachment",
            "secure document",
            "view details"
        ]
    }

    detected = []

    for category, keywords in indicators.items():
        for keyword in keywords:
            if keyword in email_text:
                detected.append(category)
                break

    return detected


# -----------------------------
# Prediction functions
# -----------------------------
def predict_email(email_text):
    email_tfidf = vectorizer.transform([email_text])
    prediction = model.predict(email_tfidf)[0]
    probability = model.predict_proba(email_tfidf)[0]
    confidence = max(probability) * 100

    label = "Phishing" if prediction == 1 else "Legitimate"

    return label, round(confidence, 2)


def assign_risk_level(prediction_label, confidence, indicators):
    indicator_count = len(indicators)

    if prediction_label == "Phishing" and confidence >= 70:
        return "High"
    elif prediction_label == "Phishing" and indicator_count >= 2:
        return "High"
    elif prediction_label == "Phishing":
        return "Medium"
    elif prediction_label == "Legitimate" and indicator_count >= 2:
        return "Medium"
    else:
        return "Low"


def analyze_email(email_text):
    prediction_label, confidence = predict_email(email_text)
    indicators = detect_suspicious_indicators(email_text)
    risk_level = assign_risk_level(prediction_label, confidence, indicators)

    return {
        "email_text": email_text,
        "prediction": prediction_label,
        "confidence": confidence,
        "suspicious_indicators": indicators,
        "risk_level": risk_level
    }


# -----------------------------
# Logging function
# -----------------------------
def log_prediction(analysis, log_file="prediction_logs.csv"):
    new_log = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "email_text": analysis["email_text"],
        "prediction": analysis["prediction"],
        "confidence": analysis["confidence"],
        "suspicious_indicators": ", ".join(analysis["suspicious_indicators"]),
        "risk_level": analysis["risk_level"]
    }])

    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        existing_logs = pd.read_csv(log_file)
        updated_logs = pd.concat([existing_logs, new_log], ignore_index=True)
    else:
        updated_logs = new_log

    updated_logs.to_csv(log_file, index=False)
    return updated_logs


# -----------------------------
# App interface
# -----------------------------
st.header("📩 Email Analysis")

email_input = st.text_area(
    "Paste an email message here:",
    height=180,
    placeholder="Example: Urgent! Your account has been locked. Click here to verify your password."
)

if st.button("Analyze Email"):
    if email_input.strip() == "":
        st.warning("Please enter an email message before analyzing.")
    else:
        analysis = analyze_email(email_input)
        logs = log_prediction(analysis)

        st.subheader("🔎 Analysis Result")

        col1, col2, col3 = st.columns(3)

        col1.metric("Prediction", analysis["prediction"])
        col2.metric("Confidence", f'{analysis["confidence"]}%')
        col3.metric("Risk Level", analysis["risk_level"])

        if analysis["prediction"] == "Phishing":
            st.error("This email is predicted as a phishing email.")
        else:
            st.success("This email is predicted as legitimate.")

        st.subheader("🚩 Suspicious Indicators")

        if analysis["suspicious_indicators"]:
            for indicator in analysis["suspicious_indicators"]:
                st.write(f"- {indicator}")
        else:
            st.write("No suspicious indicators detected.")

        st.subheader("📝 Analyst Note")

        if analysis["risk_level"] == "High":
            st.warning("High-risk email. Recommended action: do not click links, do not open attachments, and report to the security team.")
        elif analysis["risk_level"] == "Medium":
            st.info("Medium-risk email. Recommended action: review carefully before taking action.")
        else:
            st.success("Low-risk email. No major phishing indicators were detected.")


# -----------------------------
# Dashboard
# -----------------------------
st.divider()
st.header("📊 Security Dashboard")

if os.path.exists("prediction_logs.csv") and os.path.getsize("prediction_logs.csv") > 0:
    logs = pd.read_csv("prediction_logs.csv")

    total_emails = len(logs)
    phishing_count = len(logs[logs["prediction"] == "Phishing"])
    legitimate_count = len(logs[logs["prediction"] == "Legitimate"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Emails Analyzed", total_emails)
    col2.metric("Phishing Emails", phishing_count)
    col3.metric("Legitimate Emails", legitimate_count)

    st.subheader("Recent Prediction Logs")
    st.dataframe(logs.tail(10), use_container_width=True)

    st.subheader("Prediction Counts")
    st.bar_chart(logs["prediction"].value_counts())

    st.subheader("Risk Level Counts")
    st.bar_chart(logs["risk_level"].value_counts())

else:
    st.info("No prediction logs found yet. Analyze an email to generate dashboard data.")


# -----------------------------
# Dataset preview
# -----------------------------
st.divider()
st.header("📁 Dataset Preview")

if os.path.exists("phishing_dataset.csv"):
    dataset = pd.read_csv("phishing_dataset.csv")

    dataset["label_name"] = dataset["label"].map({
        0: "Legitimate",
        1: "Phishing"
    })

    st.write("Sample rows from the phishing email dataset:")
    st.dataframe(dataset[["email_text", "label_name"]].head(10), use_container_width=True)
else:
    st.warning("phishing_dataset.csv not found.")