from fastapi import APIRouter
from playwright.async_api import async_playwright
from shot_scraper.cli import take_shot


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

    return {'msg':response}

