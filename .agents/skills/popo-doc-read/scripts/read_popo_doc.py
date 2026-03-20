#!/usr/bin/env python3
"""Read a Popo document through the Langbase parse API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse, urlunparse
from urllib.request import Request, urlopen

PARSE_ENDPOINT = "https://langbase.netease.com/api/v1/document/parse-popo"


def normalize_popo_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url:
        raise ValueError("URL is required")

    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Expected an absolute Popo or Langbase URL")

    if parsed.netloc == "langbase.netease.com" and parsed.path == "/api/v1/document/parse-popo":
        nested_urls = parse_qs(parsed.query).get("popo_url")
        if not nested_urls or not nested_urls[0]:
            raise ValueError("Missing popo_url in Langbase parse URL")
        return normalize_popo_url(nested_urls[0])

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def build_api_url(popo_url: str) -> str:
    normalized = normalize_popo_url(popo_url)
    return f"{PARSE_ENDPOINT}?popo_url={quote(normalized, safe='')}"


def fetch_payload(api_url: str, timeout: int) -> dict[str, Any]:
    request = Request(
        api_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "popo-doc-read/1.0",
        },
    )

    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset)

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("API returned a non-object JSON payload")
    return payload


def extract_text(payload: dict[str, Any]) -> str | None:
    candidates: list[Any] = [
        payload.get("text_content"),
        payload.get("content"),
        payload.get("text"),
    ]

    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [
                data.get("text_content"),
                data.get("content"),
                data.get("text"),
                data.get("markdown"),
            ]
        )

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Popo document URL to the Langbase parse URL and print the document text."
    )
    parser.add_argument("url", help="Popo document URL or Langbase parse URL")
    parser.add_argument(
        "--show-api-url",
        action="store_true",
        help="Print the normalized Langbase parse URL before the output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response instead of extracted text",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        api_url = build_api_url(args.url)
        payload = fetch_payload(api_url, args.timeout)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"HTTP {error.code}: {body}", file=sys.stderr)
        return 1
    except URLError as error:
        print(f"Network error: {error}", file=sys.stderr)
        return 1

    if args.show_api_url:
        print(f"API URL: {api_url}")
        if not args.json:
            print()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    text = extract_text(payload)
    if text:
        print(text)
        return 0

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
