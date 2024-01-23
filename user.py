import requests

url = "http://139.177.184.155:8000/api/screenshot/bulk"

data = {
    'urls' : ['www.facebook.com', 'www.example1.com', 'www.instagram.com', 'www.example.com']
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())