from playwright.async_api import async_playwright
import os
import hashlib
from urllib.parse import urlparse, urljoin
from app.shot_scraper import get_screenshot_and_html


def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

async def initialize_browser():
    global browser_instance
    p = await async_playwright().start()
    browser_instance = await p.chromium.launch()


async def get_browser():
    global browser_instance
    if browser_instance is None:
        await initialize_browser()
    return browser_instance





def get_hash(url):
    hash_object = hashlib.sha256()
    hash_object.update(url.encode("utf-8"))
    hashed_string = hash_object.hexdigest()
    return hashed_string[:16]


def clean_url(url):
    url = url.rstrip('/')
    url = url.split('www.')[-1] if 'www.' in url else url
    url = url.replace('https://','').replace('http://','')
    return url

def check_bad_url(redis, url):
    url_bad_return_count = redis.hget("black_list", url)
    if not url_bad_return_count:
        return False
    url_bad_return_count = int(url_bad_return_count.decode("utf-8"))
    if url_bad_return_count < 4:
        return False
    return True

def redirected_url(redis, url):
    redirected_url = redis.hget('redirected_urls',url)
    if redirected_url is not None:
        url = redirected_url.decode('utf-8')
    return url

    
def get_path(resources_dir,name, html=False):
    resources_dir = os.path.abspath("./static/resources")
    ensure_directory_exists(resources_dir)
    if html:
        return  os.path.join(resources_dir, f"{name}.html")
    return os.path.join(resources_dir, f"{name}.png")

def get_download_url(req, url):
    return req.base_url.replace(path=f"api/download/{url}")