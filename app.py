import os
import re
import json
import smtplib
from email.message import EmailMessage
from html import escape

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from google import genai

load_dotenv()

def get_setting(name, default=None):
    try:
        return st.secrets.get(name) or os.getenv(name, default)
    except Exception:
        return os.getenv(name, default)


GEMINI_API_KEY = get_setting("GEMINI_API_KEY")
SMTP_HOST = get_setting("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_setting("SMTP_PORT", 587))
SMTP_USER = get_setting("SMTP_USER")
SMTP_PASSWORD = get_setting("SMTP_PASSWORD")
SMTP_FROM = get_setting("SMTP_FROM", SMTP_USER)

client = genai.Client(api_key=GEMINI_API_KEY)


def extract_email(text):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    emails = re.findall(pattern, text)

    excluded_domains = {
        "example.com",
        "example.org",
        "example.net"
    }

    emails = [
        email for email in emails
        if email.lower().split("@")[-1] not in excluded_domains
    ]

    return emails[0] if emails else None


def extract_resume_text(pdf_file):
    reader = PdfReader(pdf_file)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)


def generate_email(job_post, resume_text):

    prompt = f"""
You are helping a candidate apply for a job.

Analyze the following LinkedIn job post and candidate resume.

JOB POST:
{job_post}

CANDIDATE RESUME:
{resume_text}

Generate a personalized job application email.

Rules:

1. Identify the actual job title from the job post.
2. Identify the company name if available.
3. Identify important skills and requirements from the job post.
4. Match those requirements only with information explicitly present in the resume.
5. Never invent skills, experience, projects, certifications, technologies,
   achievements, responsibilities, or years of experience.
6. If the job requires 1+ years of experience and the resume does not support
   that experience, do not falsely claim it.
7. Highlight relevant projects, education, skills, certifications, or experience
   that are actually present in the resume.
8. Keep the email concise and professional.
9. Mention that the resume is attached.
10. Do not use placeholders such as [Recruiter Name].
11. Do not invent a recruiter's name.
12. Do not mention that AI generated the email.
13. Make the email specifically relevant to this job post.
14. Do not create a generic application template.

Return ONLY valid JSON.

Required format:

{{
    "subject": "email subject",
    "body": "email body"
}}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    result = response.text.strip()

    result = re.sub(r"^```json\s*", "", result)
    result = re.sub(r"\s*```$", "", result)

    return json.loads(result)


def send_email(recipient, subject, text_body, pdf_file):

    message = EmailMessage()

    message["From"] = SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(text_body)

    html_body = "<html><body>"
    html_body += "<br>".join(
        escape(line) for line in text_body.splitlines()
    )
    html_body += "</body></html>"
    message.add_alternative(html_body, subtype="html")

    pdf_bytes = pdf_file.getvalue()

    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=pdf_file.name
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:

        server.starttls()

        server.login(
            SMTP_USER,
            SMTP_PASSWORD
        )

        server.send_message(message)


st.set_page_config(
    page_title="AI Job Application Assistant",
    page_icon="📩",
    layout="wide"
)

st.title("📩 AI Job Application Assistant")

st.write(
    "Paste a LinkedIn job post and upload your PDF resume "
    "to generate a personalized application email."
)

linkedin_post = st.text_area(
    "LinkedIn Job Post",
    height=350,
    placeholder="Paste the complete LinkedIn job post here..."
)

resume_file = st.file_uploader(
    "Upload PDF Resume",
    type=["pdf"]
)


if st.button(
    "Generate Application Email",
    type="primary"
):

    if not linkedin_post.strip():

        st.error("Please paste the LinkedIn job post.")

    elif resume_file is None:

        st.error("Please upload your PDF resume.")

    elif not GEMINI_API_KEY:

        st.error("GEMINI_API_KEY is missing.")

    else:

        with st.spinner("Analyzing job post and resume..."):

            recipient_email = extract_email(
                linkedin_post
            )

            if not recipient_email:

                st.error(
                    "No valid email address was found in the LinkedIn post."
                )

                st.stop()

            resume_text = extract_resume_text(
                resume_file
            )

            if not resume_text.strip():

                st.error(
                    "Could not extract text from the PDF resume."
                )

                st.stop()

            try:

                generated = generate_email(
                    linkedin_post,
                    resume_text
                )

                st.session_state.recipient_email = (
                    recipient_email
                )

                st.session_state.subject = (
                    generated["subject"]
                )

                st.session_state.body = (
                    generated["body"]
                )

                st.session_state.generated = True

            except Exception as e:

                st.error(
                    f"Gemini generation failed: {e}"
                )


if st.session_state.get("generated"):

    st.divider()

    st.subheader("Application Preview")

    st.success(
        f"Recruiter email detected: "
        f"{st.session_state.recipient_email}"
    )

    subject = st.text_input(
        "Email Subject",
        value=st.session_state.subject
    )

    body = st.text_area(
        "Email Body",
        value=st.session_state.body,
        height=350
    )

    st.info(
        f"Attachment: {resume_file.name}"
    )

    if st.button(
        "Send Application Email",
        type="primary"
    ):

        if not SMTP_USER:

            st.error(
                "SMTP_USER is missing."
            )

        elif not SMTP_PASSWORD:

            st.error(
                "SMTP_PASSWORD is missing."
            )

        else:

            try:

                with st.spinner("Sending email..."):

                    send_email(
                        recipient=st.session_state.recipient_email,
                        subject=subject,
                        text_body=body,
                        pdf_file=resume_file
                    )

                st.success(
                    f"Application email sent successfully to "
                    f"{st.session_state.recipient_email}"
                )

            except Exception as e:

                st.error(
                    f"Failed to send email: {e}"
                )