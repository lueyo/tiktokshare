import os
import re
import requests
from fastapi import HTTPException


class FacebookService:
    FSAVE_API_URL = "https://fsave.net/proxy.php"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://fsave.net",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Referer": "https://fsave.net/es/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0",
        "TE": "trailers",
    }

    @classmethod
    def download_video_with_requests(cls, facebook_url: str, save_path: str) -> str:
        """
        Descarga un video de Facebook usando la API de fsave.net como método alternativo.
        Devuelve la ruta al archivo guardado.
        Lanza HTTPException en caso de error.
        """
        data = {"url": facebook_url}
        try:
            response = requests.post(cls.FSAVE_API_URL, headers=cls.HEADERS, data=data)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error contactando fsave.net: {str(e)}"
            )

        try:
            json_resp = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Respuesta inválida de fsave.net: {str(e)}"
            )

        # El parámetro que nos interesa es previewUrl
        preview_url = None
        if "api" in json_resp and "previewUrl" in json_resp["api"]:
            preview_url = json_resp["api"]["previewUrl"]
        if not preview_url:
            raise HTTPException(
                status_code=500,
                detail="No se encontró previewUrl en la respuesta de fsave.net",
            )

        # Descargar el video
        try:
            video_response = requests.get(
                preview_url,
                headers={"User-Agent": cls.HEADERS["User-Agent"]},
                stream=True,
            )
            video_response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error descargando el video de previewUrl: {str(e)}",
            )

        # Guardar el video
        try:
            with open(save_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error guardando el archivo de video: {str(e)}"
            )

        return save_path
