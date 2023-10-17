import os
from pathlib import Path

import aiofiles
from fastapi import UploadFile


async def save_picture(file: UploadFile, dir_path: str):
    if not Path(dir_path):
        os.mkdir(dir_path)
    async with aiofiles.open(dir_path + f"/{file.filename}", "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
