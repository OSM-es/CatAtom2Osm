import os

import requests
from tqdm import tqdm

number_of_retries = 3
default_timeout = 30
chunk_size = 1024


def get_response(url, stream=False):
    """Try many times to get a http response or raise exception"""
    for i in range(number_of_retries):
        response = requests.get(url, stream=stream, timeout=default_timeout)
        if response.status_code == requests.codes.ok:
            return response
    response.raise_for_status()


def wget(url, filename):
    """Download url to filename"""
    response = get_response(url, stream=True)
    total = 0
    if "Content-Length" in response.headers:
        total = int(response.headers["Content-Length"])
    pbar = tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=chunk_size, leave=False
    )
    pbar.set_description(_("Downloading"))
    pbar.set_postfix(file=os.path.basename(filename), refresh=False)
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            pbar.update(chunk_size)
            f.write(chunk)
    pbar.close()
