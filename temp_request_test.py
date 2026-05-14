import requests

try:
    r = requests.post('http://127.0.0.1:5000/register', json={'username': 'kami', 'password': 'test112', 'role': 'patient'})
    print('status', r.status_code)
    print(r.text)
except Exception as e:
    print('error', e)
