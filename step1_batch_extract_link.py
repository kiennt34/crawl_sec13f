#!/usr/bin/env python3
"""
Batch process multiple pages with different click strategies.

This script demonstrates how to use the enhanced web_crawler module
with multiple click strategies for different pages.

Usage:
    python step1_batch_extract_link.py [--config batch_config.json]
"""
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Import from web_crawler module
from web_crawler.extract_download_link import extract_zip_links_selenium

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_batch_config(config_file: str) -> Dict:
    """Load batch processing configuration from JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)


def save_results(results: List[Dict], output_file: str):
    """Save batch extraction results to JSON file."""
    output_data = {
        "extracted_at": datetime.utcnow().isoformat(),
        "total_pages": len(results),
        "total_files": sum(r.get('file_count', 0) for r in results),
        "results": results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"Results saved to: {output_file}")


def process_batch(config: Dict) -> List[Dict]:
    """
    Process multiple pages according to batch configuration.
    
    Args:
        config: Dictionary containing batch processing configuration
        
    Returns:
        List of results for each page processed
    """
    pages = config.get('pages', [])
    results = []
    
    for i, page_config in enumerate(pages, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing page {i}/{len(pages)}")
        logger.info(f"{'='*60}")
        
        url = page_config.get('url')
        name = page_config.get('name', f'page_{i}')
        wait_time = page_config.get('wait_time', 30)
        headless = page_config.get('headless', True)
        save_path = page_config.get('save_path', None)
        file_type = page_config.get('file_type', '.zip')
        
        # Get click strategies
        strategies = page_config.get('click_strategies', None)
        
        logger.info(f"Page: {name}")
        logger.info(f"URL: {url}")
        logger.info(f"File type: {file_type}")
        logger.info(f"Save path: {save_path if save_path else 'None'}")
        logger.info(f"Strategies: {len(strategies) if strategies else 0}")
        
        try:
            # Extract file URLs
            file_urls = extract_zip_links_selenium(
                url=url,
                wait_time=wait_time,
                click_strategies=strategies,
                headless=headless,
                file_type=file_type,
                save_path=save_path
            )
            
            result = {
                "name": name,
                "url": url,
                "status": "success",
                "file_type": file_type,
                "file_count": len(file_urls),
                "file_urls": file_urls,
                "save_path": save_path,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✓ Success: Found {len(file_urls)} {file_type} file(s)")
            
        except Exception as e:
            logger.error(f"✗ Failed: {e}")
            result = {
                "name": name,
                "url": url,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        results.append(result)
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Batch extract ZIP links from multiple pages")
    
    parser.add_argument(
        "--config",
        type=str,
        default="batch_config.json",
        help="Batch configuration JSON file (default: batch_config.json)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="batch_results.json",
        help="Output JSON file (default: batch_results.json)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        config = load_batch_config(args.config)
        
        # Process batch
        results = process_batch(config)
        
        # Save results
        save_results(results, args.output)
        
        # Print summary
        print("\n" + "="*60)
        print("BATCH EXTRACTION COMPLETE")
        print("="*60)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count
        total_files = sum(r.get('file_count', 0) for r in results)
        
        print(f"Total pages: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total files found: {total_files}")
        
        print("\nDetails:")
        for r in results:
            status_icon = "✓" if r['status'] == 'success' else "✗"
            file_count = r.get('file_count', 0)
            file_type = r.get('file_type', 'unknown')
            print(f"  {status_icon} {r['name']}: {file_count} {file_type} file(s)")
        
        print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
