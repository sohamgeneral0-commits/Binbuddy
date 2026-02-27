import requests
r=requests.post('http://127.0.0.1:5000/api/auth/login', json={'role':'citizen','id':'8888888888','password':'mypassword'})
print(r.status_code, r.text)
