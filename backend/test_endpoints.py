import os
os.environ['PYTHONUNBUFFERED'] = '1'

import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.CRITICAL)
logging.getLogger('raycarwash').setLevel(logging.CRITICAL)

import uvicorn
from main import app
import threading
import time
import warnings
warnings.filterwarnings('ignore')

def run_server():
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='critical')

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(3)

import requests
print('=== Testing endpoints ===')

print('1. GET /health')
r = requests.get('http://127.0.0.1:8000/health')
print(f'   Status: {r.status_code}, Body: {r.json()}')

print('\n2. POST /api/v1/users (create user)')
r = requests.post('http://127.0.0.1:8000/api/v1/users', json={
    'email': 'testuser6@test.com',
    'password': 'Test1234!',
    'full_name': 'Test User',
    'role': 'client'
})
print(f'   Status: {r.status_code}')
try:
    print(f'   Body: {r.json()}')
except:
    print(f'   Body: {r.text[:300]}')

print('\n3. GET /api/v1/services')
r = requests.get('http://127.0.0.1:8000/api/v1/services')
print(f'   Status: {r.status_code}')
try:
    data = r.json()
    print(f'   Body: {len(data)} services found')
except:
    print(f'   Body: {r.text[:200]}')

print('\n4. POST /api/v1/auth/login (not found)')
r = requests.post('http://127.0.0.1:8000/api/v1/auth/login', json={'email':'test@test.com','password':'test'})
print(f'   Status: {r.status_code}, Body: {r.text[:200]}')

print('\n=== All tests complete ===')
