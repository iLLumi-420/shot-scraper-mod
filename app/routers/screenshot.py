from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Path
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot
import os
from contextlib import asynccontextmanager
from typing import List
from redis import Redis
import hashlib
from pydantic import BaseModel

class ScreenshotsRequest(BaseModel):
    urls: List[str]

class ScreenshotsResponse(BaseModel):
    results: List[dict]

class StatusResponse(BaseModel):
    msg: str
    download_url: str = None
   

redis = Redis(host="localhost", port="6379", db=0)

screenshots_dir = os.path.abspath("./static/screenshots")
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


async def take_screenshot(url):
    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    name = get_hash(url)
    shot = {"url": url, "output":f"./static/screenshots/{name}.png"}

    try:
        redis.set(url, 1)
        response = await take_shot(shot=shot, context_or_page=context, fail=True)
        redis.delete(url)
        await context.close()
        return response
    
    except Exception as e:
        print("Error in taking shot for url",url, e)
        if redis.hexists("black_list", url):
            redis.hincrby("black_list", url, 1)
        else:
            redis.hset("black_list", url, 1)
        return 
      

async def process_screenshots(req,urls: List[str], background_task=BackgroundTasks):
    results = []
    for url in urls:
        
        url = clean_url(url)
        name = get_hash(url)

        screenshot_path = os.path.join(screenshots_dir, f"{name}.png")
        download_url = req.base_url.replace(path=f"api/download/{url}")

        if os.path.exists(screenshot_path):
            results.append({url: f'{download_url}'})
            continue

        is_bad_url = check_bad_url(url)
        if is_bad_url:
            results.append({url: 'Bad url'})
            continue

        background_task.add_task(take_screenshot, url)
        results.append({url: f'{download_url}'})

    return {"results": results}


@router.post("/screenshots", response_model=ScreenshotsResponse)
async def bluk_screenshot(request: ScreenshotsRequest, background_task: BackgroundTasks, req:Request):

    urls = request.urls

    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")
    
    results = await process_screenshots(req, urls, background_task)

    return results


@router.get("/download/{url:path}")
def download_screenshot(url: str = Path(..., description="URL")):

    url = clean_url(url)
    name = get_hash(url)
    screenshot_path = os.path.join(screenshots_dir, f"{name}.png")

    if os.path.exists(screenshot_path):
        return FileResponse(
            path=screenshot_path,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={name}.png",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    else:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    

@router.get("/status/{url:path}", response_model=StatusResponse)
def check_status(req: Request,url: str = Path(..., description="URL")):

    status = redis.get(url)
    if status:
        return {"msg": "URL is being processed"}

    url = clean_url(url)
    name = get_hash(url)

    screenshot_path = os.path.join(screenshots_dir, f"{name}.png")
    download_url = req.base_url.replace(path=f"api/download/{url}")

    if not os.path.exists(screenshot_path):
        return {"msg": "URL has never been processed"}
        
    return {
            "msg": f"Screenshot for URL:{url} has already been taken",
            "download_url": f"{download_url}"
        }
        
    
        