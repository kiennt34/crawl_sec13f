USE sec13f;

-- ============================================================
-- 1. SUBMISSION - Fixed 2025-11-26
-- ============================================================
CREATE TABLE submission (
  ACCESSION_NUMBER           VARCHAR(25) NOT NULL,
  FILING_DATE                DATE,
  SUBMISSIONTYPE             VARCHAR(10),
  CIK                        VARCHAR(10),
  PERIODOFREPORT             DATE,
  PRIMARY KEY (ACCESSION_NUMBER),
  INDEX idx_sub_cik_period (CIK, PERIODOFREPORT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 2. COVERPAGE (1-to-1 with submission) - Fixed 2025-11-26
-- ============================================================
CREATE TABLE coverpage (
    ACCESSION_NUMBER               VARCHAR(25) NOT NULL,
    REPORTCALENDARORQUARTER        DATE,
    ISAMENDMENT                    CHAR(1),
    AMENDMENTNO                    SMALLINT,
    AMENDMENTTYPE                  VARCHAR(20),
    CONFDENIEDEXPIRED              CHAR(1),
    DATEDENIEDEXPIRED              DATE,
    DATEREPORTED                   DATE,
    REASONFORNONCONFIDENTIALITY    VARCHAR(40),
    FILINGMANAGER_NAME             VARCHAR(150),
    FILINGMANAGER_STREET1          VARCHAR(40),
    FILINGMANAGER_STREET2          VARCHAR(40),
    FILINGMANAGER_CITY             VARCHAR(30),
    FILINGMANAGER_STATEORCOUNTRY   CHAR(2),
    FILINGMANAGER_ZIPCODE          VARCHAR(10),
    REPORTTYPE                     VARCHAR(30),
    FORM13FFILENUMBER              VARCHAR(17),
    CRDNUMBER                      VARCHAR(9),
    SECFILENUMBER                  VARCHAR(17),
    PROVIDEINFOFORINSTRUCTION5     CHAR(1),
    ADDITIONALINFORMATION          VARCHAR(4000),

    PRIMARY KEY (ACCESSION_NUMBER),
    CONSTRAINT fk_cover_sub
        FOREIGN KEY (ACCESSION_NUMBER)
        REFERENCES submission(ACCESSION_NUMBER)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 3. SIGNATURE (1-to-1 with submission) - Fixed 2025-11-26
-- ============================================================
CREATE TABLE signature (
    ACCESSION_NUMBER   VARCHAR(25) NOT NULL,
    NAME               VARCHAR(150),
    TITLE              VARCHAR(60),
    PHONE              VARCHAR(20),
    SIGNATURE          VARCHAR(150),
    CITY               VARCHAR(30),
    STATEORCOUNTRY     CHAR(2),
    SIGNATUREDATE      DATE,

    PRIMARY KEY (ACCESSION_NUMBER),

    CONSTRAINT fk_sig_sub
        FOREIGN KEY (ACCESSION_NUMBER)
        REFERENCES submission(ACCESSION_NUMBER)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 4. SUMMARYPAGE (1-to-1 with submission) - Fixed 2025-11-26
-- ============================================================
CREATE TABLE summarypage (
  ACCESSION_NUMBER         VARCHAR2(25) NOT NULL,
  OTHER_INCLUDED_MANAGERS  NUMBER(3),
  TABLE_ENTRY_TOTAL        NUMBER(6),
  TABLE_VALUE_TOTAL        NUMBER(16),
  ISCONFIDENTIALOMITTED    CHAR(1),
  PRIMARY KEY (ACCESSION_NUMBER),
  CONSTRAINT fk_sum_sub
    FOREIGN KEY (ACCESSION_NUMBER)
    REFERENCES submission(ACCESSION_NUMBER)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 5. OTHERMANAGER (0..n per submission) - Fixed 2025-11-26
-- ============================================================
CREATE TABLE othermanager (
    ACCESSION_NUMBER   VARCHAR(25) NOT NULL,
    OTHERMANAGER_SK    SMALLINT NOT NULL,
    CIK                VARCHAR(10),
    FORM13FFILENUMBER  VARCHAR(17),
    CRDNUMBER          VARCHAR(9),
    SECFILENUMBER      VARCHAR(17),
    NAME               VARCHAR(150),

    PRIMARY KEY (ACCESSION_NUMBER, OTHERMANAGER_SK),
    KEY idx_om_cik (CIK),

    CONSTRAINT fk_om_sub
        FOREIGN KEY (ACCESSION_NUMBER)
        REFERENCES submission(ACCESSION_NUMBER)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 6. OTHERMANAGER2 (0..n per submission) - Fixed 2025-11-26
-- ============================================================
CREATE TABLE othermanager2 (
    ACCESSION_NUMBER   VARCHAR(25) NOT NULL,
    SEQUENCENUMBER     SMALLINT NOT NULL,
    CIK                VARCHAR(10),
    FORM13FFILENUMBER  VARCHAR(17),
    CRDNUMBER          VARCHAR(9),
    SECFILENUMBER      VARCHAR(17),
    NAME               VARCHAR(150),

    PRIMARY KEY (ACCESSION_NUMBER, SEQUENCENUMBER),
    KEY idx_om2_cik (CIK),

    CONSTRAINT fk_om2_sub
        FOREIGN KEY (ACCESSION_NUMBER)
        REFERENCES submission(ACCESSION_NUMBER)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 7. INFOTABLE (HOLDINGS) – HUGE TABLE - Fixed 2025-11-25 
-- ============================================================
CREATE TABLE infotable (
    ACCESSION_NUMBER      VARCHAR(25) NOT NULL,
    INFOTABLE_SK          BIGINT NOT NULL,          -- NUMBER(38)
    
    NAMEOFISSUER          VARCHAR(200),
    TITLEOFCLASS          VARCHAR(150),
    CUSIP                 VARCHAR(9),
    FIGI                  VARCHAR(12), 
    VALUE                 BIGINT,                   -- NUMBER(16)
    SSHPRNAMT             BIGINT,                   -- NUMBER(16)
    SSHPRNAMTTYPE         VARCHAR(10),
    PUTCALL               VARCHAR(10),
    INVESTMENTDISCRETION  VARCHAR(10),
    OTHERMANAGERS         VARCHAR(255),
    VOTINGAUTH_SOLE       BIGINT,                   -- NUMBER(16)
    VOTINGAUTH_SHARED     BIGINT,                   -- NUMBER(16)
    VOTINGAUTH_NONE       BIGINT,                   -- NUMBER(16)

    PRIMARY KEY (ACCESSION_NUMBER, INFOTABLE_SK),

    KEY idx_info_cusip (CUSIP),
    KEY idx_info_issuer (NAMEOFISSUER),
    KEY idx_info_accession (ACCESSION_NUMBER),

    CONSTRAINT fk_info_sub
        FOREIGN KEY (ACCESSION_NUMBER)
        REFERENCES submission(ACCESSION_NUMBER)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ============================================================
-- 8. IMPORTED_ZIP_FILES (Tracking table for data loading)
-- ============================================================
CREATE TABLE IF NOT EXISTS imported_zip_files (
  zip_name VARCHAR(255) PRIMARY KEY,
  imported_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- TABLES TO RECREATE (DROP IF EXISTS)
-- ============================================================

-- DROP TABLE IF EXISTS imported_zip_files;
-- DROP TABLE IF EXISTS infotable;
-- DROP TABLE IF EXISTS othermanager2;
-- DROP TABLE IF EXISTS othermanager;
-- DROP TABLE IF EXISTS summarypage;
-- DROP TABLE IF EXISTS signature;
-- DROP TABLE IF EXISTS coverpage;
-- DROP TABLE IF EXISTS submission;
