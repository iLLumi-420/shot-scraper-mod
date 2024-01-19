from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse, HTMLResponse
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot
import os


router = APIRouter()

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

@router.get('/')
def hello_world():
    return {'hello': 'world'}

@router.get('/{url}')
async def main(url):
    global browser_instance
    browser_instance = await get_browser()
    context = await browser_instance.new_context()
    


    shot = {'url': url, 'output':f'./static/screenshots/{url}.png'}

    response = await take_shot(shot=shot, context_or_page=context)

    await context.close()

    return HTMLResponse(content=f'<p>{response}<p><br><a href="download/{url}">Download Image</a>')

@router.get('/download/{url}')
def download_screenshot(url):

    screenshots_dir = os.path.abspath('./static/screenshots')

    ss_path = os.path.join(screenshots_dir, f'{url}.png')

    print(ss_path)

    if os.path.exists(ss_path):
        return FileResponse(
            path=ss_path,
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

