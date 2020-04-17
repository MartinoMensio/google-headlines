import json
import shutil
import datetime

def get_today():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def get_time():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

def save_json(file_path, content):
    with open(file_path, 'w') as f:
        json.dump(content, f, indent=2)

def read_json(file_path):
    with open(file_path) as f:
        return json.load(f)

def clean():
    print('cleaning tmp files...')
    shutil.rmtree('data/tmp')