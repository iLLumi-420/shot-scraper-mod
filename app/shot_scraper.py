import click
import urllib
import re
import asyncio
from playwright.async_api import Error
import os   
import pathlib

disallowed_re = re.compile("[^a-zA-Z0-9_-]")


def _check_and_absolutize(filepath):
    try:
        path = pathlib.Path(filepath)
        if path.exists():
            return path.absolute()
        return False
    except OSError:
        # On Windows, instantiating a Path object on `http://` or `https://` will raise an exception
        return False

def file_exists_never(filename):
    return False

def url_or_file_path(url, file_exists=file_exists_never):
    # If url exists as a file, convert that to file:/
    file_path = file_exists(url)
    if file_path:
        return "file:{}".format(file_path)
    if not (url.startswith("http://") or url.startswith("https://")):
        return "http://{}".format(url)
    return url

async def get_screenshot_and_html(
    context,
    shot
):
    url = shot.get("url") or ""
    if not url:
        raise click.ClickException("url is required")


    url = url_or_file_path(url, file_exists=_check_and_absolutize)


    # quality = shot.get("quality")
    # omit_background = shot.get("omit_background")
    # wait = shot.get("wait")


    page = await context.new_page()
   
    viewport = {}
    full_page = True

    if shot.get("width") or shot.get("height"):
        viewport = {
            "width": shot.get("width") or 1280,
            "height": shot.get("height") or 720,
        }
        await page.set_viewport_size(viewport)
        if shot.get("height"):
            full_page = False

    # Load page and check for errors
    response = await page.goto(url)
    await page.wait_for_load_state('networkidle')
    response_url = page.url
    response_html = await page.content()

    # Check if page was a 404 or 500 or other error
    if str(response.status)[0] in ("4", "5"):
        raise click.ClickException(
            "{} error for {}".format(response.status, url)
        )

    screenshot_args = {}
    screenshot_args["full_page"] = full_page

    return await page.screenshot(**screenshot_args), response_url, response_html

