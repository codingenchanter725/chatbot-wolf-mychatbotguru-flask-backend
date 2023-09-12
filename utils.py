import random
import string
import time

def generate_unique_filename():
    timestamp = str(int(time.time() * 1000))  # Get the current timestamp in milliseconds
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))  # Generate a random string of length 16
    unique_filename = timestamp + random_string
    return unique_filename

def getS_short_type_from_real_type(type):
    print("getS_short_type_from_real_type", type)
    if type == 'text/plain': return 'txt'
    elif type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': return 'docx'
    elif type == 'application/msword': return 'doc'
    elif type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': return 'excel'
    elif type == 'application/pdf': return 'pdf'
    else: return 'other'

def split_string(string, max_length):
    return [string[i:i+max_length] for i in range(0, len(string), max_length)]
