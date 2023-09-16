import openai
import os
import string
from dotenv import load_dotenv
import PyPDF2
import pandas as pd
import docx
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')


def generate_response_35(prompt):
    """
    This function response the message using chatgpt 3.5

    Parameters:
    prompt (list): The prompt for users and system

    Returns:
    string: the answer based on the given prompt
    """
    openai.organization = os.getenv('OPENAI_ORGANIZATION')
    model_engine = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=model_engine,
        messages=prompt,
        temperature=0.5
    )
    message = response.choices[0].message.content.strip()
    return message


def generate_response_4(prompt):
    openai.organization = os.getenv('OPENAI_ORGANIZATION')
    model_engine = "gpt-4"
    print(model_engine)
    response = openai.ChatCompletion.create(
        model=model_engine,
        messages=prompt,
        temperature=0.5
    )
    message = response.choices[0].message.content.strip()
    return message


def read_text_from_txt(file_path):
    with open(file_path, 'r') as file:
        text = file.read()

    return text


def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)

        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()

    return text


def extract_text_from_excel(file_path):
    df = pd.read_excel(file_path)
    text = df.to_string(index=False)

    return text


def extract_text_from_docx(file_path):
    text = ""
    doc = docx.Document(file_path)

    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"

    return text


def convert_file_to_text(file_path, type):
    print("convert_file_to_text", type)
    if type == 'doc':
        return 'doc'
    if type == 'docx':
        return extract_text_from_docx(file_path)
    elif type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif type == 'txt':
        return read_text_from_txt(file_path)
    elif type == 'excel':
        return extract_text_from_excel(file_path)
    else:
        return "other text"
