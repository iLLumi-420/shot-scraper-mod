from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot
import os
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
from redis import Redis
import asyncio


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
    p = await async_playwright().start()
    browser_instance = await p.chromium.launch()

async def get_browser():
    if browser_instance is None:
        await initialize_browser()
    return browser_instance

async def check_bad_url(url):
    url_bad_return_count = await int(redis.hget("black_list", url).decode('utf-8'))
    if url_bad_return_count and url_bad_return_count > 3:
        print(f'The url:{url} does not provide a status 200 result')
        return True
    else:
        return False


router = APIRouter(lifespan=lifespan)


async def take_screenshot(url):
    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    shot = {'url': url, 'output':f'./static/screenshots/{url}.png'}

    try:
        is_bad_url = await check_bad_url(url)
        if is_bad_url:
            return {'msg': 'The url:{url} will contionously gives error and will not be tried anymore'}
        redis.set(url, 1)
        response = await take_shot(shot=shot, context_or_page=context, fail=True)
        redis.delete(url)
        await context.close()
        return response
    
    except Exception as e:
        print('Error in taking shot', e)
        if redis.hexists("black_list", url):
            redis.hincrby("black_list", url, 1)
        else:
            redis.hset("black_list", url, 1)
        return 
    

@router.get('/screenshot/{url}')
async def main(url: str, request: Request):
    
    screenshot_path = os.path.join(screenshots_dir, f'{url}.png')
    download_url = request.base_url.replace(path=f"api/download/{url}")

    if os.path.exists(screenshot_path):
        return {
            'msg': f'Screenshot the url:{url} has aready been taken',
            'download_url': f'{download_url}'
        }
    
    response = await take_screenshot(url)

    if response is None:
        return {
            'msg': 'Could not take screenshot for url:{url}'
        }
    return {
            'msg': 'Screenshot has been successfully taken',
            'download_url': f'{download_url}'
        }
            


    


@router.get('/download/{url}')
def download_screenshot(url: str):

    screenshot_path = os.path.join(screenshots_dir, f'{url}.png')

    if os.path.exists(screenshot_path):
        return FileResponse(
            path=screenshot_path,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={url}.png",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    else:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    

async def process_bulk_screenshot( req,urls: List[str], background_task=BackgroundTasks):
    results = []
    for url in urls:

        is_bad_url = check_bad_url(url)
        if is_bad_url:
            results.append({'msg': 'The url:{url} will contionously gives error and will not be tried anymore'})
            continue

        screenshot_path = os.path.join(screenshots_dir, f'{url}.png')
        download_url = req.base_url.replace(path=f"api/screenshot/download/{url}")


        if os.path.exists(screenshot_path):
            results.append({"msg": f'screen shot for url: {url} has already been taken', 'download_url': f'{download_url}'})
            continue


        background_task.add_task(take_screenshot, url)
        results.append({"msg": f'screenshot for url {url} is being taken', "download_info":f"After completion you can download it from {download_url}"})

    return results

@router.post('/bulk/screenshots')
async def bluk_screenshot(request: ScreenshotRequest, background_task: BackgroundTasks, req:Request):

    urls = request.urls


    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")
    
    results = await process_bulk_screenshot(req, urls, background_task)

    return results

@router.get('/status/{url}')
def check_status(url, req: Request):

    status = redis.get(url)

    print(status)

    screenshot_path = os.path.join(screenshots_dir, f'{url}.png')
    download_url = req.base_url.replace(path=f"api/screenshot/download/{url}")

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