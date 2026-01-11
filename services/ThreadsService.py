import re
import requests
import json
import html
import time
import urllib.parse
from fastapi import HTTPException


class ThreadsService:

    THREADS_URL_TEMPLATE = "https://www.threads.net/i/post/{}"

    # Publer API token for fallback download method
    PUBLER_TOKEN = "0.oNJxIRd_FY94geBo91tTEHIfzCycAZsFqozHckT6_-PsuWHw0ArJ8f7JY_fLE_Kwy52k0JXPPGhH4uebSFZYX7lcoi1sZQJkubZa-NS_zYvdWT8earnjE9mq3P0DQOEUpOC-qx4kLZn-2y-VCSrgs-g4cJWTX3frnLbkYNLnR2mD0v52kngE3bpxDfK0Mqqd7nMzTYAnxV67DTuTtjWNfal7qx8yaUKKbOyp3rxaUnwmCEOmvH0--J-rpurWchNGH-qiejh8u5J4NDkQUyY0mhmH_gpzEMt7G7ycZrE4FGrnxy35cjBRI_v81HGnNufRaAPVyBdAtkJePbNQLgcop05nzRlRwklpWHQ5_S38gjX0K_IRm_-ihR9ZSc2LCDo-hdERnOD0pnT3s80fJpAn0p4VzLK7iadQLWVm7L_3z9q5Mi8vj6vBVeU4CSK09G08oW47pDRTP96j22X4WxiIri5bolviIlN9ysyOHH0vDTH0rHjcS_mM0elIyVI05GDBEAqIZFoHiZ8QfptQzO0dpaSSaAC2wi5VSi1HjQ_u5GR0li79lpG7ozosDl49RW5NRQt1vlfqfMd1GNMCQ1SrjXdzOmMQmw46WeixE72pCTg52pLf7gudt8nOlHd0WZyQ7UdJrosY5R3D_M8k1Q7SZIRt-4MPPB0B7Yy27HKgyPUfnyOHJ0-1jjQ_zt8TKMwvK6aI082stwutrKyuSUb7E_myCWsMdRzWuatJgVyPZMDxixvnMmENthbQjgUSf6vFLBzn6NQ-xIezfZGA4LF3CIKCgkIKQ2awkb1j6sXnzGGidhjlyYidmk70tB56aGqD6x6q1Ywvc18tX6ToB6LfWYN-EuVg1ZJs630hplvAyEQ.T5V9PeYqzp83djkxhb16HA.d4a2c7d12b29492fb19a1c5d24c9ec2c728329deec2005278b46b3735e76aa9e"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
    }

    PUBLER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://publer.com/",
        "Content-Type": "application/json;",
        "Origin": "https://publer.com",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    JOB_STATUS_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://publer.com",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://publer.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "TE": "trailers",
    }
    
    DOWNLOAD_WORKER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://publer.com/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "TE": "trailers"
    }

    @classmethod
    def get_video_url(cls, thread_code: str) -> str:
        """
        Método principal para intentar extraer la URL directamente de Threads.
        """
        url = cls.THREADS_URL_TEMPLATE.format(thread_code)
        try:
            response = requests.get(url, headers=cls.HEADERS)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching Threads page: {str(e)}"
            )

        html_content = response.text

        # Pattern to match the JSON directly inside the script tag
        pattern = (
            r'<script[^>]*?type="application/json"[^>]*?data-sjs[^>]*?>(.*?)</script>'
        )
        match = re.search(pattern, html_content, re.DOTALL)

        if not match:
            raise HTTPException(
                status_code=404, detail="Threads JSON data not found in page"
            )

        json_str = match.group(1)
        json_str = html.unescape(json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500, detail=f"Error parsing Threads JSON: {str(e)}"
            )

        try:
            # Based on doc.html: {"require":[["ScheduledServerJS","handle",null,[{"__bbox":{...}}]]]}
            bbox = data["require"][0][3][0]["__bbox"]

            video_versions = bbox["result"]["data"]["data"]["edges"][0]["node"][
                "thread_items"
            ][0]["post"]["video_versions"]

            if not video_versions:
                raise HTTPException(
                    status_code=404, detail="No video found in Threads post"
                )

            # Select the highest quality video (type 101 is usually the highest)
            best_video = None
            best_type = -1

            for video in video_versions:
                video_type = video.get("type", 0)
                if video_type > best_type:
                    best_type = video_type
                    best_video = video

            if best_video and "url" in best_video:
                return best_video["url"]
            else:
                raise HTTPException(
                    status_code=404, detail="No video URL found in Threads post"
                )

        except (KeyError, IndexError, TypeError) as e:
            # Capturamos errores de estructura para forzar el fallback
            raise HTTPException(
                status_code=500,
                detail=f"Error navigating Threads JSON structure: {str(e)}",
            )

    @classmethod
    def _download_with_publer(cls, thread_url: str, save_path: str) -> str:
        """
        Método de respaldo usando la API de Publer.
        1. Crea el job.
        2. Consulta el estado cada segundo (max 5 veces).
        3. Descarga usando el worker.
        """
        print("Iniciando descarga alternativa con Publer...")
        
        # --- Peticion 1: Crear Job ---
        job_url = "https://app.publer.com/tools/media"
        payload = {"url": thread_url, "token": cls.PUBLER_TOKEN, "macOS": False}

        try:
            response = requests.post(job_url, json=payload, headers=cls.PUBLER_HEADERS)
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            if not job_id:
                raise Exception("No job_id received from Publer")
                
        except Exception as e:
            print(f"Publer Error al crear job: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating Publer job: {str(e)}"
            )

        # --- Peticion 2: Polling del estado ---
        job_status_url = f"https://app.publer.com/api/v1/job_status/{job_id}"
        video_url = None

        for attempt in range(6):
            try:
                # Si no es el primer intento, esperamos 2 segundo antes de consultar
                if attempt > 0:
                    time.sleep(2)

                response = requests.get(job_status_url, headers=cls.JOB_STATUS_HEADERS)
                response.raise_for_status()
                status_data = response.json()
                status = status_data.get("status")

                print(f"Publer Status (Intento {attempt+1}/6): {status}")

                if status == "complete":
                    payload_data = status_data.get("payload", [])
                    if payload_data:
                        video_entry = payload_data[0]
                        if video_entry.get("type") == "video" and video_entry.get("path"):
                            video_url = video_entry["path"]
                            break
                elif status == "working":
                    # Continuamos al siguiente ciclo (que hará el sleep al inicio)
                    continue 
                else:
                    # Estado desconocido o error
                    continue

            except Exception as e:
                print(f"Error en polling Publer intento {attempt+1}: {e}")
                continue

        if not video_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to get video URL from Publer after 5 polling attempts",
            )

        # --- Peticion 3: Descargar video del worker ---
        # Es necesario codificar la URL del video para pasarla como parámetro
        encoded_video_url = urllib.parse.quote(video_url)
        download_worker_url = f"https://publer-media-downloader.kalemi-code4806.workers.dev/?url={encoded_video_url}"

        try:
            print("Descargando video desde Publer worker...")
            video_response = requests.get(
                download_worker_url,
                headers=cls.DOWNLOAD_WORKER_HEADERS,
                stream=True,
            )
            video_response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return save_path

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading video from Publer worker: {str(e)}",
            )

    @classmethod
    def download_video_with_requests(cls, thread_code: str, save_path: str) -> str:
        """
        Método principal. Intenta el método original (scraping directo),
        si falla en obtener la URL o descargar el archivo, usa el fallback de Publer.
        """
        full_thread_url = cls.THREADS_URL_TEMPLATE.format(thread_code)

        try:
            # Intentar método principal
            print("Intentando método principal (Scraping)...")
            video_url = cls.get_video_url(thread_code)
            
            # Intentar descarga directa
            video_response = requests.get(
                video_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            video_response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print("Descarga principal exitosa.")
            return save_path

        except Exception as e:
            # Si falla CUALQUIER cosa del método principal, vamos al fallback
            print(f"Método principal falló ({str(e)}). Cambiando a Publer...")
            return cls._download_with_publer(full_thread_url, save_path)


if __name__ == "__main__":
    # Test Block
    test_link = "https://www.threads.net/i/post/DS-74VmCbK9"
    # Extraer código
    if "/post/" in test_link:
        thread_code = test_link.split("/post/")[-1].split("?")[0]
    else:
        thread_code = "DS-74VmCbK9"

    save_location = "video_threads.mp4"

    print(f"Probando descarga para código: {thread_code}")
    
    try:
        ThreadsService.download_video_with_requests(thread_code, save_location)
        print(f"Video guardado correctamente en: {save_location}")
    except HTTPException as e:
        print(f"Error Final: {e.status_code} - {e.detail}")
    except Exception as e:
        print(f"Error Inesperado: {e}")