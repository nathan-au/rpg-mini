import os

UPLOAD_DIR = "bucket" #define upload directory called bucket to store uploaded files
os.makedirs(UPLOAD_DIR, exist_ok=True) #if bucket does not exist, create bucket