import argparse
import csv
import json
import logging
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS = {
    "User-Agent": "HeadlineScraper/1.0"
}


def allowed_by_robots(url):
    """Check whether scraping the URL is allowed by robots.txt."""

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        return rp.can_fetch(HEADERS["User-Agent"], url)

    except Exception as error:
        logging.warning(
            "Could not read robots.txt for %s: %s",
            parsed.netloc,
            error
        )
        return False


def scrape_headlines(url, keyword=None):
    """Scrape headlines from a news webpage."""

    if not allowed_by_robots(url):
        logging.warning(
            "Scraping is not allowed by robots.txt: %s",
            url
        )
        return []

    try:
        logging.info("Fetching: %s", url)

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        # Look for common headline elements
        headline_tags = soup.find_all(
            ["h1", "h2", "h3"]
        )

        for tag in headline_tags:

            title = tag.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            # Keyword filtering
            if keyword and keyword.lower() not in title.lower():
                continue

            link = tag.find("a")

            if link and link.get("href"):
                article_url = urljoin(
                    url,
                    link["href"]
                )
            else:
                article_url = url

            # Try to find a nearby time element
            time_tag = tag.find_next(
                "time"
            )

            published_time = ""

            if time_tag:
                published_time = (
                    time_tag.get("datetime")
                    or time_tag.get_text(
                        " ",
                        strip=True
                    )
                )

            results.append({
                "title": title,
                "url": article_url,
                "time": published_time
            })

        return results

    except requests.exceptions.RequestException as error:
        logging.error(
            "Request failed for %s: %s",
            url,
            error
        )

    except Exception as error:
        logging.error(
            "Scraping failed for %s: %s",
            url,
            error
        )

    return []


def save_csv(data, filename):
    """Save results to CSV."""

    if not data:
        logging.warning("No data to save.")
        return

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "title",
                "url",
                "time"
            ]
        )

        writer.writeheader()
        writer.writerows(data)

    logging.info(
        "Saved %d headlines to %s",
        len(data),
        filename
    )


def save_json(data, filename):
    """Save results to JSON."""

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    logging.info(
        "Saved %d headlines to %s",
        len(data),
        filename
    )


def main():

    parser = argparse.ArgumentParser(
        description="Scrape headlines from news websites."
    )

    parser.add_argument(
        "-u",
        "--urls",
        nargs="+",
        required=True,
        help="One or more news website URLs"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="headlines.json",
        help="Output file (.json or .csv)"
    )

    parser.add_argument(
        "-k",
        "--keyword",
        help="Filter headlines by keyword"
    )

    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=2,
        help="Delay between requests in seconds"
    )

    args = parser.parse_args()

    all_headlines = []

    for url in args.urls:

        headlines = scrape_headlines(
            url,
            args.keyword
        )

        all_headlines.extend(headlines)

        # Respectful delay
        time.sleep(args.delay)

    # Remove duplicate URLs
    unique_headlines = {}

    for headline in all_headlines:
        unique_headlines[headline["url"]] = headline

    all_headlines = list(
        unique_headlines.values()
    )

    # Display results
    print("\nHEADLINES")
    print("=" * 70)

    for headline in all_headlines:
        print(f"Title : {headline['title']}")
        print(f"URL   : {headline['url']}")
        print(f"Time  : {headline['time']}")
        print("-" * 70)

    # Save output
    if args.output.lower().endswith(".csv"):
        save_csv(
            all_headlines,
            args.output
        )

    elif args.output.lower().endswith(".json"):
        save_json(
            all_headlines,
            args.output
        )

    else:
        logging.error(
            "Output file must end with .csv or .json"
        )


if __name__ == "__main__":
    main()