from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Path
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot
import os
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
from redis import Redis
import hashlib


class ScreenshotRequest(BaseModel):
    urls: List[str]

redis = Redis(host='localhost', port='6379', db=0)

screenshots_dir = os.path.abspath('./static/screenshots')
browser_instance = None


@asynccontextmanager
def lifespan(app: APIRouter):
    initialize_browser()
    yield
    browser_instance.close()

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
    url_bad_return_count = int(url_bad_return_count.decode('utf-8'))
    if url_bad_return_count < 4:
        return False
    return True

def get_hash(url):
    hash_object = hashlib.sha256()

    hash_object.update(url.encode('utf-8'))

    hashed_string = hash_object.hexdigest()

    return hashed_string[:16]



router = APIRouter(lifespan=lifespan)


async def take_screenshot(url):
    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    name = get_hash(url)

    shot = {'url': url, 'output':f'./static/screenshots/{name}.png'}

    try:
        redis.set(url, 1)
        response = await take_shot(shot=shot, context_or_page=context, fail=True)
        redis.delete(url)
        await context.close()
        return response
    
    except Exception as e:
        print('Error in taking shot for url',url, e)
        if redis.hexists("black_list", url):
            redis.hincrby("black_list", url, 1)
        else:
            redis.hset("black_list", url, 1)
        return 
      

async def process_screenshots(req,urls: List[str], background_task=BackgroundTasks):
    results = []
    for url in urls:

        name = get_hash(url)

        screenshot_path = os.path.join(screenshots_dir, f'{name}.png')
        download_url = req.base_url.replace(path=f"api/download/{url}")

        if os.path.exists(screenshot_path):
            results.append({"msg": f'screen shot for url: {url} has already been taken', 'download_url': f'{download_url}'})
            continue

        is_bad_url = check_bad_url(url)
        if is_bad_url:
            results.append({'msg': f'The url:{url} will contionously gives error and will not be tried anymore'})
            continue

        background_task.add_task(take_screenshot, url)
        results.append({"msg":f'screenshot for url {url} is being taken', "download_info":f"After completion you can download it from {download_url}"})

    return results

@router.post('/screenshots')
async def bluk_screenshot(request: ScreenshotRequest, background_task: BackgroundTasks, req:Request):

    urls = request.urls

    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")
    
    results = await process_screenshots(req, urls, background_task)

    return results



@router.get('/download/{url:path}')
def download_screenshot(url: str = Path(..., description="URL")):

    name = get_hash(url)
    screenshot_path = os.path.join(screenshots_dir, f'{name}.png')

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

@router.get('/status/{url:path}')
def check_status(req: Request,url: str = Path(..., description="URL")):

    status = redis.get(url)

    name = get_hash(url)

    screenshot_path = os.path.join(screenshots_dir, f'{name}.png')
    download_url = req.base_url.replace(path=f"api/download/{url}")

    if not status:
        if os.path.exists(screenshot_path):
            return {
                'msg': f'The URL:{url} has already been processed',
                'download_url': f'{download_url}'
            }
        else:
            return {'msg': 'URL has never been processed'}
    else:
        return {'msg': 'URL is being processed'}