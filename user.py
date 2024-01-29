import requests

url = "http://localhost:8000/api/screenshots"

data = {
    'urls' : ['https://www.facebook.com/login','https://www.messenger.com/', 'www.example.com', 'example1.com', 'www.instagram.com', 'www.youtube.com']
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())