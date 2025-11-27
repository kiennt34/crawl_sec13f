#!/usr/bin/env python3
"""
Extract ZIP file links from IAPD (Investment Adviser Public Disclosure) page.

The IAPD page at https://adviserinfo.sec.gov/adv is a JavaScript-rendered SPA,
so we need to use browser automation to wait for the content to load.

Usage:
    python extract_iapd_zip.py [--url URL] [--output output.json]
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

# Try to import webdriver-manager for automatic ChromeDriver management
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_driver(headless: bool = True, use_webdriver_manager: bool = True) -> webdriver.Chrome:
    """
    Setup Chrome WebDriver with appropriate options for headless server.
    
    Args:
        headless: Whether to run browser in headless mode (required for headless servers)
        use_webdriver_manager: Whether to use webdriver-manager (auto-downloads ChromeDriver)
        
    Returns:
        Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    
    # Essential options for headless server
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Additional compatibility options
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Try to initialize driver
    import shutil
    
    # Strategy 1: Use webdriver-manager if available
    if use_webdriver_manager and WEBDRIVER_MANAGER_AVAILABLE:
        try:
            logger.info("Using webdriver-manager to get ChromeDriver...")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Successfully initialized Chrome WebDriver using webdriver-manager")
            return driver
        except Exception as e:
            logger.debug(f"webdriver-manager failed: {e}")
    
    # Strategy 2: Use system ChromeDriver
    chromedriver_path = shutil.which("chromedriver")
    if chromedriver_path:
        try:
            logger.info(f"Using system ChromeDriver at: {chromedriver_path}")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Successfully initialized Chrome WebDriver using system ChromeDriver")
            return driver
        except Exception as e:
            logger.debug(f"System ChromeDriver failed: {e}")
    
    # Strategy 3: Let Selenium auto-detect ChromeDriver
    try:
        logger.info("Trying auto-detection of ChromeDriver...")
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Successfully initialized Chrome WebDriver using auto-detection")
        return driver
    except Exception as e:
        logger.debug(f"Auto-detection failed: {e}")
    
    # All strategies failed
    logger.error("=" * 60)
    logger.error("Failed to initialize Chrome WebDriver")
    logger.error("=" * 60)
    logger.error("Make sure Chromium and ChromeDriver are installed:")
    logger.error("  chromium-browser --version")
    logger.error("  chromedriver --version")
    logger.error("=" * 60)
    raise WebDriverException("Failed to initialize Chrome WebDriver: All strategies failed")


def find_elements_by_strategy(driver, strategy: dict, wait_time: int = 30) -> List:
    """
    Find ALL elements matching a specific strategy.
    
    Args:
        driver: WebDriver instance
        strategy: Dictionary containing strategy details:
            - type: 'text', 'class', 'css', 'xpath', 'id'
            - value: The value to search for
            - description: Optional description of the strategy
        wait_time: Maximum time to wait (seconds)
        
    Returns:
        List of WebElements found (may be empty)
    """
    strategy_type = strategy.get('type', '').lower()
    value = strategy.get('value', '')
    description = strategy.get('description', f"{strategy_type}: {value}")
    
    logger.debug(f"Trying strategy: {description}")
    
    try:
        if strategy_type == 'text':
            # Find by text content (case-insensitive)
            xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{value.lower()}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            
        elif strategy_type == 'class':
            # Find by class name
            elements = driver.find_elements(By.CLASS_NAME, value)
            
        elif strategy_type == 'css':
            # Find by CSS selector
            elements = driver.find_elements(By.CSS_SELECTOR, value)
            
        elif strategy_type == 'xpath':
            # Find by XPath
            elements = driver.find_elements(By.XPATH, value)
            
        elif strategy_type == 'id':
            # Find by ID
            element = driver.find_element(By.ID, value)
            elements = [element] if element else []
            
        else:
            logger.warning(f"Unknown strategy type: {strategy_type}")
            return []
        
        # Filter to clickable, visible elements
        visible_elements = []
        for elem in elements:
            try:
                if elem.is_displayed() and elem.is_enabled():
                    visible_elements.append(elem)
            except Exception:
                continue
        
        if visible_elements:
            logger.info(f"Found {len(visible_elements)} element(s) using strategy: {description}")
            for i, elem in enumerate(visible_elements, 1):
                logger.debug(f"  Element {i}: tag={elem.tag_name}, text={elem.text[:100]}")
        
        return visible_elements
                
    except Exception as e:
        logger.debug(f"Strategy '{description}' failed: {e}")
    
    return []


def find_element_by_strategy(driver, strategy: dict, wait_time: int = 30):
    """
    Find first element matching a specific strategy.
    
    Args:
        driver: WebDriver instance
        strategy: Dictionary containing strategy details:
            - type: 'text', 'class', 'css', 'xpath', 'id'
            - value: The value to search for
            - description: Optional description of the strategy
        wait_time: Maximum time to wait (seconds)
        
    Returns:
        WebElement if found, None otherwise
    """
    elements = find_elements_by_strategy(driver, strategy, wait_time)
    return elements[0] if elements else None


def click_element(driver, element, description: str = "element") -> bool:
    """
    Click on an element with proper scrolling and error handling.
    
    Args:
        driver: WebDriver instance
        element: WebElement to click
        description: Description of the element for logging
        
    Returns:
        True if click was successful, False otherwise
    """
    try:
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)
        
        # Try regular click first
        try:
            logger.info(f"Clicking on {description}")
            element.click()
        except Exception as e:
            # If regular click fails, try JavaScript click
            logger.debug(f"Regular click failed, trying JavaScript click: {e}")
            driver.execute_script("arguments[0].click();", element)
        
        # Wait for content to load
        time.sleep(2)
        
        logger.info(f"Successfully clicked on {description}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to click {description}: {e}")
        return False


def click_all_by_strategy(driver, strategy: dict, wait_time: int = 30, click_all: bool = True) -> int:
    """
    Find and click ALL elements matching a strategy.
    
    Args:
        driver: WebDriver instance
        strategy: Strategy dictionary containing:
            - type: 'text', 'class', 'css', 'xpath', 'id'
            - value: The value to search for
            - description: Optional description
            - click_all: If True (default), click all matches. If False, click only first match.
        wait_time: Maximum time to wait (seconds)
        click_all: If True, click all matches; if False, click only first match
        
    Returns:
        Number of elements successfully clicked
    """
    # Check if click_all is specified in strategy, otherwise use parameter
    should_click_all = strategy.get('click_all', click_all)
    
    description = strategy.get('description', f"{strategy.get('type')}: {strategy.get('value')}")
    logger.info(f"Finding elements with strategy: {description}")
    
    elements = find_elements_by_strategy(driver, strategy, wait_time)
    
    if not elements:
        logger.warning(f"No elements found for strategy: {description}")
        return 0
    
    if not should_click_all:
        # Click only the first element
        logger.info(f"Clicking first match only (found {len(elements)} total)")
        if click_element(driver, elements[0], f"{description} [1/1]"):
            return 1
        return 0
    
    # Click all matching elements
    logger.info(f"Found {len(elements)} matching element(s), will click all")
    clicked_count = 0
    
    for i, elem in enumerate(elements, 1):
        elem_desc = f"{description} [{i}/{len(elements)}]"
        if click_element(driver, elem, elem_desc):
            clicked_count += 1
            # Wait a bit between clicks to let content load
            time.sleep(1)
        else:
            logger.warning(f"Failed to click element {i}/{len(elements)}")
    
    logger.info(f"Successfully clicked {clicked_count}/{len(elements)} element(s)")
    return clicked_count


def click_by_strategies(driver, strategies: List[dict], wait_time: int = 30, click_all: bool = False, 
                       stop_on_first_success: bool = True) -> bool:
    """
    Try multiple strategies to find and click element(s).
    
    Args:
        driver: WebDriver instance
        strategies: List of strategy dictionaries, each containing:
            - type: 'text', 'class', 'css', 'xpath', 'id'
            - value: The value to search for
            - description: Optional description
            - click_all: Optional, if True, click all matches for this strategy
        wait_time: Maximum time to wait (seconds)
        click_all: Default behavior - if True, click all matches; if False, click first match only
        stop_on_first_success: If True, stop after first successful strategy (fallback behavior).
                               If False, execute ALL strategies regardless of success (batch behavior).
        
    Returns:
        True if any strategy succeeded in clicking at least one element, False otherwise
        
    Example:
        # Fallback mode (stop after first success)
        strategies = [
            {'type': 'class', 'value': 'accordion-header'},
            {'type': 'css', 'value': 'div.accordion-header h3'},
            {'type': 'text', 'value': 'Form ADV Part', 'click_all': True},
        ]
        click_by_strategies(driver, strategies, stop_on_first_success=True)
        
        # Batch mode (execute all strategies)
        strategies = [
            {'type': 'text', 'value': 'Form ADV Part 1'},
            {'type': 'text', 'value': 'Form ADV Part 2'},
            {'type': 'text', 'value': 'Form ADV Part 3'},
        ]
        click_by_strategies(driver, strategies, stop_on_first_success=False)
    """
    logger.info(f"Attempting to click using {len(strategies)} strategies (stop_on_first_success={stop_on_first_success})...")
    
    any_success = False
    
    for i, strategy in enumerate(strategies, 1):
        logger.info(f"Strategy {i}/{len(strategies)}: {strategy.get('description', strategy.get('type'))}")
        
        # Check if this specific strategy wants to click all matches
        strategy_click_all = strategy.get('click_all', click_all)
        
        if strategy_click_all:
            # Click all matching elements for this strategy
            clicked = click_all_by_strategy(driver, strategy, wait_time, click_all=True)
            if clicked > 0:
                any_success = True
                if stop_on_first_success:
                    logger.info(f"Strategy succeeded, stopping (stop_on_first_success=True)")
                    return True
        else:
            # Click only first match (original behavior)
            element = find_element_by_strategy(driver, strategy, wait_time)
            if element:
                description = strategy.get('description', f"{strategy.get('type')}: {strategy.get('value')}")
                if click_element(driver, element, description):
                    any_success = True
                    if stop_on_first_success:
                        logger.info(f"Strategy succeeded, stopping (stop_on_first_success=True)")
                        return True
    
    if not any_success:
        logger.warning("All strategies failed to find/click element")
    else:
        logger.info(f"Completed all {len(strategies)} strategies")
    
    return any_success


def click_and_wait_for_content(driver, click_text: str, wait_time: int = 30) -> bool:
    """
    Find and click on an element containing specific text, then wait for content to appear.
    
    This is a legacy function for backward compatibility. For more control, use click_by_strategies().
    
    Args:
        driver: WebDriver instance
        click_text: Text to search for in links/buttons (case-insensitive)
        wait_time: Maximum time to wait (seconds)
        
    Returns:
        True if click was successful, False otherwise
    """
    logger.info(f"Searching for element containing text: '{click_text}'")
    
    # Build strategies automatically based on text
    strategies = [
        {'type': 'text', 'value': click_text, 'description': f'Any element containing text "{click_text}"'},
        {'type': 'xpath', 'value': f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{click_text.lower()}')]", 
         'description': f'Link containing "{click_text}"'},
        {'type': 'xpath', 'value': f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{click_text.lower()}')]",
         'description': f'Button containing "{click_text}"'},
        {'type': 'xpath', 'value': f"//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{click_text.lower()}')]",
         'description': f'H3 heading containing "{click_text}"'},
    ]
    
    return click_by_strategies(driver, strategies, wait_time)


def extract_zip_links_selenium(url: str, wait_time: int = 30, click_text: str = None, 
                              click_strategies: List[dict] = None, headless: bool = True,
                              file_type: str = '.zip', save_path: str = None) -> List[str]:
    """
    Extract file links from a page using Selenium.
    
    Args:
        url: URL of the page
        wait_time: Maximum time to wait for page to load (seconds)
        click_text: DEPRECATED - Text to click on (use click_strategies instead)
        click_strategies: List of strategies to try for clicking elements. Each dict should have:
            - type: 'text', 'class', 'css', 'xpath', 'id'
            - value: The value to search for
            - description: Optional description
        headless: Whether to run browser in headless mode
        file_type: File extension to search for (e.g., '.zip', '.pdf', '.txt', '.mp3')
        save_path: Optional path to save the final HTML content
        
    Returns:
        List of file URLs found on the page matching the file_type
    """
    driver = None
    file_urls: Set[str] = set()
    
    # Normalize file_type to ensure it starts with a dot
    if not file_type.startswith('.'):
        file_type = '.' + file_type
    
    logger.info(f"Searching for files with extension: {file_type}")
    
    try:
        logger.info(f"Setting up browser...")
        driver = setup_driver(headless=headless)
        
        logger.info(f"Loading page: {url}")
        driver.get(url)
        
        # Wait for the Angular app to load (wait for iapd-root to have content)
        logger.info("Waiting for page content to load...")
        try:
            # Wait for any links to appear (indicating the page has loaded)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )
            
            # Give additional time for dynamic content to load
            time.sleep(5)
            
            # Handle clicking to reveal content
            if click_strategies:
                logger.info(f"Attempting to click using {len(click_strategies)} strategies")
                # When multiple strategies are provided, execute ALL of them (don't stop on first success)
                # This allows clicking multiple accordions/sections like "Part 1", "Part 2", etc.
                stop_on_first = len(click_strategies) == 1  # Only stop if single strategy (fallback mode)
                if click_by_strategies(driver, click_strategies, wait_time, stop_on_first_success=stop_on_first):
                    logger.info("Content should now be visible, waiting a bit more...")
                    time.sleep(3)
                else:
                    logger.warning("Could not find/click element with any strategy, continuing anyway...")
            elif click_text:
                # Backward compatibility: use old text-based method
                logger.info(f"Attempting to click on element containing: '{click_text}'")
                if click_and_wait_for_content(driver, click_text, wait_time):
                    logger.info("Content should now be visible, waiting a bit more...")
                    time.sleep(3)
                else:
                    logger.warning(f"Could not find/click element with text '{click_text}', continuing anyway...")
            
            # Save HTML content if requested
            if save_path:
                try:
                    html_content = driver.page_source
                    save_file_path = Path(save_path)
                    save_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(save_file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f"Saved HTML content to: {save_path}")
                except Exception as e:
                    logger.warning(f"Failed to save HTML content: {e}")
            
            # Try multiple strategies to find file links
            logger.info(f"Searching for {file_type} files...")
            
            # Strategy 1: Find all links and filter for file_type
            all_links = driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Found {len(all_links)} total links")
            
            # Log some link details for debugging
            logger.debug("Sample links found:")
            for i, link in enumerate(all_links[:10]):  # Log first 10 links
                try:
                    href = link.get_attribute("href")
                    text = link.text
                    logger.debug(f"  Link {i+1}: text='{text[:50]}', href='{href[:100] if href else None}'")
                except Exception:
                    pass
            
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if href and href.lower().endswith(file_type.lower()):
                        # Normalize URL
                        if href.startswith('http://') or href.startswith('https://'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = urljoin(url, href)
                        else:
                            full_url = urljoin(url, href)
                        file_urls.add(full_url)
                        logger.info(f"Found {file_type} link: {full_url}")
                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue
            
            # Strategy 2: Search by partial href containing file_type
            try:
                file_elements = driver.find_elements(By.XPATH, f"//a[contains(@href, '{file_type}')]")
                for elem in file_elements:
                    href = elem.get_attribute("href")
                    if href:
                        if href.startswith('http://') or href.startswith('https://'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = urljoin(url, href)
                        else:
                            full_url = urljoin(url, href)
                        file_urls.add(full_url)
                        logger.info(f"Found {file_type} link (XPath): {full_url}")
            except Exception as e:
                logger.debug(f"XPath search failed: {e}")
            
            # Strategy 3: Get page source and search for file patterns
            page_source = driver.page_source
            import re
            # Escape special regex characters in file_type and build pattern
            escaped_ext = re.escape(file_type)
            file_pattern = rf'https?://[^\s<>"]+{escaped_ext}'
            matches = re.findall(file_pattern, page_source, re.IGNORECASE)
            for match in matches:
                file_urls.add(match)
                logger.info(f"Found {file_type} link (regex): {match}")
            
            # Strategy 4: Check if there's a download button or link with specific text
            try:
                download_links = driver.find_elements(By.XPATH, 
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]")
                for link in download_links:
                    href = link.get_attribute("href")
                    if href and file_type.lower() in href.lower():
                        if href.startswith('http://') or href.startswith('https://'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = urljoin(url, href)
                        else:
                            full_url = urljoin(url, href)
                        file_urls.add(full_url)
                        logger.info(f"Found {file_type} link (download text): {full_url}")
            except Exception as e:
                logger.debug(f"Download text search failed: {e}")
                
        except TimeoutException:
            logger.warning(f"Timeout waiting for page to load after {wait_time} seconds")
            logger.info("Trying to extract links from partially loaded page...")
            # Still try to extract what we can
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if href and href.lower().endswith(file_type.lower()):
                        if href.startswith('http://') or href.startswith('https://'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = urljoin(url, href)
                        else:
                            full_url = urljoin(url, href)
                        file_urls.add(full_url)
                except Exception:
                    continue
        
        sorted_urls = sorted(file_urls)
        logger.info(f"Found {len(sorted_urls)} unique {file_type} file(s)")
        
        return sorted_urls
        
    except Exception as e:
        logger.error(f"Error extracting ZIP links: {e}", exc_info=True)
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract ZIP links from IAPD page")
    
    parser.add_argument(
        "--url",
        type=str,
        default="https://adviserinfo.sec.gov/adv",
        help="IAPD page URL (default: https://adviserinfo.sec.gov/adv)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="iapd_zips.json",
        help="Output JSON file path (default: iapd_zips.json)"
    )
    
    parser.add_argument(
        "--wait-time",
        type=int,
        default=30,
        help="Maximum time to wait for page to load in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    
    parser.add_argument(
        "--click-text",
        type=str,
        default="Form ADV Part 1 Data Files",
        help="Text to click on to reveal zip links (default: 'Form ADV Part 1 Data Files')"
    )
    
    parser.add_argument(
        "--no-click",
        action="store_true",
        help="Skip clicking on any element (just search for zip links directly)"
    )
    
    parser.add_argument(
        "--click-strategy",
        type=str,
        choices=['text', 'class', 'css', 'xpath'],
        help="Strategy type to use for clicking: text, class, css, or xpath"
    )
    
    parser.add_argument(
        "--click-value",
        type=str,
        help="Value for the click strategy (e.g., class name, CSS selector, XPath expression)"
    )
    
    parser.add_argument(
        "--click-all",
        action="store_true",
        help="Click ALL matching elements, not just the first one (useful for multiple accordions)"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info(f"[IAPD ZIP Extractor] URL: {args.url}")
        
        # Prepare click strategies
        click_strategies = None
        
        if not args.no_click:
            if args.click_strategy and args.click_value:
                # Use custom strategy provided via CLI
                click_strategies = [
                    {
                        'type': args.click_strategy, 
                        'value': args.click_value,
                        'click_all': args.click_all
                    }
                ]
                logger.info(f"Using custom click strategy: {args.click_strategy} = {args.click_value} (click_all={args.click_all})")
            elif args.click_text:
                # Use text-based strategy (default behavior)
                click_strategies = [
                    {
                        'type': 'text', 
                        'value': args.click_text,
                        'click_all': args.click_all
                    }
                ]
                logger.info(f"Using text-based strategy: {args.click_text} (click_all={args.click_all})")
            else:
                # Default strategies for accordion expansion
                click_strategies = [
                    {'type': 'class', 'value': 'accordion-header', 'description': 'Accordion header by class', 'click_all': args.click_all},
                    {'type': 'css', 'value': 'div.accordion-header', 'description': 'Accordion header by CSS', 'click_all': args.click_all},
                    {'type': 'text', 'value': 'Form ADV Part 1', 'description': 'Text: Form ADV Part 1', 'click_all': args.click_all},
                ]
        
        # Extract ZIP URLs
        headless_mode = args.headless
        zip_urls = extract_zip_links_selenium(
            args.url, 
            wait_time=args.wait_time, 
            click_strategies=click_strategies,
            headless=headless_mode
        )
        
        if not zip_urls:
            logger.warning("No ZIP files found on the page")
            logger.info("The page might require additional navigation or the ZIP link might be behind a button/click")
            logger.info("You may need to manually inspect the page or modify the script to handle specific interactions")
            sys.exit(1)
        
        # Prepare output data
        output_data = {
            "source_url": args.url,
            "extracted_at": None,
            "zip_count": len(zip_urls),
            "zip_files": [
                {
                    "url": url,
                    "filename": Path(urlparse(url).path).name
                }
                for url in zip_urls
            ]
        }
        
        # Add timestamp
        from datetime import datetime
        output_data["extracted_at"] = datetime.utcnow().isoformat()
        
        # Write output JSON
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Extracted {len(zip_urls)} ZIP file(s)")
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(f"\nExtraction Complete: Found {len(zip_urls)} ZIP file(s)")
        for i, url in enumerate(zip_urls, 1):
            print(f"  {i}. {url}")
        print(f"\nOutput: {output_path}")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

