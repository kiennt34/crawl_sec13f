# Accessing EDGAR Data
*Source: SEC.gov – Accessing EDGAR Data*  
*(Extracted from uploaded HTML file)*

_Last Reviewed: June 26, 2024_

---

## Overview

All companies—foreign and domestic—must file registration statements, periodic reports, and other disclosures through the **EDGAR** system (Electronic Data Gathering, Analysis & Retrieval).

Anyone may:
- Access or **download EDGAR data for free**
- Query EDGAR using public search tools

---

## Fair Access

- **Current max request rate:** **10 requests / second**
- Use efficient, respectful crawling
- SEC may throttle abusive scripts or botnets
- Always declare a **User-Agent** header

### Sample Automated Request Headers

User-Agent: Sample Company Name AdminContact@samplecompany.com

Accept-Encoding: gzip, deflate
Host: www.sec.gov


---

## How Far Back EDGAR Data Goes

- Electronic filings begin around **1994–1995**  
- Pre-1994 filings may require a **FOIA request**

---

## Business Hours & Dissemination

- Filing acceptance: **Mon–Fri, 6:00 a.m. – 10:00 p.m. ET**
- Daily indexes are updated starting **~10:00 p.m. ET**
- Submissions after cutoff (5:30 p.m. or 10 p.m. depending on form) appear next business day

---

## Post-Acceptance Corrections & Deletions

- SEC staff may remove or correct filings for reasons including:
  - Wrong filer submitted
  - Duplicate filings
  - Unreadable documents
  - Sensitive information
- Daily corrections appear in same-day indexes
- Weekly (Saturday) rebuild merges quarterly + corrections

---

## Data APIs

JSON data is available through **REST APIs** at:

https://www.sec.gov/page/edgar-application-programming-interfaces-old

Includes:
- Submissions by CIK
- Extracted XBRL financial data

---

## EDGAR Index Files

Indexes are available from **1994Q3 to present**:

- `/Archives/edgar/daily-index/` — daily indexes  
- `/Archives/edgar/full-index/` — current-quarter "bridge" index (rolled into quarterly index at quarter end)

Each directory contains (not shown in browser):
- `index.html`
- `index.xml`
- `index.json`

### Index Data Includes:

- Company name  
- Form type  
- CIK  
- Date filed  
- File name (path to raw txt)

### Index Types:

- **company** — sorted by name  
- **form** — sorted by form type  
- **master** — sorted by CIK  
- **XBRL** — filings containing XBRL

---

## CIK (Central Index Key)

- Unique ID assigned to each filer
- Never reused
- List available:  
  https://www.sec.gov/Archives/edgar/cik-lookup-data.txt

---

## Feed & Oldloads Directories

- `/Archives/edgar/Feed/` — daily `.tar.gz` feeds  
- `/Archives/edgar/Oldloads/` — concatenated daily submissions

Each has hidden:
- `index.html`
- `index.xml`
- `index.json`

PDS spec:  
https://www.sec.gov/info/edgar/specifications/pds_dissemination_spec.pdf

---

## Paths & Directory Structure

Example raw text filing:

/Archives/edgar/data/1122304/0001193125-15-118890.txt


Post-EDGAR 7.0 alternative symbolic path:



/Archives/edgar/data/1122304/000119312515118890/0001193125-15-118890.txt


### Additional Useful Files:

- HTML index:  
  `/Archives/edgar/data/1122304/0001193125-15-118890-index.html`

- SGML header:  
  `/Archives/edgar/data/.../0001193125-15-118890.hdr.sgml`

### Accession Number Format

`0001193125-15-118890`

- First block: filer’s CIK  
- Next block: year  
- Final digits: sequential submission number

---

## Directory Browsing

Allowed for CIK and accession directories:



https://www.sec.gov/Archives/edgar/data/51143/

https://www.sec.gov/Archives/edgar/data/51143/000104746917001061/


Hidden files:
- `index.html`
- `index.xml`
- `index.json`

---

## Virtual Private Reference Room (VPRR)

Contains PDF scans of paper filings (not indexed):



https://www.sec.gov/Archives/edgar/vprr/index.html


Directory names = first four digits of Film Number / DCN.

Each directory (hidden):
- index.html
- index.xml
- index.json

---

## Monthly Directory

XBRL RSS archives (from April 2005):



https://www.sec.gov/Archives/edgar/monthly/


More info: Structured Disclosure RSS Feeds.

---

## CIK, Ticker, and Exchange Lists

Periodically updated; not guaranteed complete.

- Company tickers:  
  https://www.sec.gov/files/company_tickers.json
- Company tickers + exchange:  
  https://www.sec.gov/files/company_tickers_exchange.json
- Mutual fund tickers:  
  https://www.sec.gov/files/company_tickers_mf.json

---

## Other Sources of EDGAR / SEC Data

- SEC Webmaster FAQ  
- DERA datasets:
  - Mutual fund summaries
  - Crowdfunding
  - Form D
  - Regulation A
  - Transfer Agent
  - EDGAR Logfiles
  - Financial Statements datasets
  - EDGAR Filing Count

---

## Contacts

- EDGAR Filer Support  
  https://www.sec.gov/edgar/filer-information/contact-filer-support

- General SEC contact  
  https://www.sec.gov/contact.shtml

- Technical/structured data questions:  
  structureddata@sec.gov