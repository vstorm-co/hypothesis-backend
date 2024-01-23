# from io import BytesIO

# import requests
# from fastapi.responses import FileResponse
#
#
# def download_from_url(url):
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         raise RuntimeError(f"Failed to download {url}") from e
#
#     file_like = BytesIO(response.content)
#
#     file_name = url.split("/")[-1]
#
#     return FileResponse(file_like, filename=file_name)
