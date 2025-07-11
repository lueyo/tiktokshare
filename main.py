from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import re
import yt_dlp
import asyncio
import time

app = FastAPI()

VIDEO_DIR = "./videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


async def delete_old_videos():
    while True:
        now = time.time()
        for filename in os.listdir(VIDEO_DIR):
            filepath = os.path.join(VIDEO_DIR, filename)
            if os.path.isfile(filepath):
                file_mtime = os.path.getmtime(filepath)
                # If file is older than 3 minutes (180 seconds), delete it
                if now - file_mtime > 180:
                    try:
                        os.remove(filepath)
                        print(f"Deleted old video: {filename}")
                    except Exception as e:
                        print(f"Error deleting file {filename}: {e}")
        await asyncio.sleep(300)  # Sleep for 5 minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(delete_old_videos())

def get_tiktok_url(tiktok_id: str) -> str:
    # Check if the id is short form (e.g. ZNd5tth8o)
    if re.fullmatch(r"[A-Za-z0-9]+", tiktok_id):
        return f"https://vm.tiktok.com/{tiktok_id}"
    # Check if the id is long form (e.g. @drielita/video/7498636088018210070)
    elif re.fullmatch(r"@[^/]+/video/\d+", tiktok_id):
        return f"https://www.tiktok.com/{tiktok_id}"
    else:
        return None


@app.get("/")
async def form():

    return FileResponse("web/index.html")


@app.get("/ping")
async def ping():
    return {"message": "pong"}  # Return a simple pong response


@app.get("/{tiktok_id:path}")
async def download_tiktok_video(tiktok_id: str):
    url = get_tiktok_url(tiktok_id)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid TikTok ID format")

    ydl_opts = {
        "outtmpl": os.path.join(VIDEO_DIR, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract info without downloading
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id")
            ext = info_dict.get("ext")
            filename = os.path.join(VIDEO_DIR, f"{video_id}.{ext}")

            if os.path.exists(filename):
                # If file exists, return it directly
                return FileResponse(filename, media_type="video/mp4")

            # Else download the video
            ydl.extract_info(url, download=True)

            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {str(e)}"
        )

    # Serve the video with media_type video/mp4 so it can be played in browser
    return FileResponse(filename, media_type="video/mp4")
