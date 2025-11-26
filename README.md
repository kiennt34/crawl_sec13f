# crawl_sec13f

This folder contains the code to **download, parse, and load SEC Form 13F data sets** into our **MariaDB `sec13f` database**.

The goal is to build a repeatable ETL pipeline that:

1. Crawls the **Form 13F Data Sets** page on SEC.
2. Downloads all quarterly **ZIP** files.
3. Extracts the tab-delimited text files inside each ZIP.
4. Normalizes and loads them into MariaDB using the **`sec13f` schema**.
5. Supports **incremental updates** (only process new ZIPs).

Cursor should treat this as a standalone Python subproject that plugs into our existing crawler framework.

---

## 1. Data sources

### 1.1 Documentation / schema

- **13F readme / schema:**  
  - `https://www.sec.gov/files/form_13f_readme.pdf`  
  - Describes:
    - Tables (`submission`, `coverpage`, `othermanager`, `othermanager2`, `signature`, `summarypage`, `infotable`)
    - Columns, data types, and primary keys
    - File naming conventions and formats

If needed, we can store a local copy here as:  
`docs/form_13f_readme.pdf`

### 1.2 Data sets (quarterly ZIPs)

- **Index page:**  
  - `https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets`
- This page links to many ZIP files:
  - `.../2025-june-july-august-form13f.zip`
  - `.../2025-march-april-may-form13f.zip`
  - …
  - Back to 2013 Q2

Each ZIP contains **multiple tab-delimited (`.txt`) files**, one per table (names may vary slightly but typically include `submission`, `coverpage`, `summarypage`, `othermanager`, `othermanager2`, `signature`, `infotable`).

---

## 2. Target database

We use **MariaDB** running on a dedicated Linux container.

- Database: `sec13f`
- Engine: `InnoDB` for all tables
- Charset: `utf8mb4`

The tables are pre-created (or will be) using this schema.

### 2.1 `submission`

One row per EDGAR submission (filing).

```sql
CREATE TABLE submission (
  ACCESSION_NUMBER           VARCHAR(20) NOT NULL,
  CIK                        BIGINT,
  FILER_NAME                 VARCHAR(255),
  SUBMISSIONTYPE             VARCHAR(20),
  REPORTCALENDARORQUARTER    DATE,
  PERIODOFREPORT             DATE,
  FILING_DATE                DATE,
  FILED_AS_OF_DATE           DATE,
  EFFECTIVE_DATE             DATE,
  PRIMARY KEY (ACCESSION_NUMBER),
  INDEX idx_sub_cik_period (CIK, PERIODOFREPORT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
Primary key: ACCESSION_NUMBER

2.2 coverpage
1:1 with submission.

sql
Copy code
CREATE TABLE coverpage (
  ACCESSION_NUMBER     VARCHAR(20) NOT NULL,
  NAME                 VARCHAR(255),
  STREET1              VARCHAR(255),
  STREET2              VARCHAR(255),
  CITY                 VARCHAR(100),
  STATEORCOUNTRY       VARCHAR(50),
  ZIPCODE              VARCHAR(20),
  PHONE                VARCHAR(50),
  TYPEOFREPORT         VARCHAR(100),
  FORM13F_FILE_NUMBER  VARCHAR(50),
  PRIMARY KEY (ACCESSION_NUMBER),
  CONSTRAINT fk_cover_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
2.3 signature
1:1 with submission.

sql
Copy code
CREATE TABLE signature (
  ACCESSION_NUMBER   VARCHAR(20) NOT NULL,
  NAME               VARCHAR(255),
  TITLE              VARCHAR(255),
  PHONE              VARCHAR(50),
  CITY               VARCHAR(100),
  STATEORCOUNTRY     VARCHAR(50),
  SIGNATUREDATE      DATE,
  PRIMARY KEY (ACCESSION_NUMBER),
  CONSTRAINT fk_sig_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
2.4 summarypage
1:1 with submission.

sql
Copy code
CREATE TABLE summarypage (
  ACCESSION_NUMBER         VARCHAR(20) NOT NULL,
  OTHER_INCLUDED_MANAGERS  INT,
  TABLE_ENTRY_TOTAL        INT,
  TABLE_VALUE_TOTAL        BIGINT,
  PRIMARY KEY (ACCESSION_NUMBER),
  CONSTRAINT fk_sum_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
2.5 othermanager
0..N per submission.

sql
Copy code
CREATE TABLE othermanager (
  ACCESSION_NUMBER   VARCHAR(20) NOT NULL,
  OTHERMANAGER_SK    INT NOT NULL,
  SEQUENCENUMBER     INT,
  NAME               VARCHAR(255),
  CIK                BIGINT,
  PRIMARY KEY (ACCESSION_NUMBER, OTHERMANAGER_SK),
  INDEX idx_om_cik (CIK),
  CONSTRAINT fk_om_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
2.6 othermanager2
0..N per submission.

sql
Copy code
CREATE TABLE othermanager2 (
  ACCESSION_NUMBER   VARCHAR(20) NOT NULL,
  SEQUENCENUMBER     INT NOT NULL,
  CIK                BIGINT,
  NAME               VARCHAR(255),
  PRIMARY KEY (ACCESSION_NUMBER, SEQUENCENUMBER),
  INDEX idx_om2_cik (CIK),
  CONSTRAINT fk_om2_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
2.7 infotable (holdings)
The largest table; one row per security holding in a filing.

sql
Copy code
CREATE TABLE infotable (
  ACCESSION_NUMBER      VARCHAR(20) NOT NULL,
  INFOTABLE_SK          INT NOT NULL,

  NAMEOFISSUER          VARCHAR(255),
  TITLEOFCLASS          VARCHAR(100),
  CUSIP                 VARCHAR(20),
  VALUE                 BIGINT,
  SSHPRNAMT             BIGINT,
  SSHPRNAMTTYPE         VARCHAR(4),
  PUTCALL               VARCHAR(10),
  INVESTMENTDISCRETION  VARCHAR(50),
  OTHERMANAGERS         VARCHAR(255),
  VOTINGAUTH_SOLE       BIGINT,
  VOTINGAUTH_SHARED     BIGINT,
  VOTINGAUTH_NONE       BIGINT,

  PRIMARY KEY (ACCESSION_NUMBER, INFOTABLE_SK),

  INDEX idx_info_cusip (CUSIP),
  INDEX idx_info_issuer (NAMEOFISSUER),
  INDEX idx_info_accession (ACCESSION_NUMBER),

  CONSTRAINT fk_info_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
3. Project structure (desired)
The crawl_sec13f folder should be organized roughly like:

text
Copy code
crawl_sec13f/
  README.md            <- this file
  config.py            <- SEC URLs, DB connection, paths
  main.py              <- entry point (crawl + load)
  sec_index.py         <- code to fetch & parse ZIP links from SEC
  downloader.py        <- download ZIPs
  extractor.py         <- unzip + enumerate .txt files
  loader/
    __init__.py
    submission_loader.py
    coverpage_loader.py
    infotable_loader.py
    ...                <- one module per table
  db/
    connection.py      <- MariaDB connection (pymysql or mysqlclient)
    schema_notes.md    <- optional extra docs
  data/
    zips/              <- downloaded ZIP files
    staging/           <- temporary normalized tab files for LOAD DATA
  docs/
    form_13f_readme.pdf (optional local copy)
Cursor can reorganize as appropriate, but the above expresses intent.

4. Environment / configuration
Use environment variables (or .env) to keep secrets out of code:

SEC13F_DB_HOST – MariaDB host (localhost in the container)

SEC13F_DB_PORT – MariaDB port (3306)

SEC13F_DB_USER – DB user (e.g. secuser)

SEC13F_DB_PASSWORD – DB password

SEC13F_DB_NAME – Database name (sec13f)

SEC13F_DATA_DIR – base directory for ZIPs and staging (e.g. /data/sec13f)

SEC13F_USER_AGENT – custom User-Agent string required by SEC, e.g.:
"HybridFinancial 13F Loader (contact@example.com)"

SEC13F_LINK - Link to crawl

5. Required behavior / steps
5.1 Crawl SEC index and discover ZIP files
Fetch https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets.

Parse HTML to find <a> tags whose href ends with .zip.

Normalize relative URLs (prefix with https://www.sec.gov).

Deduplicate and sort the ZIP URLs.

Optionally maintain a local record (e.g. in DB or a JSON file) of which ZIPs have already been processed.

5.2 Download ZIP files
For each discovered ZIP URL:

Check if the target file already exists in data/zips/. If yes, skip download (idempotent).

Download streaming to disk.

Use the configured SEC13F_USER_AGENT header to be nice to SEC’s servers.

5.3 Extract & classify text files
Inside each ZIP:

List files, pick only *.txt (tab-delimited).

Identify which table each file corresponds to by name pattern:

e.g. if "submission" in filename → submission

"cover" or "coverpage" → coverpage

"summary" → summarypage

"othermanager2" → othermanager2

"othermanager" → othermanager (but not ...2)

"signature" → signature

"infotable" → infotable

For each recognized file:

Feed it to the corresponding loader.

5.4 Parsing / normalization
Each .txt file is a tab-delimited text file with a header row.

Requirements:

Read using UTF-8, delimiter="\t".

Strip whitespace from field values.

Convert:

Empty strings → None (or \N for LOAD DATA)

Date strings DD-MON-YYYY → YYYY-MM-DD

Numeric fields → int / BIGINT compatible values.

Example date parsing:

Input: "31-DEC-2024"

Output: "2024-12-31"

We can implement normalization either:

In Python and then write a cleaned tab file for LOAD DATA, or

Use Python value transforms while preparing bulk inserts.

5.5 Loading into MariaDB
Preferred method: LOAD DATA LOCAL INFILE for speed.

Per table, the loader should:

Create a temporary normalized .tsv file in data/staging/ with:

no header line

\t as separator

\n line endings

\N for NULLs

Execute LOAD DATA LOCAL INFILE with explicit column list.

Example (Python concept):

sql
Copy code
LOAD DATA LOCAL INFILE '/data/sec13f/staging/submission_2025Q2.tsv'
INTO TABLE submission
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
(ACCESSION_NUMBER, CIK, FILER_NAME, SUBMISSIONTYPE,
 REPORTCALENDARORQUARTER, PERIODOFREPORT,
 FILING_DATE, FILED_AS_OF_DATE, EFFECTIVE_DATE);
The loader should be idempotent:

If the same ZIP is re-processed, submission rows with the same ACCESSION_NUMBER should not be duplicated.

Strategy:

Use INSERT IGNORE or ON DUPLICATE KEY UPDATE if inserting row-by-row, or

Load into a temporary table and upsert.

For simplicity in phase 1, we can:

Truncate related tables before reloading a specific ZIP
OR

Keep a separate "imported_zip_files" tracking table to never re-import the same ZIP twice.

5.6 Incremental updates
The pipeline should support:

Initial full load:

Process all discovered ZIPs.

Subsequent runs:

Re-scan the index page.

Only download and process new ZIPs that:

Are not in data/zips/, or

Are not marked as processed in tracking table.

We can add a table:

sql
Copy code
CREATE TABLE imported_zip_files (
  zip_name      VARCHAR(255) PRIMARY KEY,
  imported_at   DATETIME NOT NULL
) ENGINE=InnoDB;
Each time we successfully finish loading a ZIP, we insert a row here.

6. Implementation notes for Cursor
Language: Python 3

Likely dependencies:

requests – HTTP client

beautifulsoup4 – HTML parsing

pymysql or mysqlclient – MariaDB connector

python-dotenv – (optional) for .env file

The code should be structured to:

Allow a top-level main.py to run the full ETL end-to-end.

Re-use our existing crawler framework where possible (e.g., request helpers, logging).

SEC politeness
Always set a meaningful User-Agent.

Consider adding small sleeps or basic rate limiting if needed.

Handle transient errors (HTTP 5xx) with retries.

7. Example usage
Once implemented:

bash
Copy code
# (Optional) activate virtualenv
cd crawl_sec13f

# .env contains DB + SEC config
python main.py
main.py should:

Read config.

Fetch and parse ZIP links.

Download any missing ZIPs.

For each new ZIP:

Extract .txt files.

Run loaders for each table.

Mark ZIP as imported.

Afterwards, the sec13f database will be populated and ready for analytics / downstream tasks.

::contentReference[oaicite:0]{index=0}