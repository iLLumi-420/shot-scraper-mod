import requests

url = "http://localhost:8000/api/screenshots"

data = {
    'urls' : ['setopati.org','https://lichess.org']
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())