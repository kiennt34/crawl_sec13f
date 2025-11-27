# SEC 13F ETL Pipeline - Usage Guide

This document describes how to use the modular ETL scripts for SEC Form 13F data processing.

## Overview

The pipeline consists of 4 independent steps that can be run separately or chained together:

1. **step1_batch_extract_link.py** - Crawl web page and discover files, can use multiple purposes
2. **step2_download_extract.py** - Download ZIP files and extract text files, can use multiple purposes
3. **step3_sec13f_parse_normalize.py** - Parse and normalize tab-delimited files, specific for sec13f data
4. **step4_sec13f_load_db.py** - Load normalized data into MariaDB, specific for sec13f data

Each step produces a JSON output file that serves as input for the next step, making it easy to integrate with workflow automation tools like n8n.

## Prerequisites

1. **Python 3.10+** with pip
2. **MariaDB** database with the `sec13f` schema created
3. **Environment variables** configured (see Configuration section)

## Example: SEC 13F Data Pipeline

### Step 1: Extract file links from web page
```bash
python step1_batch_extract_link.py --config config/batch_sec13f.json --output config/results_sec13f.json
```

### Step 2: Download and extract archives
```bash
python step2_download_extract.py --input config/results_sec13f.json --base-dir /mnt/Data_Temp/sec13f/ --output config/extracted_files_sec13f.json

# Optional: Extract only specific file types
python3 step2_download_extract.py --input config/results_sec13f.json --file-extensions ".tsv,.txt" --output config/extracted_files_sec13f.json

# Optional: Extract into subdirectories (archive/file.txt instead of archive__file.txt)
python3 step2_download_extract.py --input config/results_sec13f.json --create-sub-dir --output config/extracted_files_sec13f.json
```

### Step 3: Parse and normalize SEC 13F data
```bash
python3 step3_sec13f_parse_normalize.py --input config/extracted_files_sec13f.json --output config/normalized_files_sec13f.json
```

### Step 4: Load into database
```bash
python3 step4_sec13f_load_db.py --staging-dir /mnt/Data_Temp/sec13f/staging/
```


For ADV data
python3 step1_batch_extract_link.py --config config/batch_adviserinfo.json --output config/results_adviserinfo.json
python3 step2_download_extract.py --input config/results_adviserinfo.json --create-sub-dir --output config/extracted_files_adviserinfo.json