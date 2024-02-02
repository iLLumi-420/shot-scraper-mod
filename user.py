import requests

url = "http://localhost:8000/api/screenshots"

data = {
    'urls' : [
    "www.wikipedia.org",
    "https://www.google.com",
    "https://www.facebook.com",
    "https://www.twitter.com",
    "https://www.instagram.com",
    "setopati.org",
    "https://www.linkedin.com",
    "https://www.reddit.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.apple.com",
    ]
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())