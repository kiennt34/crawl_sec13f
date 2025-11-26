#!/usr/bin/env python3
"""
Step 1: Crawl SEC index page and discover ZIP file URLs.

This script:
- Fetches the SEC Form 13F data sets index page
- Parses HTML to find all ZIP file links
- Outputs a JSON file with discovered ZIP URLs

Usage:
    python step1_crawl.py [--output output.json]
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_index_page(url: str) -> str:
    """
    Fetch the SEC index page HTML.
    
    Args:
        url: URL of the SEC index page
        
    Returns:
        HTML content as string
        
    Raises:
        requests.RequestException: If the request fails
    """
    headers = {
        "User-Agent": Config.USER_AGENT
    }
    
    logger.info(f"Fetching index page: {url}")
    
    for attempt in range(Config.MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            logger.info(f"Successfully fetched index page ({len(response.text)} bytes)")
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {e}")
            if attempt < Config.MAX_RETRIES - 1:
                import time
                time.sleep(Config.RETRY_DELAY * (attempt + 1))
            else:
                raise


def extract_zip_urls(html: str, base_url: str) -> List[str]:
    """
    Extract ZIP file URLs from HTML.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative URLs
        
    Returns:
        List of normalized ZIP URLs
    """
    soup = BeautifulSoup(html, 'html.parser')
    zip_urls: Set[str] = set()
    
    # Find all <a> tags with href ending in .zip
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # Check if it's a ZIP file
        if href.lower().endswith('.zip'):
            # Normalize URL
            if href.startswith('http://') or href.startswith('https://'):
                full_url = href
            elif href.startswith('/'):
                full_url = urljoin(base_url, href)
            else:
                full_url = urljoin(base_url, href)
            
            zip_urls.add(full_url)
            logger.debug(f"Found ZIP: {full_url}")
    
    # Sort for consistent output
    sorted_urls = sorted(zip_urls)
    logger.info(f"Found {len(sorted_urls)} ZIP files")
    
    return sorted_urls


def get_zip_filename(zip_url: str) -> str:
    """
    Extract filename from ZIP URL.
    
    Args:
        zip_url: Full URL to ZIP file
        
    Returns:
        Filename (e.g., "2025-june-july-august-form13f.zip")
    """
    return Path(urlparse(zip_url).path).name


def main():
    """Main entry point for step 1."""
    parser = argparse.ArgumentParser(description="Crawl SEC index and discover ZIP files")
    parser.add_argument(
        "--output",
        type=str,
        default="discovered_zips.json",
        help="Output JSON file path (default: discovered_zips.json)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Override SEC index URL (default: from config)"
    )
    
    args = parser.parse_args()
    
    try:
        # Get URL
        index_url = args.url or Config.SEC_INDEX_URL
        
        logger.info(f"[STEP 1] Index URL: {index_url}")
        
        # Fetch index page
        html = fetch_index_page(index_url)
        
        # Extract ZIP URLs
        zip_urls = extract_zip_urls(html, index_url)
        
        if not zip_urls:
            logger.warning("[STEP 1] No ZIP files found on the index page")
            sys.exit(1)
        
        # Prepare output data
        output_data = {
            "index_url": index_url,
            "discovered_at": None,  # Will be set by json.dump
            "zip_count": len(zip_urls),
            "zip_files": [
                {
                    "url": url,
                    "filename": get_zip_filename(url)
                }
                for url in zip_urls
            ]
        }
        
        logger.info(f"[STEP 1] Output data: {output_data}")
        
        # Add timestamp
        from datetime import datetime
        output_data["discovered_at"] = datetime.utcnow().isoformat()
        
        # Write output JSON
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[STEP 1] Output path: {output_path}")
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Discovered {len(zip_urls)} ZIP files")
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(f"\nStep 1 Complete: Discovered {len(zip_urls)} ZIP files")
        print(f"  Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Step 1 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

