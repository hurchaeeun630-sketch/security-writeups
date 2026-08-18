#!/usr/bin/env python3
"""Import public Naver Blog security posts as English Markdown."""

from __future__ import annotations

import html
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests


BLOG_ID = "chaeeunhur630"
RSS_URL = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
ROOT = Path(__file__).resolve().parents[1]
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (compatible; security-writeups-importer/1.0)"


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.in_main = False
        self.blocks: list[tuple[str, str]] = []
        self.current: list[str] = []
        self.current_tag = ""
        self.pre_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if not self.in_main and tag == "div" and "se-main-container" in classes:
            self.in_main = True
            self.depth = 1
            return
        if not self.in_main:
            return
        if tag == "div":
            self.depth += 1
        if tag in {"p", "h1", "h2", "h3", "h4", "pre"}:
            self.flush()
            self.current_tag = tag
        if tag == "pre":
            self.pre_depth += 1
        if tag == "br":
            self.current.append("\n")
        if tag == "img":
            src = attr.get("data-lazy-src") or attr.get("src")
            if src and not src.startswith("data:"):
                self.flush()
                self.blocks.append(("img", src))

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return
        if tag in {"p", "h1", "h2", "h3", "h4", "pre"}:
            self.flush()
        if tag == "pre" and self.pre_depth:
            self.pre_depth -= 1
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_main:
            self.current.append(data)

    def flush(self) -> None:
        text = html.unescape("".join(self.current)).replace("\u200b", "")
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text:
            kind = "code" if self.current_tag == "pre" or self.pre_depth else "text"
            self.blocks.append((kind, text))
        self.current = []
        self.current_tag = ""


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).lower()
    value = value.replace("collison", "collision")
    value = re.sub(r"(?:dreamhack\.io|pwnable\.kr|reversing\.kr|포너블\.kr|리버싱\.kr)", "", value)
    value = re.sub(r"(?:writeup|problem solving|풀이|문제풀이)", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "untitled"


def destination(title: str, category: str) -> tuple[str, str]:
    low = title.lower()
    if "포너블" in title or "pwnable.kr" in low:
        platform = "pwnable.kr"
    elif "리버싱" in title or "reversing.kr" in low:
        platform = "reversing.kr"
    elif "dreamhack" in low:
        platform = "dreamhack.io"
    elif category == "개념 공부":
        platform = "concepts"
    else:
        platform = "miscellaneous"
    slug = slugify(english_title(title))
    if title.strip().lower() == "dreamhack.io":
        slug = "basic-exploitation-002"
    return platform, slug


def english_title(title: str) -> str:
    replacements = {
        "포너블.kr 문제풀이.": "pwnable.kr:",
        "리버싱.kr 문제풀이.": "reversing.kr:",
        "리버싱.kr 풀이.": "reversing.kr:",
        "BOF 유튜브 실습.": "Buffer Overflow Practice",
        "계산기 띄우기. (유튜브 따라하기)": "Launching Calculator with a Buffer Overflow",
        "각 취약점 정리": "Vulnerability Notes",
        "PIE & RELRO 우회": "Bypassing PIE and RELRO",
    }
    out = replacements.get(title, title)
    out = out.replace("포너블.kr 문제풀이.", "pwnable.kr:")
    out = out.replace("리버싱.kr 문제풀이.", "reversing.kr:")
    out = out.replace("리버싱.kr 풀이.", "reversing.kr:")
    return out.replace("collison", "collision").strip(" []")


def translate(text: str) -> str:
    if not re.search(r"[가-힣]", text):
        return text
    response = SESSION.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "ko", "tl": "en", "dt": "t", "q": text},
        timeout=30,
    )
    response.raise_for_status()
    translated = "".join(part[0] for part in response.json()[0] if part[0])
    return translated.strip()


def translate_blocks(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Translate prose in bounded batches while preserving block boundaries."""
    marker = "\n\nZXQBLOCKZXQ\n\n"
    result = list(blocks)
    pending: list[tuple[int, str]] = []

    def flush_pending() -> None:
        nonlocal pending
        if not pending:
            return
        translated = translate(marker.join(value for _, value in pending))
        parts = re.split(r"\s*ZXQBLOCKZXQ\s*", translated)
        if len(parts) == len(pending):
            for (block_index, _), part in zip(pending, parts):
                result[block_index] = ("text", part.strip())
        pending = []

    size = 0
    for block_index, (kind, value) in enumerate(blocks):
        if kind != "text" or not re.search(r"[가-힣]", value):
            continue
        if pending and size + len(value) + len(marker) > 2800:
            flush_pending()
            size = 0
        pending.append((block_index, value))
        size += len(value) + len(marker)
    flush_pending()
    return result


def download_image(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size:
        return
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    target.write_bytes(response.content)


def image_extension(url: str, content_type: str = "") -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return ext
    return ".png" if "png" in content_type else ".jpg"


def main() -> int:
    rss_response = SESSION.get(RSS_URL, timeout=30)
    rss_response.raise_for_status()
    channel = ET.fromstring(rss_response.content).find("channel")
    assert channel is not None
    items = channel.findall("item")
    items = [item for item in items if (item.findtext("category") or "") != "일상 블로그 for ㄱㅇ ㅅㅎ"]
    manifest = []

    for index, item in enumerate(items, 1):
        title = item.findtext("title") or "Untitled"
        category = item.findtext("category") or ""
        source_url = item.findtext("guid") or item.findtext("link") or ""
        log_no = source_url.rstrip("/").split("/")[-1]
        page_url = f"https://m.blog.naver.com/{BLOG_ID}/{log_no}"
        platform, slug = destination(title, category)
        post_dir = ROOT / "wargames" / platform / slug if platform != "concepts" else ROOT / "concepts" / slug
        assets_dir = post_dir / "images"
        post_dir.mkdir(parents=True, exist_ok=True)

        page = SESSION.get(page_url, timeout=30)
        page.raise_for_status()
        parser = ArticleParser()
        parser.feed(page.text)
        parser.flush()
        try:
            parser.blocks = translate_blocks(parser.blocks)
        except Exception as exc:
            print(f"translation warning for {title}: {exc}", file=sys.stderr)

        output = [
            f"# {english_title(title)}",
            "",
            f"> Originally published on [Naver Blog]({source_url}). Translated and reformatted in English.",
            "",
        ]
        image_number = 0
        for kind, value in parser.blocks:
            if kind == "img":
                image_number += 1
                assets_dir.mkdir(exist_ok=True)
                ext = image_extension(value)
                filename = f"figure-{image_number:02d}{ext}"
                try:
                    download_image(value, assets_dir / filename)
                    output.extend([f"![Figure {image_number}](images/{filename})", ""])
                except requests.RequestException:
                    output.extend([f"![Figure {image_number}]({value})", ""])
            elif kind == "code":
                output.extend(["```text", value, "```", ""])
            else:
                output.extend([value, ""])

        (post_dir / "README.md").write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
        manifest.append({"title": english_title(title), "platform": platform, "slug": slug, "source": source_url})
        print(f"[{index:02d}/{len(items)}] {platform}/{slug}")

    (ROOT / "tools" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
