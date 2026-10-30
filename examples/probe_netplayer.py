"""Inspect Netplayer's public WRIF page without collecting or storing songs.

This is a manual, one-request diagnostic. Check site terms and robots rules
before developing an automated poller. No HTML or audio is saved.
"""
from __future__ import annotations

import argparse
import json
import asyncio
import re
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

WRIF_URL = "https://netplayer.net/radio/101-wrif-64370/recently-played"



class RowInspector(HTMLParser):
    """Find timestamp-bearing ancestor elements and their visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, object]] = []
        self.rows: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        node: dict[str, object] = {"tag": tag, "class": attributes.get("class", ""), "text": []}
        self.stack.append(node)
        if tag == "time" and (attributes.get("datetime") or attributes.get("dateTime")):
            stamp = attributes.get("datetime") or attributes.get("dateTime")
            # Netplayer uses a station header time plus per-song times.
            candidates = [
                n for n in reversed(self.stack[:-1])
                if n["tag"] in ("div", "article", "li")
            ]
            self.rows.append({
                "timestamp": stamp,
                "ancestors": [{"tag": n["tag"], "class": n["class"]} for n in candidates[:7]],
                "nodes": candidates[:7],
            })

    def handle_data(self, data: str) -> None:
        for node in self.stack:
            node["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return


def row_samples(html: str) -> list[dict[str, object]]:
    parser = RowInspector()
    parser.feed(html)
    results = []
    for row in parser.rows:
        if len(results) >= 4:
            break
        ancestors = row["nodes"]
        texts = [
            {"class": n["class"], "text": re.sub(r"\\s+", " ", "".join(n["text"])).strip()[:400]}
            for n in ancestors
        ]
        if any("Playlist updated" in item["text"] for item in texts[:3]):
            continue
        results.append({
            "timestamp": row["timestamp"],
            "ancestors": row["ancestors"],
            "ancestor_texts": texts,
        })
    return results


def inspect_html(html: str) -> dict[str, object]:
    title = re.search(r"<title\b[^>]*>(.*?)</title\s*>", html, re.I | re.S)
    clean_title = unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else None
    scripts = sorted(set(re.findall(
        r'<script\b[^>]*\btype=["\'](application/(?:ld\+json|json))["\']',
        html, re.I,
    )))
    times = sorted(set(re.findall(
        r'<time\b[^>]*\bdatetime=["\']([^"\']{1,80})', html, re.I,
    )))
    ld_types = []
    for match in re.finditer(r"<script\b[^>]*>(.*?)</script>", html, re.I | re.S):
        try:
            if "application/ld+json" not in match.group(0).split(">", 1)[0].lower():
                continue
            data = json.loads(match.group(1))
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    ld_types.append({"type": item.get("@type"), "keys": sorted(item.keys())[:20]})
        except json.JSONDecodeError:
            ld_types.append({"error": "invalid_json_ld"})
    time_tags = list(re.finditer(r"<time\b[^>]*\bdatetime=[\x27\x22][^\x27\x22]+[\x27\x22][^>]*>", html, re.I))
    time_tag = max(time_tags, key=lambda m: m.group(0)) if time_tags else None
    context = None
    if time_tag:
        context = html[max(0, time_tag.start() - 800):time_tag.end() + 800]
        context = re.sub(r"<script\b.*?</script>", "[script omitted]", context, flags=re.I | re.S)
        context = re.sub(r'<[^>]+>', " ", context)
        context = unescape(re.sub(r"\s+", " ", context)).strip()[:1000]
    # Show the structural context for several time elements, excluding the
    # station-level "Playlist updated" timestamp.
    timestamp_samples = []
    for tag in time_tags:
        before = html[max(0, tag.start() - 1100):tag.start()]
        if "Playlist updated" in before[-120:]:
            continue
        nearby = html[max(0, tag.start() - 550):tag.end() + 150]
        timestamp_samples.append({
            "time_tag": tag.group(0),
            "preceding_html": nearby[:700],
        })
        if len(timestamp_samples) == 3:
            break
    return {
        "song_container_samples": row_samples(html),
        "timestamp_row_samples": timestamp_samples,
        "json_ld_summary": ld_types,
        "latest_timestamp_context": context,
        "newest_timestamp_tag": time_tag.group(0) if time_tag else None,
        "latest_timestamp_html_excerpt": (
            html[max(0, time_tag.start() - 250):time_tag.end() + 300]
            .replace("\\n", " ")[:600] if time_tag else None
        ),
        "page_title": clean_title,
        "structured_script_types": scripts,
        "html_time_elements": len(times),
        "recent_time_examples": times[-5:],
        "next_data_marker": "__NEXT_DATA__" in html,
        "next_flight_marker": "self.__next_f.push" in html,
        "json_ld_marker": "application/ld+json" in html,
        "wrif_mentions": len(re.findall(r"\bWRIF\b", html, re.I)),
        "html_bytes": len(html.encode("utf-8")),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=WRIF_URL)
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or parsed.hostname != "netplayer.net":
        parser.error("This probe only accepts https://netplayer.net URLs")
    print(f"probe_utc={datetime.now(timezone.utc).isoformat()}", flush=True)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            response = await client.get(args.url, headers={
                "User-Agent": "libMusicForge-research-probe/0.1",
                "Accept": "text/html",
            })
            print(f"status={response.status_code} final_url={response.url}", flush=True)
            response.raise_for_status()
            print(f"content_type={response.headers.get('content-type')}", flush=True)
            if "text/html" not in response.headers.get("content-type", "").lower():
                print("not_html=true", flush=True)
                return
            for key, value in inspect_html(response.text).items():
                print(f"{key}={value}", flush=True)
        except httpx.HTTPError as exc:
            print(f"request_error={type(exc).__name__}: {exc}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
