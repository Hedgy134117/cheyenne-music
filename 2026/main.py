import re
import sys
from pathlib import Path
from pprint import pprint
from urllib.parse import urlencode
from urllib.request import urlretrieve

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def clean_text(text: str) -> str:
    return re.sub(r"\W", "", text, flags=re.UNICODE)


def get_albums(filename: str) -> list[tuple[str, str]]:
    with open(filename, encoding="utf-8") as f:
        music = "".join(f.readlines())

    return re.findall(r"[0-9]+\. (.+?),\sby\s(.+?)\s-", music)


def download_album_art(albums: list[tuple[str, str]]) -> None:
    driver_options = Options()
    driver_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=driver_options)

    img_path = Path.cwd().parent / "imgs"

    for title, artist in albums:
        print(f"Downloading {title} by {artist}")
        params = urlencode(
            {
                "album": title,
                "artist": artist,
                "country": "us",
                "sources": "spotify",
            }
        )

        driver.get(f"https://covers.musichoarders.xyz/?{params}")

        try:
            wait = WebDriverWait(driver, 10)
            img = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='http']"))
            )
            img_url = img.get_attribute("src")

            extension = "jpg" if ".jpg" in img_url else "png"
            filename = f"{clean_text(artist)}-{clean_text(title)}.{extension}"

            urlretrieve(img_url, img_path / filename)
        except TimeoutException:
            print("\t! Couldn't find on Apple Music, skipping")


def create_file(filepath: Path, frontmatter: list[str], content: list[str]) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.writelines(frontmatter)
        f.write("---\n")
        f.writelines(content)


def split_albums(filename: str, path: Path, tags: list[str]) -> None:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    albums_created = 0
    i = 0

    prev = ""
    next_ = ""
    for i in range(len(lines)):
        if lines[i] == "\n":
            continue

        header_match = re.match(r"([0-9]+)\. (.+?),\sby\s(.+?)\s-\s(.+)", lines[i])
        rank, title, artist, review = header_match.groups()

        # Create frontmatter
        clean_title = clean_text(title)
        clean_artist = clean_text(artist)

        if i < len(lines) - 1:
            prev_match = re.match(r"([0-9]+)\. (.+?),\sby\s(.+?)\s-\s.+", lines[i + 1])
            # print(prev_match)
            prev_rank, prev_title, prev_artist = prev_match.groups()
            prev = f"{prev_rank}-{clean_text(prev_artist)}-{clean_text(prev_title)}"
        else:
            prev = ""

        frontmatter = [
            "layout: album.njk\n",
            f"tags: {tags}\n",
            f"rank: {rank}\n",
            f"title: {title}\n",
            f"artist: {artist}\n",
            f"is_short: True\n",
            f"prev: {prev if prev else ''}\n",
            f"next: {next_}\n",
        ]

        # Find image if exists
        img_files = list(Path("../imgs").glob(f"{clean_artist}-{clean_title}*"))
        if img_files:
            frontmatter.append(f"img_url: /imgs/{img_files[0].name}\n")

        name = f"{rank}-{clean_artist}-{clean_title}"

        create_file(
            path / f"{name}.md",
            frontmatter,
            ["\n", review, "\n", "\n<!-- excerpt -->\n"],
        )

        next_ = name

        albums_created += 1


if __name__ == "__main__":
    MAIN = "2026 music masterdoc.md"

    # albums = get_albums(MAIN)
    # download_album_art(albums)
    split_albums("jan/_jan.md", Path("jan"), ["album2026", "jan2026"])
