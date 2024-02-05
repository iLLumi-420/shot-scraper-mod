from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Path, Query
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
# from shot_scraper.cli import take_shot
import os
from contextlib import asynccontextmanager
from typing import List
from redis import Redis
import hashlib
from app.models import ScreenshotsRequest,StatusResponse
import requests
from urllib.parse import urlparse, urljoin
import asyncio
from app.shot_scraper import get_screenshot_and_html
from zipfile import ZipFile

redis = Redis(host="localhost", port="6379", db=0)


def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

resources_dir = os.path.abspath("./static/resources")
ensure_directory_exists(resources_dir)
browser_instance = None


@asynccontextmanager
def lifespan(app: APIRouter):
    initialize_browser()
    yield
    browser_instance.close()

router = APIRouter(lifespan=lifespan)


async def initialize_browser():
    global browser_instance
    p = await async_playwright().start()
    browser_instance = await p.chromium.launch()


async def get_browser():
    global browser_instance
    if browser_instance is None:
        await initialize_browser()
    return browser_instance


def check_bad_url(url):
    url_bad_return_count = redis.hget("black_list", url)
    if not url_bad_return_count:
        return False
    url_bad_return_count = int(url_bad_return_count.decode("utf-8"))
    if url_bad_return_count < 4:
        return False
    return True


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

def redirected_url(url):
    redirected_url = redis.hget('redirected_urls',url)
    if redirected_url is not None:
        url = redirected_url.decode('utf-8')
    return url

    
def get_path(name, html=False):
    if html:
        return  os.path.join(resources_dir, f"{name}.html")
    return os.path.join(resources_dir, f"{name}.png")

def get_download_url(req, url):
    return req.base_url.replace(path=f"api/download/{url}")

async def take_screenshot(url):

    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    shot = {"url": url}

    try:
        redis.set(url, 1)
        screenshot_bytes, response_url, response_html = await get_screenshot_and_html(context=context, shot=shot)
        await context.close()
        redis.delete(url)

        response_url = clean_url(response_url)
        if url != response_url:
            redis.hset('redirected_urls', url, response_url)
            print('redirected url saved', url, response_url)

        name = get_hash(response_url)
        screenshot_path = get_path(name)
        html_path = get_path(name, html=True)
        with open(screenshot_path, 'wb') as file:
            file.write(screenshot_bytes)
        with open(html_path, 'w') as file:
            file.write(response_html)
        
    
    except Exception as e:
        print("Error in taking shot for url",url, e)
        if redis.hexists("black_list", url):
            redis.hincrby("black_list", url, 1)
        else:
            redis.hset("black_list", url, 1)
        return {}


async def get_tasks_and_results(req, urls):
    tasks = []
    results = []
    for url in urls:
        url = clean_url(url)
        url = redirected_url(url)
        name = get_hash(url)

        screenshot_path = get_path(name)
        download_url = get_download_url(req, url)

        if os.path.exists(screenshot_path):
            results.append({url: f'{download_url}'})
            continue

        is_bad_url = check_bad_url(url)
        if is_bad_url:
            results.append({url: 'Bad url'})
            continue

        tasks.append(take_screenshot(url))
        results.append({url: f'{download_url}'})

    return tasks, results


async def process_task_chunks(tasks, urls_length):
    chunk_size = 5
    for i in range(0, urls_length, chunk_size):
        chunk_tasks = tasks[i:i+chunk_size]
        await asyncio.gather(*chunk_tasks)


@router.post("/screenshots")
async def bulk_screenshot(screenshot_request: ScreenshotsRequest, request: Request, background_task:BackgroundTasks):
    redis.hdel('black_list', 'reddit.com')
    urls = screenshot_request.urls

    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")

    tasks, results = await get_tasks_and_results(request, urls)
    
    background_task.add_task(process_task_chunks, tasks, len(urls))

    return {'results': results}



    

@router.get("/status/{url:path}", response_model=StatusResponse)
def check_status(req: Request,url: str = Path(..., description="URL")):

    url = clean_url(url)
    status = redis.get(url)
    if status:
        return {"msg": f"screenshot for url:{url} is being taken"}

    url = redirected_url(url)
    name = get_hash(url)

    screenshot_path = get_path(name)
    download_url = get_download_url(url)

    if not os.path.exists(screenshot_path):
        return {"msg": f"screenshot for url:{url} has not been taken"}
        
    return {
            "msg": f"Screenshot for url:{url} has been taken",
            "download_url": f"{download_url}"
        }
        
    
        