from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
import os
import re
import yt_dlp
import asyncio
import time
import requests
from urllib.parse import parse_qs, urlparse
from services.InstagramService import InstagramService
from services.FacebookService import FacebookService
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_DIR = "./videos"
VIDEO_DIR_T = os.path.join(VIDEO_DIR, "t")
VIDEO_DIR_X = os.path.join(VIDEO_DIR, "x")
VIDEO_DIR_I = os.path.join(VIDEO_DIR, "i")
VIDEO_DIR_F = os.path.join(VIDEO_DIR, "f")
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR_T, exist_ok=True)
os.makedirs(VIDEO_DIR_X, exist_ok=True)
os.makedirs(VIDEO_DIR_I, exist_ok=True)
os.makedirs(VIDEO_DIR_F, exist_ok=True)


async def delete_old_videos():
    while True:
        now = time.time()
        # Check all four directories
        for directory in [VIDEO_DIR_T, VIDEO_DIR_X, VIDEO_DIR_I, VIDEO_DIR_F]:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    file_mtime = os.path.getmtime(filepath)
                    # If file is older than 3 minutes (180 seconds), delete it
                    if now - file_mtime > 180:
                        try:
                            os.remove(filepath)
                            print(f"Deleted old video: {filename} from {directory}")
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
    # return FileResponse("web/index.html")
    return RedirectResponse(url="https://ttk.lueyo.es")


@app.get("/ping")
async def ping():
    return {"message": "pong"}  # Return a simple pong response


async def download_tiktok_video_by_id(tiktok_id: str):
    url = get_tiktok_url(tiktok_id)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid TikTok ID format")

    ydl_opts = {
        "outtmpl": os.path.join(VIDEO_DIR_T, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id")
            ext = info_dict.get("ext")
            filename = os.path.join(VIDEO_DIR_T, f"{video_id}.{ext}")

            if os.path.exists(filename):
                return FileResponse(filename, media_type="video/mp4")

            ydl.extract_info(url, download=True)

            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {str(e)}"
        )

    return FileResponse(filename, media_type="video/mp4")


def get_x_url(x_id: str) -> str:
    # Build the URL for platform x based on the path
    # Example: /x/VS4_INDULTADO/status/1943993973292376519
    # We assume the full path after /x/ is the path on https://x.com/
    return f"https://x.com/i/status/{x_id}"


@app.get("/x/{x_id:path}")
async def download_x_video(x_id: str):
    url = get_x_url(x_id)
    ydl_opts = {
        "outtmpl": os.path.join(VIDEO_DIR_X, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

            # If multiple entries (e.g. quoted tweet video), select only the main video
            if "entries" in info_dict and info_dict["entries"]:
                # Select the first entry as the main tweet video
                main_video_info = info_dict["entries"][0]
            else:
                main_video_info = info_dict

            video_id = main_video_info.get("id")
            ext = main_video_info.get("ext")
            filename = os.path.join(VIDEO_DIR_X, f"{video_id}.{ext}")

            if os.path.exists(filename):
                return FileResponse(filename, media_type="video/mp4")

            # Download only the main video
            ydl.extract_info(main_video_info.get("webpage_url") or url, download=True)

            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {str(e)}"
        )

    return FileResponse(filename, media_type="video/mp4")


def get_facebook_url(facebook_id: str) -> str:
    # Construct Facebook video URL from id
    # Example: https://www.facebook.com/reel/765993538835063
    return f"https://www.facebook.com/reel/{facebook_id}"


async def download_facebook_video_by_id(facebook_id: str):
    # Check if facebook_id matches the pattern like 1AZfMP4wBz (length and character types)
    if re.fullmatch(r"[A-Za-z0-9]{10}", facebook_id):
        print(f"Detected short Facebook ID: {facebook_id}")
        # Make a request to get the 302 redirect location header
        share_url = f"https://www.facebook.com/share/v/{facebook_id}/"
        try:
            response = requests.head(share_url, allow_redirects=False)
            print(f"Response: {response.headers}")
            if response.status_code == 302 or response.status_code == 307:
                location = response.headers.get("location")
                if location:
                    # Check if location is a Facebook story URL
                    if location.startswith("https://www.facebook.com/story.php?"):
                        # Extract story_fbid parameter from the query string
                        parsed_url = urlparse(location)
                        query_params = parse_qs(parsed_url.query)
                        story_fbid = query_params.get("story_fbid", [None])[0]
                        if story_fbid:
                            facebook_id = story_fbid
                            print(f"Extracted story_fbid: {story_fbid}")

                    # Check if location is a Facebook videos URL format
                    elif "/videos/" in location:
                        # Extract video ID from /videos/ format
                        match = re.search(r"/videos/(\d+)", location)
                        if match:
                            facebook_id = match.group(1)
                            print(f"Extracted video ID from videos URL: {facebook_id}")

                    # Always use the facebook_id (either original or extracted) to construct proper reel URL
                    url = get_facebook_url(facebook_id)
                    print(f"Using reel URL: {url}")
                else:
                    url = get_facebook_url(facebook_id)
            else:
                url = get_facebook_url(facebook_id)
        except Exception:
            url = get_facebook_url(facebook_id)
    else:
        url = get_facebook_url(facebook_id)

    ydl_opts = {
        "outtmpl": os.path.join(VIDEO_DIR_F, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id")
            ext = info_dict.get("ext")
            filename = os.path.join(VIDEO_DIR_F, f"{video_id}.{ext}")

            if os.path.exists(filename):
                return FileResponse(filename, media_type="video/mp4")
            # print(f"Downloading Facebook video: {url}")

            ydl.extract_info(url, download=True)

            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        # Fallback a FacebookService si falla yt_dlp
        try:
            filename = os.path.join(VIDEO_DIR_F, f"{facebook_id}.mp4")
            FacebookService.download_video_with_requests(url, filename)
        except Exception as fallback_e:
            raise HTTPException(
                status_code=500,
                detail=f"Error descargando video: {str(e)}; Fallback error: {str(fallback_e)}",
            )

        if not os.path.exists(filename):
            raise HTTPException(
                status_code=500, detail="Video download failed in fallback"
            )

    return FileResponse(filename, media_type="video/mp4")


def get_instagram_url(instagram_id: str) -> str:
    return f"https://www.instagram.com/p/{instagram_id}/"


async def download_instagram_video_by_id(instagram_id: str):
    url = get_instagram_url(instagram_id)

    ydl_opts = {
        "outtmpl": os.path.join(VIDEO_DIR_I, f"{instagram_id}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            ext = info_dict.get("ext")
            filename = os.path.join(VIDEO_DIR_I, f"{instagram_id}.{ext}")

            if os.path.exists(filename):
                return FileResponse(filename, media_type="video/mp4")

            ydl.extract_info(url, download=True)

            if not os.path.exists(filename):
                raise HTTPException(status_code=500, detail="Video download failed")
    except Exception as e:
        # Fallback to InstagramService download with requests
        try:
            filename = os.path.join(VIDEO_DIR_I, f"{instagram_id}.mp4")
            InstagramService.download_video_with_requests(url, filename)
        except Exception as fallback_e:
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading video: {str(e)}; Fallback error: {str(fallback_e)}",
            )

        if not os.path.exists(filename):
            raise HTTPException(
                status_code=500, detail="Video download failed in fallback"
            )

    return FileResponse(filename, media_type="video/mp4")


@app.get("/i/{instagram_id}")
async def download_instagram_video(instagram_id: str):
    return await download_instagram_video_by_id(instagram_id)


@app.get("/t/{tiktok_id:path}")
async def download_tiktok_video_t(tiktok_id: str):
    return await download_tiktok_video_by_id(tiktok_id)


@app.get("/f/{facebook_id}")
async def download_facebook_video(facebook_id: str):
    return await download_facebook_video_by_id(facebook_id)


@app.get("/{tiktok_id:path}")
async def download_tiktok_video(tiktok_id: str):
    return await download_tiktok_video_by_id(tiktok_id)
