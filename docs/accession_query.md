# Form 13F – Filing Data Dictionary  
_For ACCESSION_NUMBER = 0000002230-13-000066 (example)_

This document explains the meaning of the columns in the joined dataset
built from:

- `submission`
- `coverpage`
- `summarypage`
- `infotable`

for a **single Form 13F filing** (one `ACCESSION_NUMBER`).

---

## 1. High-level structure

Each CSV row represents **one holding (one security)** in the filing.

- Columns from **`submission`**, **`coverpage`**, and **`summarypage`**
  repeat for every row (they describe the filing/manager as a whole).
- Columns from **`infotable`** describe the specific security in that row
  (issuer, CUSIP, shares, value, voting authority, etc.).

So:

- One `ACCESSION_NUMBER` = one **filing**
- Many `INFOTABLE_SK` values = many **holdings inside that filing**

---

## 2. Filing-level metadata (`submission`)

These columns describe the SEC filing itself:

- **ACCESSION_NUMBER**  
  Unique ID assigned by the SEC to this submission  
  (e.g. `0000002230-13-000066`).  

- **FILING_DATE**  
  Date the filing was accepted by the SEC.

- **SUBMISSIONTYPE**  
  Type of filing, e.g.:
  - `13F-HR` – Holdings report  
  - `13F-HR/A` – Amended holdings report  
  - `13F-NT` – Notice (no holdings table)  

- **CIK**  
  Central Index Key – SEC’s unique ID for the manager (filer).

- **PERIODOFREPORT**  
  Effective date for the holdings snapshot
  (usually the quarter-end, e.g. `2013-06-30`).

All holdings rows in this file share the same values for these columns.

---

## 3. Manager & report info (`coverpage`)

These columns describe **who** filed and what kind of report it is.

- **REPORTCALENDARORQUARTER**  
  Calendar date or quarter end for which holdings are reported.

- **ISAMENDMENT**  
  `Y` if this filing is an amendment; otherwise `N` or NULL.

- **AMENDMENTNO**  
  Amendment sequence number (1, 2, …).

- **AMENDMENTTYPE**  
  What the amendment does, e.g.:
  - `RESTATEMENT` – replaces prior data  
  - `NEW HOLDINGS` – adds positions only  

- **CONFDENIEDEXPIRED / DATEDENIEDEXPIRED / DATEREPORTED / REASONFORNONCONFIDENTIALITY**  
  Fields related to confidential treatment requests, if any.

- **FILINGMANAGER_NAME**  
  Legal name of the investment manager submitting the 13F.

- **FILINGMANAGER_STREET1 / STREET2 / CITY / STATEORCOUNTRY / ZIPCODE**  
  Manager’s address.

- **REPORTTYPE**  
  Type of 13F report:
  - `13F HOLDINGS REPORT`  
  - `13F NOTICE`  
  - `13F COMBINATION REPORT`  

- **FORM13FFILENUMBER**  
  SEC 13F file number for this manager (e.g. `028-12345`).

- **CRDNUMBER / SECFILENUMBER**  
  Optional registration identifiers if applicable.

- **PROVIDEINFOFORINSTRUCTION5**  
  `Y`/`N` flag indicating whether information is provided under
  instruction 5.

- **ADDITIONALINFORMATION**  
  Free-text comments from the manager (often empty).

Again, these are constant across all rows for the same `ACCESSION_NUMBER`.

---

## 4. Filing summary (`summarypage`)

These columns summarize the entire holdings table:

- **OTHER_INCLUDED_MANAGERS**  
  Number of *other* managers included in this report
  (co-filers / shared discretion).

- **TABLE_ENTRY_TOTAL**  
  Count of reported holdings (number of rows in the information table).

- **TABLE_VALUE_TOTAL**  
  Sum of **VALUE** for all holdings in the filing.

  > Important: For filings **before 2023-01-03**, VALUE is reported in
  > **thousands of dollars**. For filings on or after that date, VALUE
  > is in **actual dollars**.

- **ISCONFIDENTIALOMITTED**  
  Indicates whether some holdings are omitted due to granted
  confidential treatment.

---

## 5. Holding-level data (`infotable`)

These columns describe a **single security position** held by the manager.

### 5.1 Keys

- **ACCESSION_NUMBER**  
  Ties the holding back to its filing.

- **INFOTABLE_SK**  
  Surrogate key (row ID) for the holding within that filing.

The pair `(ACCESSION_NUMBER, INFOTABLE_SK)` is unique.

---

### 5.2 Security identification

- **NAMEOFISSUER**  
  Name of the issuer (company or fund), e.g. `APPLE INC`.

- **TITLEOFCLASS**  
  Class of security, e.g. `COM`, `CALL`, `PUT`, `ADR`.

- **CUSIP**  
  9-character CUSIP security identifier.

- **FIGI**  
  Financial Instrument Global Identifier, if present.

---

### 5.3 Position size & type

- **VALUE**  
  Market value of the holding.

  - Before 2023-01-03: value is in **thousands of USD**  
  - On/after 2023-01-03: value is in **actual USD**

- **SSHPRNAMT**  
  Number of shares or principal amount.

- **SSHPRNAMTTYPE**  
  Indicates whether SSHPRNAMT is:
  - `SH` – shares  
  - `PRN` – principal amount  

- **PUTCALL**  
  For options:
  - `PUT` or `CALL`; otherwise NULL for non-option holdings.

---

### 5.4 Discretion & other managers

- **INVESTMENTDISCRETION**  
  Who has investment discretion:
  - `SOLE` – sole discretion  
  - `SHARED` – shared discretion  
  - `NONE` – no investment discretion  

- **OTHERMANAGERS**  
  Sequence numbers of other managers (from OTHERMANAGER2 table)
  with whom discretion is shared.

---

### 5.5 Voting authority

These describe how many shares the manager can vote:

- **VOTINGAUTH_SOLE**  
  Shares for which the manager has sole voting power.

- **VOTINGAUTH_SHARED**  
  Shares with shared voting power.

- **VOTINGAUTH_NONE**  
  Shares with no voting power.

By definition:

```text
VOTINGAUTH_SOLE + VOTINGAUTH_SHARED + VOTINGAUTH_NONE
  ≈ SSHPRNAMT  (for equity positions)
