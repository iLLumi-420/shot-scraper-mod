import requests

url = "http://localhost:8000/api/screenshots"

data = {
    'urls' : ['https://www.facebook.com','https://www.messenger.com/','https://lichess.org']
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())