import requests

url = "http://localhost:8000/api/save"

data = {
    'urls' : [
    "https://www.wikipedia.org",
    "https://www.google.com",
    "https://www.facebook.com",
    "https://www.twitter.com",
    "https://www.instagram.com",
    "https://www.linkedin.com",
    "https://www.reddit.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.apple.com",
    "https://www.microsoft.com",
    "https://www.amazon.com",
    "https://www.netflix.com",
    "https://www.youtube.com",
    "https://www.spotify.com",
    "https://www.nytimes.com",
    "https://www.bbc.com",
    "https://www.cnn.com",
    "https://www.nike.com",
    "https://www.adidas.com",
    "https://www.etsy.com",
    "https://www.airbnb.com",
    "https://www.tripadvisor.com",
    "https://www.weather.com",
    "https://www.nationalgeographic.com",
    "https://www.nasa.gov",
    "https://www.imdb.com",
    "https://www.ebay.com",
    "https://www.paypal.com",
    "https://www.craigslist.org",
    # "https://www.twitch.tv",
    # "https://www.quora.com",
    # "https://www.pinterest.com",
    # "https://www.squarespace.com",
    # "https://www.wordpress.com",
    # "https://www.medium.com",
    # "https://www.ted.com",
    # "https://www.bloomberg.com",
    # "https://www.wsj.com",
    # "https://www.cnbc.com",
    # "https://www.economist.com",
    # "https://www.forbes.com",
    # "https://www.techcrunch.com",
    # "https://www.arstechnica.com",
    # "https://www.wired.com",
    # "https://www.engadget.com",
    # "https://www.buzzfeed.com",
    # "https://www.huffpost.com",
    # "https://www.cnet.com",
    # "https://www.espn.com"
]
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())