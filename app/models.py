from pydantic import BaseModel
from typing import List


class ScreenshotsRequest(BaseModel):
    urls: List[str]



class StatusResponse(BaseModel):
    msg: str
    download_url: str = None