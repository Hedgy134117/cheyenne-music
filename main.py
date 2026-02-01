import re
import sys
from pathlib import Path
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


def get_top_50_albums(filename: str) -> list[tuple[str, str]]:
    with open(filename, encoding="utf-8") as f:
        music = "".join(f.readlines())

    return re.findall(r"[0-9]+\. (.+)\, by (.+)", music)[:50]


def get_other_albums(filename: str) -> list[tuple[str, str]]:
    with open(filename, encoding="utf-8") as f:
        music = "".join(f.readlines())
        index = "Late 2024 albums I enjoyed this year:"
        music = music[music.index(index) :]

    return re.findall(r"[0-9]+\. (.+)\, by (.+)", music)


def download_album_art(albums: list[tuple[str, str]]) -> None:
    driver_options = Options()
    driver_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=driver_options)

    img_path = Path.cwd() / "imgs"

    for title, artist in albums:
        print(f"Downloading {title} by {artist}")
        params = urlencode(
            {
                "album": title,
                "artist": artist,
                "country": "us",
                "sources": "applemusic",
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


def split_top_50_albums(filename: str, path: Path) -> None:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    albums_created = 0
    i = 0

    prev = ""
    next_ = ""
    while i < len(lines) and albums_created < 50:
        # Find next album header
        header_match = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if not header_match:
            i += 1
            continue

        rank, title, artist = header_match.groups()

        # Collect content until next header or end
        content_lines = []
        i += 1
        while i < len(lines) and not re.match(r"[0-9]+\. .+, by .+", lines[i]):
            content_lines.append(lines[i].lstrip() + "\n")
            if len(content_lines) == 2:
                content_lines.append("<!-- excerpt -->\n\n")
            i += 1

            # Stop adding content after the last line of content for the last album
            # (otherwise it would keep going and include honorable mentions, etc.)
            if albums_created == 49 and lines[i] == "\n":
                break

        num_paragraphs = sum([len(line.strip()) > 0 for line in content_lines])

        # Create frontmatter
        clean_title = clean_text(title)
        clean_artist = clean_text(artist)

        prev = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if prev:
            prev_rank, prev_title, prev_artist = prev.groups()
            prev = f"{prev_rank}-{clean_text(prev_artist)}-{clean_text(prev_title)}"

        frontmatter = [
            "layout: album.njk\n",
            "tags: album\n",
            f"rank: {rank}\n",
            f"title: {title}\n",
            f"artist: {artist}\n",
            f"is_short: {num_paragraphs == 2}\n",
            f"prev: {prev if prev else ''}\n",
            f"next: {next_}\n",
        ]

        # Find image if exists
        img_files = list(Path("imgs").glob(f"{clean_artist}-{clean_title}*"))
        if img_files:
            frontmatter.append(f"img_url: /imgs/{img_files[0].name}\n")

        name = f"{rank}-{clean_artist}-{clean_title}"

        create_file(
            path / f"{name}.md",
            frontmatter,
            content_lines,
        )

        next_ = name

        albums_created += 1


def split_top_50_songs(filename: str, path: Path) -> None:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    songs_created = 0
    i = lines.index("50 Songs:\n") + 2

    prev = ""
    next_ = ""
    while i < len(lines) and songs_created < 50:
        # Find next song header
        header_match = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if not header_match:
            i += 1
            continue

        rank, title, artist = header_match.groups()

        # Collect content until next header or end
        content_lines = []
        i += 1
        while (
            i < len(lines)
            and not re.match(r"[0-9]+\. .+, by .+", lines[i])
            and songs_created < 49
        ):
            content_lines.append(lines[i].lstrip() + "\n")
            if len(content_lines) == 2:
                content_lines.append("<!-- excerpt -->\n\n")
            i += 1

        num_paragraphs = sum([len(line.strip()) > 0 for line in content_lines])

        # Create frontmatter
        clean_title = clean_text(title)
        clean_artist = clean_text(artist)

        prev = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if prev:
            prev_rank, prev_title, prev_artist = prev.groups()
            prev = f"{prev_rank}-{clean_text(prev_artist)}-{clean_text(prev_title)}"

        frontmatter = [
            "layout: song.njk\n",
            "tags: song\n",
            f"rank: {rank}\n",
            f"title: {title}\n",
            f"artist: {artist}\n",
            f"is_short: {num_paragraphs == 2 or num_paragraphs == 0}\n",
            f"prev: {prev if prev else ''}\n",
            f"next: {next_}\n",
        ]

        name = f"{rank}-{clean_artist}-{clean_title}"

        # Find image if exists
        img_files = list(Path("imgs").glob(f"{clean_artist}-{clean_title}*"))
        if img_files:
            frontmatter.append(f"img_url: /imgs/{img_files[0].name}\n")

        create_file(
            path / f"{name}.md",
            frontmatter,
            content_lines,
        )

        next_ = name

        songs_created += 1


def split_top_5_eps(filename: str, path: Path) -> None:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    eps_created = 0
    i = lines.index("5 EPs:\n") + 2

    prev = ""
    next_ = ""
    while i < len(lines) and eps_created < 5:
        # Find next ep header
        header_match = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if not header_match:
            i += 1
            continue

        rank, title, artist = header_match.groups()

        # Collect content until next header or end
        content_lines = []
        i += 1
        while i < len(lines) and not re.match(r"[0-9]+\. .+, by .+", lines[i]):
            content_lines.append(lines[i].lstrip() + "\n")
            if len(content_lines) == 2:
                content_lines.append("<!-- excerpt -->\n\n")
            i += 1

            if eps_created == 4 and lines[i] == "\n":
                break

        # Create frontmatter
        clean_title = clean_text(title)
        clean_artist = clean_text(artist)

        prev = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if prev:
            prev_rank, prev_title, prev_artist = prev.groups()
            prev = f"{prev_rank}-{clean_text(prev_artist)}-{clean_text(prev_title)}"

        frontmatter = [
            "layout: song.njk\n",
            "tags: ep\n",
            f"rank: {rank}\n",
            f"title: {title}\n",
            f"artist: {artist}\n",
            f"is_short: True\n",
            f"prev: {prev if prev else ''}\n",
            f"next: {next_}\n",
        ]

        name = f"{rank}-{clean_artist}-{clean_title}"

        # Find image if exists
        img_files = list(Path("imgs").glob(f"{clean_artist}-{clean_title}*"))
        if img_files:
            frontmatter.append(f"img_url: /imgs/{img_files[0].name}\n")

        create_file(
            path / f"{name}.md",
            frontmatter,
            content_lines,
        )

        next_ = name

        eps_created += 1


def split_other(filename: str, path: Path) -> None:
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    i = lines.index("Late 2024 albums I enjoyed this year:\n")

    is_last_year = True
    last_last_year = False

    prev = ""
    next_ = ""
    while i < len(lines):
        # Find next album header
        header_match = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
        if not header_match:
            i += 1
            continue

        rank, title, artist = header_match.groups()

        # Collect content until next header or end
        content_lines = []
        i += 1
        while i < len(lines) and not re.match(r"[0-9]+\. .+, by .+", lines[i]):
            if is_last_year and "Older albums that stayed with me in 2025" in lines[i]:
                last_last_year = True
                break

            content_lines.append(lines[i].lstrip() + "\n")
            if len(content_lines) == 2:
                content_lines.append("<!-- excerpt -->\n\n")
            i += 1

        num_paragraphs = sum([len(line.strip()) > 0 for line in content_lines])

        # Create frontmatter
        clean_title = clean_text(title)
        clean_artist = clean_text(artist)

        try:
            prev = re.match(r"([0-9]+)\. (.+), by (.+)", lines[i])
            if prev:
                prev_rank, prev_title, prev_artist = prev.groups()
                prev = f"{prev_rank}-{clean_text(prev_artist)}-{clean_text(prev_title)}"
        except IndexError:
            prev = ""

        frontmatter = [
            "layout: album.njk\n",
            f"tags: {'lastyear' if is_last_year else 'older'}\n",
            f"rank: {rank}\n",
            f"title: {title}\n",
            f"artist: {artist}\n",
            f"is_short: {num_paragraphs == 2}\n",
            f"prev: {prev if prev else ''}\n",
            f"next: {next_}\n",
        ]

        # Find image if exists
        img_files = list(Path("imgs").glob(f"{clean_artist}-{clean_title}*"))
        if img_files:
            frontmatter.append(f"img_url: /imgs/{img_files[0].name}\n")

        name = f"{rank}-{clean_artist}-{clean_title}"

        create_file(
            path / f"{name}.md",
            frontmatter,
            content_lines,
        )

        next_ = name

        if last_last_year and is_last_year:
            prev = ""
            next_ = ""
            is_last_year = False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <download50|downloadother|split> [start] [end]")
        sys.exit(1)

    MAIN = "Best Music of 2025 (1).md"

    command = sys.argv[1]

    if command == "download50":
        albums = get_top_50_albums(MAIN)
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        end = int(sys.argv[3]) if len(sys.argv) > 3 else len(albums)
        download_album_art(albums[start:end])
    elif command == "downloadother":
        albums = get_other_albums(MAIN)
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        end = int(sys.argv[3]) if len(sys.argv) > 3 else len(albums)
        download_album_art(albums[start:end])
    elif command == "split":
        split_top_50_albums(MAIN, Path("albums"))
        split_top_50_songs(MAIN, Path("songs"))
        split_top_5_eps(MAIN, Path("eps"))
        split_other(MAIN, Path("other"))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
