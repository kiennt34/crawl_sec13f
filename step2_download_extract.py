#!/usr/bin/env python3
"""
Step 2: Download ZIP files and extract data files.

This script:
- Reads discovered ZIP URLs from JSON (from step1)
- Downloads ZIP files to data/zips/
- Extracts data files (.tsv, .txt) to data/extracted/
- Outputs a JSON file with extraction results

Usage:
    python step2_download_extract.py [--input discovered_zips.json] [--output extracted_files.json]
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile

import requests

from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_zip(zip_url: str, output_path: Path, skip_existing: bool = True) -> bool:
    """
    Download a ZIP file from URL.
    
    Args:
        zip_url: URL of the ZIP file
        output_path: Local path to save the ZIP
        skip_existing: If True, skip download if file already exists
        
    Returns:
        True if downloaded (or already exists), False on failure
    """
    if skip_existing and output_path.exists():
        logger.info(f"ZIP already exists, skipping: {output_path.name}")
        return True
    
    headers = {
        "User-Agent": Config.USER_AGENT
    }
    
    logger.info(f"Downloading: {zip_url}")
    
    for attempt in range(Config.MAX_RETRIES):
        try:
            response = requests.get(
                zip_url,
                headers=headers,
                timeout=Config.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()
            
            # Write to file
            total_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            logger.info(f"Downloaded {output_path.name} ({total_size:,} bytes)")
            return True
            
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {e}")
            if attempt < Config.MAX_RETRIES - 1:
                time.sleep(Config.RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"Failed to download {zip_url}: {e}")
                return False
    
    return False


def extract_text_files(zip_path: Path, extract_dir: Path) -> List[Dict[str, str]]:
    """
    Extract data files (.tsv, .txt) from a ZIP archive.
    
    Args:
        zip_path: Path to the ZIP file
        extract_dir: Directory to extract files to
        
    Returns:
        List of dictionaries with file info: {filename, table_type, extracted_path}
    """
    extracted_files = []
    
    logger.info(f"Extracting: {zip_path.name}")
    
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files
            file_list = zip_ref.namelist()
            
            # Filter for data files (.tsv or .txt), exclude readme/metadata files
            data_file_extensions = ['.tsv', '.txt']
            exclude_patterns = ['readme', 'metadata', '.htm', '.html', '.json', '.pdf']
            
            data_files = []
            for f in file_list:
                f_lower = f.lower()
                # Check if it's a data file
                is_data_file = any(f_lower.endswith(ext) for ext in data_file_extensions)
                # Exclude readme/metadata files
                is_excluded = any(pattern in f_lower for pattern in exclude_patterns)
                
                if is_data_file and not is_excluded:
                    data_files.append(f)
            
            if not data_files:
                logger.warning(f"No data files (.tsv/.txt) found in {zip_path.name}")
                return extracted_files
            
            # Extract each data file
            for data_file in data_files:
                # Determine table type from filename
                table_type = identify_table_type(data_file)
                
                # Create output path
                # Use zip filename + original filename to avoid conflicts
                zip_stem = zip_path.stem
                file_name = Path(data_file).name
                output_filename = f"{zip_stem}__{file_name}"
                output_path = extract_dir / output_filename
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Extract file directly to output path
                # Read from ZIP and write to output path to avoid nested directory issues
                with zip_ref.open(data_file) as source:
                    with open(output_path, 'wb') as target:
                        target.write(source.read())
                
                extracted_files.append({
                    "original_filename": data_file,
                    "extracted_path": str(output_path),
                    "table_type": table_type,
                    "zip_filename": zip_path.name
                })
                
                logger.debug(f"Extracted: {data_file} -> {table_type} ({output_path.name})")
        
        logger.info(f"Extracted {len(extracted_files)} data files from {zip_path.name}")
        
    except Exception as e:
        logger.error(f"Error extracting {zip_path.name}: {e}")
        raise
    
    return extracted_files


def identify_table_type(filename: str) -> str:
    """
    Identify table type from filename.
    
    Args:
        filename: Name of the data file (e.g., SUBMISSION.tsv, coverpage.txt)
        
    Returns:
        Table type name (submission, coverpage, etc.)
    """
    filename_lower = filename.lower()
    # Remove extension for matching
    filename_no_ext = filename_lower.replace('.tsv', '').replace('.txt', '')
    
    # Check in order of specificity (most specific first)
    if "othermanager2" in filename_no_ext:
        return "othermanager2"
    elif "othermanager" in filename_no_ext:
        return "othermanager"
    elif "submission" in filename_no_ext:
        return "submission"
    elif "coverpage" in filename_no_ext or "cover" in filename_no_ext:
        return "coverpage"
    elif "summarypage" in filename_no_ext or "summary" in filename_no_ext:
        return "summarypage"
    elif "signature" in filename_no_ext:
        return "signature"
    elif "infotable" in filename_no_ext or "info" in filename_no_ext:
        return "infotable"
    else:
        return "unknown"


def main():
    """Main entry point for step 2."""
    parser = argparse.ArgumentParser(description="Download ZIP files and extract text files")
    parser.add_argument(
        "--input",
        type=str,
        default="discovered_zips.json",
        help="Input JSON file from step1 (default: discovered_zips.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="extracted_files.json",
        help="Output JSON file path (default: extracted_files.json)"
    )
    parser.add_argument(
        "--skip-downloaded",
        action="store_true",
        default=True,
        help="Skip ZIPs that are already downloaded (default: True)"
    )
    parser.add_argument(
        "--zip-filter",
        type=str,
        help="Process only ZIPs matching this substring (for testing)"
    )
    
    parser.add_argument(
        "--base-dir",
        type=str,
        help="Custom directory to put files to (default: from config)"
    )

    args = parser.parse_args()
    
    # Override base directory if provided
    if args.base_dir:
        Config.reinit_datadirs(base_dir=Path(args.base_dir))
    
    try:
        # Ensure directories exist
        Config.ensure_directories()
        
        # Read input JSON
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            sys.exit(1)
        
        with open(input_path, 'r') as f:
            input_data = json.load(f)
        
        zip_files = input_data.get("zip_files", [])
        
        if not zip_files:
            logger.warning("No ZIP files found in input")
            sys.exit(1)
        
        # Filter ZIPs if requested
        if args.zip_filter:
            zip_files = [
                zf for zf in zip_files
                if args.zip_filter.lower() in zf["filename"].lower()
            ]
            logger.info(f"Filtered to {len(zip_files)} ZIP files matching '{args.zip_filter}'")
        
        # Process each ZIP
        all_extracted = []
        downloaded_count = 0
        extracted_count = 0
        
        for zip_info in zip_files:
            zip_url = zip_info["url"]
            zip_filename = zip_info["filename"]
            zip_path = Config.ZIPS_DIR / zip_filename
            
            # Download ZIP
            if download_zip(zip_url, zip_path, skip_existing=args.skip_downloaded):
                if not (args.skip_downloaded and zip_path.exists()):
                    downloaded_count += 1
                
                # Extract text files
                extracted = extract_text_files(zip_path, Config.EXTRACTED_DIR)
                all_extracted.extend(extracted)
                extracted_count += 1
        
        # Prepare output data
        output_data = {
            "input_file": str(input_path),
            "processed_at": None,
            "zips_processed": extracted_count,
            "zips_downloaded": downloaded_count,
            "total_extracted_files": len(all_extracted),
            "extracted_files": all_extracted
        }
        
        # Add timestamp
        from datetime import datetime
        output_data["processed_at"] = datetime.utcnow().isoformat()
        
        # Write output JSON
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Step 2 complete: Processed {extracted_count} ZIPs, extracted {len(all_extracted)} files")
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(f"\n✓ Step 2 Complete:")
        print(f"  ZIPs processed: {extracted_count}")
        print(f"  ZIPs downloaded: {downloaded_count}")
        print(f"  Files extracted: {len(all_extracted)}")
        print(f"  Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Step 2 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

