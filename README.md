# SEC 13F ETL Pipeline

A modular Python pipeline to **crawl, download, extract, parse, and load SEC Form 13F data** into MariaDB.

## Overview

**4-Step ETL Pipeline:**

1. **step1_batch_extract_link.py** - Crawl web pages and extract download links (reusable)
2. **step2_download_extract.py** - Download and extract archives (reusable, supports .zip/.tar.gz)
3. **step3_sec13f_parse_normalize.py** - Parse and normalize SEC 13F data (specific to 13F)
4. **step4_sec13f_load_db.py** - Load normalized data into MariaDB (specific to 13F)

**Key Features:**
- ✅ **Modular**: Each step is independent and can be run separately
- ✅ **Reusable**: Steps 1 & 2 work with any web source (not just SEC 13F)
- ✅ **JSON-based**: Each step outputs JSON for workflow automation (e.g., n8n)
- ✅ **Configurable**: Batch processing via JSON config files

---

## Quick Start

```bash
# Step 1: Crawl SEC page and discover ZIP files
python step1_batch_extract_link.py \\
  --config config/batch_sec13f.json \\
  --output config/results_sec13f.json

# Step 2: Download ZIPs and extract .tsv/.txt files
python step2_download_extract.py \\
  --input config/results_sec13f.json \\
  --file-extensions ".tsv,.txt" \\
  --exclude-patterns "readme,metadata" \\
  --output config/extracted_files_sec13f.json

# Step 3: Parse and normalize data
python step3_sec13f_parse_normalize.py \\
  --input config/extracted_files_sec13f.json \\
  --output config/normalized_files_sec13f.json

# Step 4: Load into MariaDB
python step4_sec13f_load_db.py \\
  --staging-dir /mnt/Data_Temp/sec13f/staging/
```

---

## Project Structure

```
crawl_sec13f/
  # Core Scripts
  step1_batch_extract_link.py       <- Step 1: Web crawling
  step2_download_extract.py         <- Step 2: Download & extract
  step3_sec13f_parse_normalize.py   <- Step 3: Parse & normalize
  step4_sec13f_load_db.py           <- Step 4: Load to database
  
  # Reusable Web Crawler Module
  web_crawler/
    __init__.py
    extract_download_link.py        <- Selenium automation + click strategies
  
  # Database Module
  db/
    __init__.py
    connection.py                   <- MariaDB connection helper
  
  # Configuration
  config.py                         <- Settings (DB, paths, URLs)
  config/
    batch_sec13f.json               <- Batch config for SEC 13F
    results_sec13f.json             <- Step 1 output
    extracted_files_sec13f.json     <- Step 2 output
    normalized_files_sec13f.json    <- Step 3 output
  
  # Data Storage (runtime)
  data/ or /mnt/Data/App/HybridFinancial/sec13f/
    zips/                           <- Downloaded archives
    extracted/                      <- Extracted raw files
    staging/                        <- Normalized TSV for LOAD DATA
  
  # Documentation
  README.md                         <- This file
  USAGE.md                          <- Detailed usage guide
  docs/                             <- Additional documentation
```

---

## Data Source

**SEC Form 13F Data Sets:**
- URL: https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets
- Format: Quarterly ZIP files (2013 Q2 - present)
- Contains: Tab-delimited files for multiple tables

---

## Database Schema

**Target:** MariaDB database `sec13f` with 7 tables:

### Core Tables

**submission** (filing metadata)
- Primary key: `ACCESSION_NUMBER`
- Fields: CIK, filer name, report date, filing date, etc.

**coverpage** (filer information)
- 1:1 with submission
- Fields: Name, address, phone, report type, etc.

**signature** (signatory information)
- 1:1 with submission
- Fields: Name, title, signature date, etc.

**summarypage** (filing summary)
- 1:1 with submission
- Fields: Total entries, total value, etc.

**othermanager** / **othermanager2** (other managers)
- 0..N per submission
- Fields: Name, CIK, sequence number

**infotable** (holdings - largest table)
- 0..N per submission
- Fields: Security name, CUSIP, value, shares, voting authority, etc.

See [create_13f_tables.sql](config/create_13f_tables.sql) for complete schema.

---

## Environment Variables

Configure via `.env` file or environment:

```bash
# Database
SEC13F_DB_HOST=hybrid-admin-mysql.mysql.database.azure.com
SEC13F_DB_PORT=3306
SEC13F_DB_USER=YourUser
SEC13F_DB_PASSWORD=YourPassword
SEC13F_DB_NAME=sec13f_db

# Paths
SEC13F_DATA_DIR=/mnt/Data/App/HybridFinancial/sec13f

# SEC Compliance
SEC13F_USER_AGENT="HybridFinancial 13F Loader (contact@example.com)"
```

---

## Pipeline Details

### Step 1: Web Crawling (Reusable)

**Module:** `web_crawler.extract_download_link`

**Features:**
- Selenium automation for JavaScript-rendered pages
- Multiple click strategies (text, class, css, xpath, id)
- Universal file type detection
- Batch processing support

**Example Config:**
```json
{
  "pages": [
    {
      "name": "SEC Market Data 13f Data Sets",
      "url": "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets",
      "file_type": ".zip",
      "click_strategies": []
    }
  ]
}
```

---

### Step 2: Download & Extract (Reusable)

**Features:**
- Multi-format support: .zip, .tar.gz, .tar, .tgz
- File filtering: `--file-extensions`, `--exclude-patterns`
- Structure options: flat (default) or subdirectories (`--create-sub-dir`)
- Idempotent: Skips already-downloaded files

**Output naming:**
- Flat: `2023q4_form13f__COVERPAGE.tsv`
- Sub-dir: `2023q4_form13f/COVERPAGE.tsv`

---

### Step 3: Parse & Normalize (SEC 13F Specific)

**Features:**
- Tab-delimited parsing
- Data normalization:
  - Dates: `31-DEC-2024` → `2024-12-31`
  - Nulls: Empty strings → `\N`
  - Types: int, bigint, varchar
- Table identification by filename pattern
- Output: Clean TSV files for LOAD DATA

---

### Step 4: Load into Database (SEC 13F Specific)

**Features:**
- Bulk loading via `LOAD DATA LOCAL INFILE`
- Idempotent: `ON DUPLICATE KEY UPDATE`
- Transaction support with rollback
- Foreign key ordering (submission → coverpage → infotable, etc.)
- Import tracking to prevent duplicates

**Tracking table:**
```sql
CREATE TABLE imported_zip_files (
  zip_name VARCHAR(255) PRIMARY KEY,
  imported_at DATETIME NOT NULL
) ENGINE=InnoDB;
```

---

## Technology Stack

- **Language:** Python 3.10+
- **Web Automation:** Selenium + ChromeDriver
- **Database:** MariaDB (InnoDB)
- **Dependencies:**
  - `selenium` - browser automation
  - `webdriver-manager` - automatic ChromeDriver
  - `requests` - HTTP client
  - `pymysql` - MariaDB connector
  - `python-dotenv` - environment variables

---

## Reusability

**Steps 1 & 2 are universal:**
- ✅ Works with any website
- ✅ Any file type (.pdf, .mp3, .txt, etc.)
- ✅ Any archive format
- ✅ Batch processing ready

**Use cases beyond SEC 13F:**
- IAPD (Investment Adviser Public Disclosure)
- Other SEC filings (13D, 13G, Form 4, etc.)
- Any web scraping + file extraction task

**Steps 3 & 4 are SEC 13F-specific:**
- Template for other SEC filing parsers
- Can be adapted for similar structured data

---

## Future Enhancements

### Planned:
- [ ] Add support for other SEC forms (13D, 13G, Form 4)
- [ ] Incremental updates (delta detection)
- [ ] Data quality checks and validation
- [ ] n8n workflow examples
- [ ] Monitoring and alerting
- [ ] Docker containerization

### Already Flexible:
- ✅ Universal file type support
- ✅ Multiple archive formats
- ✅ Batch configuration
- ✅ Modular architecture

---

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage guide with examples
- [docs/](docs/) - Additional documentation and notes
- [config/create_13f_tables.sql](config/create_13f_tables.sql) - Database schema

---

## License

Internal use only - HybridFinancial
