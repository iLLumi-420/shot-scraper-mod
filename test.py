from playwright.sync_api import sync_playwright
from shot_scraper.cli import shot, take_shot

browser_instance = None

def initialize_browser():
    global browser_instance
    p = sync_playwright().start()
    browser_instance = p.chromium.launch()

def get_browser():
    global browser_instance
    if browser_instance is None:
        initialize_browser()
    return browser_instance

browser_instance = get_browser()
page = browser_instance.new_context()

shot = {
    'url' : 'www.facebook.com',
    'output': '~/Desktop/ss'
}

take_shot(shot=shot, context_or_page=page)


