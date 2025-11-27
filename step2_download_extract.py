#!/usr/bin/env python3
"""Step 2: Download archive files and extract data files.

This script:
- Reads discovered file URLs from JSON (from step1)
- Downloads archives (.zip, .tar.gz, etc.) to data/zips/
- Extracts files to data/extracted/ with optional filtering
- Outputs a JSON file with extraction results

Usage:
    python step2_download_extract.py [--input results_sec13f.json] [--output extracted_files.json]
    python step2_download_extract.py --file-extensions ".tsv,.txt" --exclude-patterns "readme,metadata"
"""
import argparse
import json
import logging
import sys
import time
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from zipfile import ZipFile

import requests

from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_file(file_url: str, output_path: Path, skip_existing: bool = True) -> bool:
    """
    Download an archive file from URL.
    
    Args:
        file_url: URL of the archive file
        output_path: Local path to save the file
        skip_existing: If True, skip download if file already exists
        
    Returns:
        True if downloaded (or already exists), False on failure
    """
    if skip_existing and output_path.exists():
        logger.info(f"File already exists, skipping: {output_path.name}")
        return True
    
    headers = {
        "User-Agent": Config.USER_AGENT
    }
    
    logger.info(f"Downloading: {file_url}")
    
    for attempt in range(Config.MAX_RETRIES):
        try:
            response = requests.get(
                file_url,
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
                logger.error(f"Failed to download {file_url}: {e}")
                return False
    
    return False


def should_extract_file(filename: str, file_extensions: Optional[Set[str]], exclude_patterns: Optional[Set[str]]) -> bool:
    """
    Check if a file should be extracted based on filters.
    
    Args:
        filename: Name of the file
        file_extensions: Set of allowed extensions (e.g., {'.tsv', '.txt'}), None = all
        exclude_patterns: Set of patterns to exclude (e.g., {'readme', 'metadata'})
        
    Returns:
        True if file should be extracted
    """
    filename_lower = filename.lower()
    
    # Check file extension filter
    if file_extensions:
        if not any(filename_lower.endswith(ext) for ext in file_extensions):
            return False
    
    # Check exclude patterns
    if exclude_patterns:
        if any(pattern in filename_lower for pattern in exclude_patterns):
            return False
    
    return True


def extract_files(archive_path: Path, extract_dir: Path, 
                  file_extensions: Optional[Set[str]] = None,
                  exclude_patterns: Optional[Set[str]] = None,
                  create_sub_dir: bool = False) -> List[Dict[str, str]]:
    """
    Extract files from archive (.zip, .tar.gz, etc.) with optional filtering.
    
    Args:
        archive_path: Path to the archive file
        extract_dir: Directory to extract files to
        file_extensions: Set of file extensions to extract (None = all)
        exclude_patterns: Set of patterns to exclude from extraction
        create_sub_dir: If True, extract to archive_name/ subdirectory. If False, use archive__filename pattern
        
    Returns:
        List of dictionaries with file info: {filename, table_type, extracted_path}
    """
    extracted_files = []
    archive_name = archive_path.name
    archive_stem = archive_path.stem
    
    # Remove .tar from stem if it's .tar.gz
    if archive_stem.endswith('.tar'):
        archive_stem = archive_stem[:-4]
    
    logger.info(f"Extracting: {archive_name}")
    
    # Determine output directory
    if create_sub_dir:
        output_dir = extract_dir / archive_stem
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Creating subdirectory: {output_dir}")
    else:
        output_dir = extract_dir
    
    try:
        # Determine archive type and extract
        if archive_path.suffix == '.zip':
            extracted_files = _extract_zip(archive_path, archive_stem, output_dir, file_extensions, exclude_patterns, create_sub_dir)
        elif archive_path.suffix == '.gz' and archive_path.stem.endswith('.tar'):
            extracted_files = _extract_tar_gz(archive_path, archive_stem, output_dir, file_extensions, exclude_patterns, create_sub_dir)
        elif archive_path.suffix in ['.tar', '.tgz']:
            extracted_files = _extract_tar(archive_path, archive_stem, output_dir, file_extensions, exclude_patterns, create_sub_dir)
        else:
            logger.warning(f"Unsupported archive format: {archive_path.suffix}")
            return extracted_files
        
        logger.info(f"Extracted {len(extracted_files)} file(s) from {archive_name}")
        
    except Exception as e:
        logger.error(f"Error extracting {archive_name}: {e}")
        raise
    
    return extracted_files


def _extract_zip(zip_path: Path, archive_stem: str, extract_dir: Path,
                 file_extensions: Optional[Set[str]], exclude_patterns: Optional[Set[str]],
                 create_sub_dir: bool) -> List[Dict[str, str]]:
    """Extract files from ZIP archive."""
    extracted_files = []
    
    with ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        
        for file_name in file_list:
            # Skip directories
            if file_name.endswith('/'):
                continue
            
            if not should_extract_file(file_name, file_extensions, exclude_patterns):
                continue
            
            # Create output path
            base_name = Path(file_name).name
            if create_sub_dir:
                # Extract to subdirectory with original filename
                output_path = extract_dir / base_name
            else:
                # Flat structure with archive prefix
                output_filename = f"{archive_stem}__{base_name}"
                output_path = extract_dir / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract file
            with zip_ref.open(file_name) as source:
                with open(output_path, 'wb') as target:
                    target.write(source.read())
            
            extracted_files.append({
                "original_filename": file_name,
                "extracted_path": str(output_path),
                "table_type": identify_table_type(file_name),
                "archive_filename": zip_path.name
            })
            
            logger.debug(f"Extracted: {file_name} -> {output_path.name}")
    
    return extracted_files


def _extract_tar_gz(tar_path: Path, archive_stem: str, extract_dir: Path,
                    file_extensions: Optional[Set[str]], exclude_patterns: Optional[Set[str]],
                    create_sub_dir: bool) -> List[Dict[str, str]]:
    """Extract files from tar.gz archive."""
    extracted_files = []
    
    with tarfile.open(tar_path, 'r:gz') as tar_ref:
        members = tar_ref.getmembers()
        
        for member in members:
            # Skip directories
            if member.isdir():
                continue
            
            if not should_extract_file(member.name, file_extensions, exclude_patterns):
                continue
            
            # Create output path
            base_name = Path(member.name).name
            if create_sub_dir:
                # Extract to subdirectory with original filename
                output_path = extract_dir / base_name
            else:
                # Flat structure with archive prefix
                output_filename = f"{archive_stem}__{base_name}"
                output_path = extract_dir / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract file
            with tar_ref.extractfile(member) as source:
                if source:
                    with open(output_path, 'wb') as target:
                        target.write(source.read())
            
            extracted_files.append({
                "original_filename": member.name,
                "extracted_path": str(output_path),
                "table_type": identify_table_type(member.name),
                "archive_filename": tar_path.name
            })
            
            logger.debug(f"Extracted: {member.name} -> {output_path.name}")
    
    return extracted_files


def _extract_tar(tar_path: Path, archive_stem: str, extract_dir: Path,
                 file_extensions: Optional[Set[str]], exclude_patterns: Optional[Set[str]],
                 create_sub_dir: bool) -> List[Dict[str, str]]:
    """Extract files from tar archive."""
    extracted_files = []
    
    with tarfile.open(tar_path, 'r') as tar_ref:
        members = tar_ref.getmembers()
        
        for member in members:
            # Skip directories
            if member.isdir():
                continue
            
            if not should_extract_file(member.name, file_extensions, exclude_patterns):
                continue
            
            # Create output path
            base_name = Path(member.name).name
            if create_sub_dir:
                # Extract to subdirectory with original filename
                output_path = extract_dir / base_name
            else:
                # Flat structure with archive prefix
                output_filename = f"{archive_stem}__{base_name}"
                output_path = extract_dir / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract file
            with tar_ref.extractfile(member) as source:
                if source:
                    with open(output_path, 'wb') as target:
                        target.write(source.read())
            
            extracted_files.append({
                "original_filename": member.name,
                "extracted_path": str(output_path),
                "table_type": identify_table_type(member.name),
                "archive_filename": tar_path.name
            })
            
            logger.debug(f"Extracted: {member.name} -> {output_path.name}")
    
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
        default="results.json",
        help="Input JSON file from step1 batch extraction (default: results_sec13f.json)"
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
        help="Skip archives that are already downloaded (default: True)"
    )
    parser.add_argument(
        "--archive-filter",
        type=str,
        help="Process only archives matching this substring (for testing)"
    )
    parser.add_argument(
        "--file-extensions",
        type=str,
        help="Comma-separated list of file extensions to extract (e.g., '.tsv,.txt'). Default: extract all"
    )
    parser.add_argument(
        "--exclude-patterns",
        type=str,
        help="Comma-separated list of patterns to exclude (e.g., 'readme,metadata'). Default: none"
    )
    parser.add_argument(
        "--create-sub-dir",
        action="store_true",
        help="Extract files into subdirectories named after archive (e.g., foldera/file.txt). Default: flat with prefix (foldera__file.txt)"
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
        
        # Handle new step1 format: results array with file_urls
        zip_files = []
        results = input_data.get("results", [])
        
        for result in results:
            if result.get("status") != "success":
                logger.warning(f"Skipping failed result: {result.get('name')}")
                continue
            
            file_urls = result.get("file_urls", [])
            for file_url in file_urls:
                # Extract filename from URL
                filename = file_url.split('/')[-1]
                zip_files.append({
                    "url": file_url,
                    "filename": filename,
                    "source_page": result.get("name", "unknown")
                })
        
        if not zip_files:
            logger.warning("No file URLs found in input")
            sys.exit(1)
        
        logger.info(f"Loaded {len(zip_files)} file(s) from {len(results)} page(s)")
        
        # Parse file extension filters
        file_extensions = None
        if args.file_extensions:
            file_extensions = set()
            for ext in args.file_extensions.split(','):
                ext = ext.strip()
                if not ext.startswith('.'):
                    ext = '.' + ext
                file_extensions.add(ext.lower())
            logger.info(f"Filtering by extensions: {', '.join(sorted(file_extensions))}")
        else:
            logger.info("Extracting all file types")
        
        # Parse exclude patterns
        exclude_patterns = None
        if args.exclude_patterns:
            exclude_patterns = set(p.strip().lower() for p in args.exclude_patterns.split(','))
            logger.info(f"Excluding patterns: {', '.join(sorted(exclude_patterns))}")
        
        # Filter archives if requested
        if args.archive_filter:
            zip_files = [
                zf for zf in zip_files
                if args.archive_filter.lower() in zf["filename"].lower()
            ]
            logger.info(f"Filtered to {len(zip_files)} file(s) matching '{args.archive_filter}'")
        
        # Process each archive
        all_extracted = []
        downloaded_count = 0
        extracted_count = 0
        
        for file_info in zip_files:
            file_url = file_info["url"]
            file_name = file_info["filename"]
            file_path = Config.ZIPS_DIR / file_name
            
            # Download archive
            if download_file(file_url, file_path, skip_existing=args.skip_downloaded):
                if not (args.skip_downloaded and file_path.exists()):
                    downloaded_count += 1
                
                # Extract files with filtering
                extracted = extract_files(
                    file_path, 
                    Config.EXTRACTED_DIR,
                    file_extensions=file_extensions,
                    exclude_patterns=exclude_patterns,
                    create_sub_dir=args.create_sub_dir
                )
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
        
        logger.info(f"Step 2 complete: Processed {extracted_count} archives, extracted {len(all_extracted)} files")
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(f"\n✓ Step 2 Complete:")
        print(f"  Archives processed: {extracted_count}")
        print(f"  Archives downloaded: {downloaded_count}")
        print(f"  Files extracted: {len(all_extracted)}")
        print(f"  Structure: {'subdirectories (archive/file.txt)' if args.create_sub_dir else 'flat (archive__file.txt)'}")
        if file_extensions:
            print(f"  Extensions: {', '.join(sorted(file_extensions))}")
        if exclude_patterns:
            print(f"  Excluded: {', '.join(sorted(exclude_patterns))}")
        print(f"  Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Step 2 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

