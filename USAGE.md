# SEC 13F ETL Pipeline - Usage Guide

This document describes how to use the modular ETL scripts for SEC Form 13F data processing.

## Overview

The pipeline consists of 4 independent steps that can be run separately or chained together:

1. **step1_crawl.py** - Crawl SEC index page and discover ZIP files
2. **step2_download_extract.py** - Download ZIP files and extract text files
3. **step3_parse_normalize.py** - Parse and normalize tab-delimited files
4. **step4_load_db.py** - Load normalized data into MariaDB

Each step produces a JSON output file that serves as input for the next step, making it easy to integrate with workflow automation tools like n8n.

## Prerequisites

1. **Python 3.8+** with pip
2. **MariaDB** database with the `sec13f` schema created
3. **Environment variables** configured (see Configuration section)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
SEC13F_DB_HOST=localhost
SEC13F_DB_PORT=3306
SEC13F_DB_USER=secuser
SEC13F_DB_PASSWORD=your_password
SEC13F_DB_NAME=sec13f

# Data Directories
SEC13F_DATA_DIR=/data/sec13f

# SEC Configuration
SEC13F_USER_AGENT=HybridFinancial 13F Loader (contact@example.com)
SEC13F_LINK=https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets
```

Alternatively, you can set these as environment variables directly.

## Step-by-Step Usage

### Step 1: Crawl SEC Index

Discovers all ZIP file URLs from the SEC index page.

```bash
python step1_crawl.py [--output discovered_zips.json]
```

**Output:** `discovered_zips.json` containing:
- List of discovered ZIP URLs
- Filenames
- Discovery timestamp

**Example:**
```bash
python step1_crawl.py --output discovered_zips.json
```

### Step 2: Download & Extract

Downloads ZIP files and extracts text files.

```bash
python step2_download_extract.py \
    [--input discovered_zips.json] \
    [--output extracted_files.json] \
    [--skip-downloaded] \
    [--zip-filter "2025"]
```

**Options:**
- `--input`: Input JSON from step 1 (default: `discovered_zips.json`)
- `--output`: Output JSON file (default: `extracted_files.json`)
- `--skip-downloaded`: Skip ZIPs that are already downloaded (default: True)
- `--zip-filter`: Process only ZIPs matching this substring (useful for testing)

**Output:** `extracted_files.json` containing:
- List of extracted text files
- Table type for each file
- Extraction paths

**Example:**
```bash
python step2_download_extract.py --zip-filter "2025"
```

### Step 3: Parse & Normalize

Parses tab-delimited files and normalizes data (dates, numbers, nulls).

```bash
python step3_parse_normalize.py \
    [--input extracted_files.json] \
    [--output normalized_files.json] \
    [--table-filter submission]
```

**Options:**
- `--input`: Input JSON from step 2 (default: `extracted_files.json`)
- `--output`: Output JSON file (default: `normalized_files.json`)
- `--table-filter`: Process only files for this table type (useful for testing)

**Output:** `normalized_files.json` containing:
- List of normalized TSV files
- Row counts
- Normalization stats

**Example:**
```bash
python step3_parse_normalize.py --table-filter submission
```

### Step 4: Load into Database

Loads normalized data into MariaDB using `LOAD DATA LOCAL INFILE`.

```bash
python step4_load_db.py \
    [--input normalized_files.json] \
    [--output load_results.json] \
    [--skip-imported] \
    [--table-filter submission]
```

**Options:**
- `--input`: Input JSON from step 3 (default: `normalized_files.json`)
- `--output`: Output JSON file (default: `load_results.json`)
- `--skip-imported`: Skip ZIPs that are already imported (default: True)
- `--table-filter`: Load only files for this table type (useful for testing)

**Output:** `load_results.json` containing:
- Load statistics
- Rows loaded per file
- Imported ZIPs

**Example:**
```bash
python step4_load_db.py --table-filter submission
```

## Running the Full Pipeline

### Option 1: Using main.py

Run all steps sequentially:

```bash
python main.py --all
```

Run a specific step:

```bash
python main.py --step 1
```

### Option 2: Manual Chain

```bash
python step1_crawl.py
python step2_download_extract.py
python step3_parse_normalize.py
python step4_load_db.py
```

## Integration with n8n

Each script can be integrated into n8n workflows:

1. **Step 1**: Use "Execute Command" node to run `step1_crawl.py`
2. **Step 2**: Read `discovered_zips.json`, then execute `step2_download_extract.py`
3. **Step 3**: Read `extracted_files.json`, then execute `step3_parse_normalize.py`
4. **Step 4**: Read `normalized_files.json`, then execute `step4_load_db.py`

Each step can be triggered:
- On a schedule (cron)
- After the previous step completes
- Manually via webhook

### Example n8n Workflow Structure

```
┌─────────────┐
│  Schedule   │ (Daily at 2 AM)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Execute: step1  │ → discovered_zips.json
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Execute: step2  │ → extracted_files.json
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Execute: step3  │ → normalized_files.json
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Execute: step4  │ → load_results.json
└─────────────────┘
```

## Incremental Updates

The pipeline supports incremental updates:

- **Step 2**: Skips ZIPs that are already downloaded (if `--skip-downloaded` is used)
- **Step 4**: Skips ZIPs that are already imported (tracked in `imported_zip_files` table)

To force a full reload, omit the `--skip-downloaded` and `--skip-imported` flags.

## Error Handling

Each script:
- Logs errors to stdout/stderr
- Returns non-zero exit code on failure
- Produces partial output JSON even if some files fail

Check the output JSON files for detailed error information.

## Testing

Test with a single ZIP or table type:

```bash
# Test with one ZIP
python step1_crawl.py
python step2_download_extract.py --zip-filter "2025-june"

# Test with one table
python step3_parse_normalize.py --table-filter submission
python step4_load_db.py --table-filter submission
```

## Troubleshooting

### Database Connection Issues

- Verify MariaDB is running and accessible
- Check database credentials in `.env`
- Ensure `local_infile` is enabled in MariaDB:
  ```sql
  SET GLOBAL local_infile = 1;
  ```

### Missing Dependencies

```bash
pip install -r requirements.txt
```

### Permission Issues

Ensure the data directory is writable:
```bash
chmod -R 755 /data/sec13f
```

### SEC Rate Limiting

The scripts include retry logic and respect SEC's User-Agent requirements. If you encounter rate limiting, add delays between requests.

## Output Files

All intermediate JSON files are stored in the project root:
- `discovered_zips.json` - ZIP discovery results
- `extracted_files.json` - File extraction results
- `normalized_files.json` - Normalization results
- `load_results.json` - Database load results

Data files are stored in:
- `data/zips/` - Downloaded ZIP files
- `data/extracted/` - Extracted text files
- `data/staging/` - Normalized TSV files for loading

