from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot
import os
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
from redis import Redis


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


router = APIRouter(lifespan=lifespan)


async def take_screenshot(url):
    global browser_instance
    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    shot = {'url': url, 'output':f'./static/screenshots/{url}.png'}

    try:
        response = await take_shot(shot=shot, context_or_page=context)
        await context.close()
        return response
    except Exception as e:
        print('Error in taking shot', e)
    

@router.get('/{url}')
async def main(url: str, request: Request):
    
    screenshot_path = os.path.join(screenshots_dir, f'{url}.png')
    download_url = request.base_url.replace(path=f"api/screenshot/download/{url}")

    if not os.path.exists(screenshot_path):
        response = await take_screenshot(url)

    return {
        'download_url': download_url
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
    

async def process_bulk_screenshot(req, urls: List[str], background_task=BackgroundTasks):
    results = []
    for url in urls:
        
        background_task.add_task(take_screenshot, url)
        results.append({"msg": f'screenshot for url {url} is being taken'})

    return results

@router.post('/bulk')
async def bluk_screenshot(request: ScreenshotRequest, background_task: BackgroundTasks, req:Request):

    urls = request.urls

    download_url = req.base_url.replace(path="api/screenshot/download/{url}")

    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")
    
    results = await process_bulk_screenshot(request ,urls, background_task)

    return {
        "results": results,
        "download_url" : download_url
    }

