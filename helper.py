import openai
import os
import string
from dotenv import load_dotenv
# from langchain.document_loaders import UnstructuredPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from PyPDF2 import PdfReader
import pandas as pd
# from docx import Document
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


def read_text_from_txt(file_path):
    with open(file_path, 'r') as file:
        text = file.read()

    return text


# def convert_pdf_text(file_path):
#     if (os.path.exists(file_path)):
#         loader = UnstructuredPDFLoader(file_path)
#         data = loader.load()
#         splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000, chunk_overlap=0)
#         texts = splitter.split_documents(data)
#         res: string = ""
#         for text in texts:
#             res = res + text.page_content
#         return res
#     return ""


# def extract_text_from_pdf(file_path):
#     text = ""
#     with open(file_path, 'rb') as file:
#         pdf = PdfReader(file)
#         for page in pdf.pages:
#             text += page.extract_text()

#     return text


def extract_text_from_excel(file_path):
    df = pd.read_excel(file_path)
    text = df.to_string(index=False)

    return text


# def extract_text_from_docx(file_path):
#     doc = Document(file_path)
#     text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])

#     return text

def convert_file_to_text(file_path, type):
    print("convert_file_to_text", type)
    return "This is the text from the attachment"
    if type == 'doc':
        return 'doc'
    if type == 'docx':
        return 'docx'
    elif type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif type == 'txt':
        return read_text_from_txt(file_path)
    elif type == 'excel':
        return extract_text_from_excel(file_path)
    else:
        return "other text"
