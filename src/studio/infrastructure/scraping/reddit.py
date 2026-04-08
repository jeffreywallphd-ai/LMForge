"""Reddit scraping adapter.

Migrated from the legacy ``lmforge_core.views.scrape`` implementation,
with reusable pure functions and explicit result metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass(slots=True)
class RedditScrapeResult:
    file_type: str
    content: str
    extracted_title: str = ""


class RedditScraper:
    user_agent = "LMForge-Studio-Scraper/1.0"

    def scrape(self, url: str, *, delay_seconds: float = 0.5) -> RedditScrapeResult:
        parsed_url = urlparse(url)
        if "/comments/" in parsed_url.path:
            return self._scrape_post(url, delay_seconds=delay_seconds)
        if parsed_url.path.startswith("/r/"):
            return self._scrape_subreddit(parsed_url.path.split("/")[2], delay_seconds=delay_seconds)
        raise ValueError("Invalid Reddit URL. Must target a subreddit or specific post.")

    def _scrape_post(self, url: str, *, delay_seconds: float) -> RedditScrapeResult:
        headers = {"User-Agent": self.user_agent}
        api_url = url.rstrip("/") + ".json"
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        post_data = data[0]["data"]["children"][0]["data"]
        post_title = post_data.get("title", "No Title")
        post_author = post_data.get("author", "Unknown Author")
        post_text = post_data.get("selftext", "No content text.")

        content_lines = [
            f"Title: {post_title}",
            f"Author: u/{post_author}",
            "--- POST CONTENT ---",
            post_text,
            "\n--- COMMENTS ---",
        ]

        comments_data = data[1]["data"]["children"]
        self._append_comments(content_lines, comments_data)

        return RedditScrapeResult(
            file_type="reddit_post",
            content="\n".join(content_lines),
            extracted_title=post_title,
        )

    def _scrape_subreddit(self, subreddit_name: str, *, delay_seconds: float) -> RedditScrapeResult:
        headers = {"User-Agent": self.user_agent}
        base_api_url = f"https://www.reddit.com/r/{subreddit_name}"

        content_lines = [f"Scraped Posts and Comments from r/{subreddit_name} (All Filters):\n" + "=" * 40]

        simple_filters = ["hot", "new", "rising", "best"]
        top_filters = [
            ("hour", "Now (Top)"),
            ("day", "Today (Top)"),
            ("week", "This Week (Top)"),
            ("month", "This Month (Top)"),
            ("year", "This Year (Top)"),
            ("all", "All Time (Top)"),
        ]

        all_posts_to_scrape: list[dict[str, Any]] = []
        seen_post_ids: set[str] = set()

        for listing in simple_filters:
            self._collect_listing_posts(
                f"{base_api_url}/{listing}.json?limit=25",
                headers=headers,
                seen_post_ids=seen_post_ids,
                all_posts_to_scrape=all_posts_to_scrape,
                delay_seconds=delay_seconds,
            )

        for top_param, _label in top_filters:
            self._collect_listing_posts(
                f"{base_api_url}/top.json?t={top_param}&limit=25",
                headers=headers,
                seen_post_ids=seen_post_ids,
                all_posts_to_scrape=all_posts_to_scrape,
                delay_seconds=delay_seconds,
            )

        for post_item in all_posts_to_scrape:
            post_data = post_item["data"]
            post_title = post_data.get("title", "No Title")
            permalink = post_data.get("permalink")
            if not permalink:
                content_lines.append(f"\n[Skipping post with no permalink: {post_title}]")
                continue

            post_api_url = f"https://www.reddit.com{permalink.rstrip('/')}.json"
            content_lines.append(f"\n\n{'=' * 20}\nPOST: {post_title}\n{'=' * 20}")

            try:
                time.sleep(delay_seconds)
                post_response = requests.get(post_api_url, headers=headers, timeout=30)
                post_response.raise_for_status()
                post_and_comment_data = post_response.json()

                post_content_data = post_and_comment_data[0]["data"]["children"][0]["data"]
                post_text = post_content_data.get("selftext", "")
                post_author = post_content_data.get("author", "Unknown")

                content_lines.append(f"Author: u/{post_author}")
                if post_text:
                    content_lines.append(f"\n--- POST CONTENT ---\n{post_text}\n")
                else:
                    content_lines.append("\n[No self-text for this post.]\n")

                content_lines.append("--- COMMENTS ---")
                comments_data = post_and_comment_data[1]["data"]["children"]
                before_count = len(content_lines)
                self._append_comments(content_lines, comments_data)
                if len(content_lines) == before_count:
                    content_lines.append("No comments found for this post.")
            except Exception as exc:  # noqa: BLE001
                content_lines.append(f"\n[Could not fetch content for post '{post_title}'. Error: {exc}]")

        return RedditScrapeResult(
            file_type="reddit_subreddit_full",
            content="\n".join(content_lines),
            extracted_title=f"Scrape of r/{subreddit_name}",
        )

    def _collect_listing_posts(
        self,
        listing_url: str,
        *,
        headers: dict[str, str],
        seen_post_ids: set[str],
        all_posts_to_scrape: list[dict[str, Any]],
        delay_seconds: float,
    ) -> None:
        time.sleep(delay_seconds)
        response = requests.get(listing_url, headers=headers, timeout=30)
        response.raise_for_status()
        posts = response.json().get("data", {}).get("children", [])
        for post_item in posts:
            post_id = post_item.get("data", {}).get("id")
            if post_id and post_id not in seen_post_ids:
                all_posts_to_scrape.append(post_item)
                seen_post_ids.add(post_id)

    def _append_comments(self, content_lines: list[str], comment_list: list[dict[str, Any]], depth: int = 0) -> None:
        if not comment_list:
            return
        for comment in comment_list:
            if comment.get("kind") != "t1":
                continue
            if "data" not in comment or "body" not in comment["data"]:
                continue
            comment_author = comment["data"].get("author", "Unknown")
            comment_body = comment["data"].get("body", "")
            indent = "  " * depth
            formatted = comment_body.replace("\n", "\n" + indent)
            content_lines.append(f"\n{indent}> u/{comment_author}:\n{indent}{formatted}\n")

            replies = comment["data"].get("replies")
            if replies and isinstance(replies, dict):
                children = replies.get("data", {}).get("children", [])
                self._append_comments(content_lines, children, depth + 1)
