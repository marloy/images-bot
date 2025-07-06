import requests
from pathlib import Path
from config import YANDEX_TOKEN

def create_nested_folders(path: str):
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    base_url = "https://cloud-api.yandex.net/v1/disk/resources"
    
    parts = Path(path).parts
    accumulated_path = ""

    for part in parts:
        accumulated_path = f"{accumulated_path}/{part}" if accumulated_path else part
        response = requests.put(
            base_url,
            headers=headers,
            params={"path": accumulated_path}
        )
        if response.status_code not in (201, 409):  # 409 = уже существует
            raise Exception(f"Ошибка создания папки '{accumulated_path}': {response.text}")

def upload_bytes(file_bytes: bytes, remote_path: str):
    folder_path = str(Path(remote_path).parent)
    if folder_path:
        create_nested_folders(folder_path)

    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/upload",
        headers=headers,
        params={"path": remote_path, "overwrite": "false"}
    )
    if response.status_code != 200:
        raise Exception(f"Не удалось получить ссылку загрузки: {response.text}")

    upload_url = response.json()["href"]

    put_resp = requests.put(upload_url, data=file_bytes)
    if put_resp.status_code not in (201, 202):
        raise Exception(f"Ошибка загрузки файла: {put_resp.text}")