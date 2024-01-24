import requests

url = "http://localhost:8000/api/bulk/screenshots"

data = {
    'urls' : ['www.facebook.com', 'www.example1.com', 'www.instagram.com', 'www.example.com']
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())