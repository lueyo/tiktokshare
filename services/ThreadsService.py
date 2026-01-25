import re
import requests
import html
import time
import urllib.parse
from fastapi import HTTPException
import json


class ThreadsService:

    THREADS_URL_TEMPLATE = "https://www.threads.net/i/post/{}"

    # Publer API token for fallback download method
    PUBLER_TOKEN = "0.oNJxIRd_FY94geBo91tTEHIfzCycAZsFqozHckT6_-PsuWHw0ArJ8f7JY_fLE_Kwy52k0JXPPGhH4uebSFZYX7lcoi1sZQJkubZa-NS_zYvdWT8earnjE9mq3P0DQOEUpOC-qx4kLZn-2y-VCSrgs-g4cJWTX3frnLbkYNLnR2mD0v52kngE3bpxDfK0Mqqd7nMzTYAnxV67DTuTtjWNfal7qx8yaUKKbOyp3rxaUnwmCEOmvH0--J-rpurWchNGH-qiejh8u5J4NDkQUyY0mhmH_gpzEMt7G7ycZrE4FGrnxy35cjBRI_v81HGnNufRaAPVyBdAtkJePbNQLgcop05nzRlRwklpWHQ5_S38gjX0K_IRm_-ihR9ZSc2LCDo-hdERnOD0pnT3s80fJpAn0p4VzLK7iadQLWVm7L_3z9q5Mi8vj6vBVeU4CSK09G08oW47pDRTP96j22X4WxiIri5bolviIlN9ysyOHH0vDTH0rHjcS_mM0elIyVI05GDBEAqIZFoHiZ8QfptQzO0dpaSSaAC2wi5VSi1HjQ_u5GR0li79lpG6ozosDl49RW5NRQt1vlfqfMd1GNMCQ1SrjXdzOmMQmw46WeixE72pCTg52pLf7gudt8nOlHd0WZyQ7UdJrosY5R3D_M8k1Q7SZIRt-4MPPB0B7Yy27HKgyPUfnyOHJ0-1jjQ_zt8TKMwvK6aI082stwutrKyuSUb7E_myCWsMdRzWuatJgVyPZMDxixvnMmENthbQjgUSf6vFLBzn6NQ-xIezfZGA4LF3CIKCgkIKQ2awkb1j6sXnzGGidhjlyYidmk70tB56aGqD6x6q1Ywvc18tX6ToB6LfWYN-EuVg1ZJs630hplvAyEQ.T5V9PeYqzp83djkxhb16HA.d4a2c7d12b29492fb19a1c5d24c9ec2c728329deec2005278b46b3735e76aa9e"

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
        "TE": "trailers",
    }

    @classmethod
    def fetch_html(cls, url: str) -> str:
        """
        Obtiene el contenido HTML de una URL de Threads.

        Args:
            url: URL completa del post de Threads

        Returns:
            Contenido HTML de la página

        Raises:
            HTTPException: Si hay error al hacer la petición
        """
        try:
            response = requests.get(url, headers=cls.HEADERS)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching Threads page: {str(e)}"
            )

    @classmethod
    def obtener_video_threads(cls, html_content: str) -> str:
        """
        Extrae la URL del video del contenido HTML de un post de Threads.

        Args:
            html_content: Contenido HTML de la página del post

        Returns:
            URL del video en calidad HD

        Raises:
            HTTPException: Si no se encuentra el video
        """
        # 1. Intentar extraer desde JSON estructurado (más confiable)
        try:
            pattern = r'<script[^>]*?type="application/json"[^>]*?data-sjs[^>]*?>(.*?)</script>'
            match = re.search(pattern, html_content, re.DOTALL)

            if match:
                json_str = match.group(1)
                json_str = html.unescape(json_str)
                data = json.loads(json_str)

                # Navegar la estructura JSON
                bbox = data["require"][0][3][0]["__bbox"]
                video_versions = bbox["result"]["data"]["data"]["edges"][0]["node"][
                    "thread_items"
                ][0]["post"]["video_versions"]

                if video_versions:
                    # Seleccionar mejor calidad (101 = HD, 102/103 = SD)
                    best_video = max(video_versions, key=lambda v: v.get("type", 0))
                    if "url" in best_video:
                        return best_video["url"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            pass  # Si falla, intentamos con regex

        # 2. Fallback: expresión regular para video_versions
        try:
            patron = r'"video_versions":\s*(\[\{.*?\}\])'
            coincidencias = re.findall(patron, html_content)

            for json_str in coincidencias:
                versiones = json.loads(json_str)
                video_hd = next((v for v in versiones if v.get("type") == 101), None)
                if not video_hd:
                    video_hd = next(
                        (v for v in versiones if v.get("type") in [102, 103]), None
                    )
                if video_hd and "url" in video_hd:
                    return video_hd["url"]
        except (json.JSONDecodeError, StopIteration):
            pass  # Si falla, continuamos y lanzamos excepción al final

        raise HTTPException(
            status_code=404, detail="No se encontró video en el post de Threads"
        )

    @classmethod
    def _download_with_publer(cls, thread_url: str, save_path: str) -> str:
        """
        Método de respaldo usando la API de Publer.
        1. Crea el job.
        2. Consulta el estado cada 2 segundos (max 6 intentos).
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
                        if video_entry.get("type") == "video" and video_entry.get(
                            "path"
                        ):
                            video_url = video_entry["path"]
                            break
                elif status == "working":
                    continue
                else:
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
    def download_video(cls, thread_code: str, save_path: str) -> str:
        """
        Método principal para descargar un video de Threads.

        Flujo:
        1. Construye la URL del post
        2. Obtiene el HTML
        3. Extrae la URL del video
        4. Descarga el video
        5. Si falla, usa Publer como fallback

        Args:
            thread_code: Código del post de Threads (ej: DS-74VmCbK9)
            save_path: Ruta donde se guardará el video

        Returns:
            Ruta del archivo descargado
        """
        full_thread_url = cls.THREADS_URL_TEMPLATE.format(thread_code)

        try:
            # Paso 1: Obtener HTML
            print("Obteniendo HTML de Threads...")
            html_content = cls.fetch_html(full_thread_url)

            # Paso 2: Extraer URL del video
            print("Extrayendo URL del video...")
            video_url = cls.obtener_video_threads(html_content)
            print(f"URL del video: {video_url}")

            # Paso 3: Descargar video
            print("Descargando video...")
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

            print(f"Descarga exitosa: {save_path}")
            return save_path

        except HTTPException:
            # Re-lanzar HTTPException directamente (ya tiene el mensaje apropiado)
            raise
        except Exception as e:
            # Para cualquier otro error, usar Publer como fallback
            print(f"Método principal falló ({str(e)}). Cambiando a Publer...")
            return cls._download_with_publer(full_thread_url, save_path)
