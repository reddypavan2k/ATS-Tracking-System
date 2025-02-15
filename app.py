from dotenv import load_dotenv
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
import fitz  # PyMuPDF
import re

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(input, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input, pdf_content[0], prompt])
    return response.text

def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        images = pdf2image.convert_from_bytes(uploaded_file.read())
        first_page = images[0]
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            }
        ]
        return pdf_parts, first_page
    else:
        raise FileNotFoundError("No file uploaded")

def extract_keywords(response):
    # Use regex to find keywords in the response
    keyword_pattern = re.compile(r'Keywords missing:\s*(.+?)\s*Final thoughts:', re.DOTALL)
    match = keyword_pattern.search(response)
    if match:
        keywords_section = match.group(1).strip()
        keywords = [kw.strip() for kw in keywords_section.split(',')]
        return keywords
    else:
        st.error("The response does not contain the expected 'Keywords missing' section.")
        return []

def image_to_pdf(image, output_path):
    image.save(output_path, "PDF", resolution=100.0)

def edit_pdf(pdf_path, keywords):
    doc = fitz.open(pdf_path)
    page = doc[0]
    text_instances = page.search_for(" ")  # Find spaces to insert keywords

    for keyword in keywords:
        if text_instances:
            rect = text_instances.pop(0)
            page.insert_text(rect, keyword, fontsize=12, color=(0, 0, 0))

    edited_pdf_path = "edited_resume.pdf"
    doc.save(edited_pdf_path)
    doc.close()
    return edited_pdf_path

# Streamlit App
st.set_page_config(page_title="ATS Resume Expert")
st.header("ATS Tracking System")
input_text = st.text_area("Job Description: ", key="input")
uploaded_file = st.file_uploader("Upload your resume(PDF)...", type=["pdf"])

if uploaded_file is not None:
    st.write("PDF Uploaded Successfully")

submit1 = st.button("Tell Me About the Resume")
submit3 = st.button("Percentage match")
submit4 = st.button("Edit Resume with Missing Keywords")

input_prompt1 = """
You are an experienced Technical Human Resource Manager, your task is to review the provided resume against the job description.
Please share your professional evaluation on whether the candidate's profile aligns with the role.
Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
"""

input_prompt3 = """
You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding of data science and ATS functionality,
your task is to evaluate the resume against the provided job description. Give me the percentage of match if the resume matches
the job description. First the output should come as percentage and then keywords missing and last final thoughts.
"""

if submit1:
    if uploaded_file is not None:
        pdf_content, first_page = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt1, pdf_content, input_text)
        st.subheader("The Response is")
        st.write(response)
    else:
        st.write("Please upload the resume")

elif submit3:
    if uploaded_file is not None:
        pdf_content, first_page = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt3, pdf_content, input_text)
        st.subheader("The Response is")
        st.write(response)
    else:
        st.write("Please upload the resume")

elif submit4:
    if uploaded_file is not None:
        pdf_content, first_page = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt3, pdf_content, input_text)
        st.subheader("The Response is")
        st.write(response)

        # Extract missing keywords from the response
        keywords = extract_keywords(response)

        if keywords:
            # Save the uploaded PDF to a temporary file
            with open("uploaded_resume.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Convert the first page image back to PDF
            image_to_pdf(first_page, "temp_resume.pdf")

            # Edit the PDF with the missing keywords
            edited_pdf_path = edit_pdf("temp_resume.pdf", keywords)

            # Provide a download link for the edited PDF
            with open(edited_pdf_path, "rb") as f:
                st.download_button(label="Download Edited Resume", data=f, file_name="edited_resume.pdf")
        else:
            st.write("No keywords found to add to the resume.")
    else:
        st.write("Please upload the resume")
