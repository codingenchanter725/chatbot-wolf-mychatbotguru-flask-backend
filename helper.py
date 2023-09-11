import openai
import os
from dotenv import load_dotenv
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