import random
import string
import time

def generate_unique_filename():
    timestamp = str(int(time.time() * 1000))  # Get the current timestamp in milliseconds
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))  # Generate a random string of length 16
    unique_filename = timestamp + random_string
    return unique_filename

def get_short_type_from_real_type(type):
    print("get_short_type_from_real_type", type)
    if type == 'text/plain': return 'txt'
    elif type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': return 'docx'
    elif type == 'application/msword': return 'doc'
    elif type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': return 'excel'
    elif type == 'application/pdf': return 'pdf'
    else: return 'other'

def split_string(string, max_length):
    return [string[i:i+max_length] for i in range(0, len(string), max_length)]


def optimize_string(script_tokens, batch_size):
    return split_string(script_tokens, batch_size)
    # prompt_arr = []
    # for i in range(0, len(script_tokens), batch_size):
    #     if i < batch_size:
    #         before_context = ""
    #     else:
    #         before_context = " ".join(script_tokens[i-batch_size:i])
    #     text_to_edit = " ".join(script_tokens[i:i+batch_size])
    #     if i+batch_size*2 >= len(script_tokens):
    #         after_context = ""
    #     else:
    #         after_context = " ".join(script_tokens[i+batch_size:i+batch_size*2])
        
    #     prompt = f"Please proofread, rewrite, and improve of the following text inside the brackets (in the context that it is a description script for a https://afrilabsgathering.com/), considering the context given before and after it: before:\"{before_context}\" text to edit:{text_to_edit} after:\"{after_context}\" []"
    #     prompt_arr.append(prompt)
        
    # return prompt_arr