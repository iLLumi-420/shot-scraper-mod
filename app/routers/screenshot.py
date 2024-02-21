from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Path, Query
from starlette.responses import FileResponse
from playwright.async_api import async_playwright
import os
from contextlib import asynccontextmanager
from typing import List
from redis import Redis
from app.models import ScreenshotsRequest,StatusResponse
from urllib.parse import urlparse, urljoin
import asyncio
from app.shot_scraper import get_screenshot_and_html
from zipfile import ZipFile
from app.functions import *

redis = Redis(host="localhost", port="6379", db=0)
browser_instance = None



async def initialize_browser():
    global browser_instance
    p = await async_playwright().start()
    browser_instance = await p.chromium.launch()


async def get_browser():
    global browser_instance
    if browser_instance is None:
        await initialize_browser()
    return browser_instance


@asynccontextmanager
def lifespan(app: APIRouter):
    initialize_browser()
    yield
    browser_instance.close()

router = APIRouter(lifespan=lifespan)



async def take_screenshot(url, retry_count = 0):

    if retry_count > 2:
        return None

    browser_instance = await get_browser()
    context = await browser_instance.new_context()

    shot = {"url": url}

    try:
        print(url)
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
        print('retrying', url)
        return await take_screenshot(url, retry_count+1)


async def get_tasks_and_results(req, urls):
    tasks = []
    results = []
    for url in urls:
        url = clean_url(url)
        url = redirected_url(redis, url)
        name = get_hash(url)
        
        redis.hdel('black_list', url)

        screenshot_path = get_path(name)
        download_url = get_download_url(req, url)

        if os.path.exists(screenshot_path):
            results.append({url: f'{download_url}'})
            continue

        is_bad_url = check_bad_url(redis,url)
        if is_bad_url:
            results.append({url: 'Bad url'})
            continue

        tasks.append(take_screenshot(url))
        results.append({url: f'{download_url}'})

    return tasks, results


async def process_task_chunks(tasks, urls_length):
    chunk_size = 10
    for i in range(0, urls_length, chunk_size):
        chunk_tasks = tasks[i:i+chunk_size]
        await asyncio.gather(*chunk_tasks)


@router.post("/save")
async def bulk_screenshot(screenshot_request: ScreenshotsRequest, request: Request, background_task:BackgroundTasks):

    urls = screenshot_request.urls

    if not urls:
        raise HTTPException(status_code=400, detail="No urls received")

    tasks, results = await get_tasks_and_results(request, urls)
    
    background_task.add_task(process_task_chunks, tasks, len(urls))

    return {'results': results}


@router.get("/download/{url:path}")
def download_screenshot(
    url: str = Path(..., description="URL"),
    html: bool = Query(True, description="Download HTML file (default: True)"),
    ss: bool = Query(True, description="Download screenshot (default: True)")
):
    url = clean_url(url)
    url = redirected_url(url)

    name = get_hash(url)
    screenshot_path = get_path(name)
    html_path = get_path(name, html=True)

    if not ss and not html:
        raise HTTPException(status_code=400, detail="Specify either 'ss' or 'html' parameter")

    if ss and html:
        zip_filename = f"{name}_files.zip"

        with ZipFile(zip_filename, 'w') as zip_file:
            if os.path.exists(screenshot_path):
                zip_file.write(screenshot_path, arcname=f"{name}.png")

            if os.path.exists(html_path):
                zip_file.write(html_path, arcname=f"{name}.html")

        return FileResponse(
            path=zip_filename,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    elif ss and os.path.exists(screenshot_path):
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

    elif html and os.path.exists(html_path):
        return FileResponse(
            path=html_path,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={name}.html",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    raise HTTPException(status_code=404, detail="File not found")
    

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
        
    
        