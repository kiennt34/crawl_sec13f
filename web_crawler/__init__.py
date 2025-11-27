"""Web crawler module for extracting download links from web pages."""

from .extract_download_link import (
    extract_zip_links_selenium,
    setup_driver,
    find_elements_by_strategy,
    find_element_by_strategy,
    click_element,
    click_all_by_strategy,
    click_by_strategies,
)

__all__ = [
    'extract_zip_links_selenium',
    'setup_driver',
    'find_elements_by_strategy',
    'find_element_by_strategy',
    'click_element',
    'click_all_by_strategy',
    'click_by_strategies',
]
