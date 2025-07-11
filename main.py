from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import re
import yt_dlp

app = FastAPI()

VIDEO_DIR = "./videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


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
            info_dict = ydl.extract_info(url, download=True)
            video_id = info_dict.get("id")
            ext = info_dict.get("ext")
            filename = os.path.join(VIDEO_DIR, f"{video_id}.{ext}")
            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {str(e)}"
        )

    # Serve the video with media_type video/mp4 so it can be played in browser
    return FileResponse(filename, media_type="video/mp4")
