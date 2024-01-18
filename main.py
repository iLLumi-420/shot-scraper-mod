from fastapi import FastAPI
from playwright.sync_api import sync_playwright
from shot_scraper.cli import take_shot



app = FastAPI()


browser_instance = None

def initialize_browser():
    global browser_instance
    try:
        print('before p')
        p = sync_playwright().start()
        print('p start')
        browser_instance = p.chromium.launch()
        return browser_instance
    except Exception as e:
        print(f"Error initializing browser: {e}")

def get_browser():
    global browser_instance
    if browser_instance is not None:
        return browser_instance
    else:
        print('returning browser')
        return initialize_browser()

@app.get('/api/ss')
def hello_world():
    return {'hello': 'world'}

@app.get('/api/ss/{url}')
def save_screenshot(url):
    browser = get_browser()
    context = browser.new_context()

    print('working')

    shot = {
    'url' : url
    }

    take_shot(shot=shot, context_or_page=context)

    context.close()

    return {'ss':'saved'}


    
    


