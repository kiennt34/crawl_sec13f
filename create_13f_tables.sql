USE sec13f;

-- ============================================================
-- 1. SUBMISSION
-- ============================================================
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


-- ============================================================
-- 2. COVERPAGE (1-to-1 with submission)
-- ============================================================
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


-- ============================================================
-- 3. SIGNATURE (1-to-1 with submission)
-- ============================================================
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


-- ============================================================
-- 4. SUMMARYPAGE (1-to-1 with submission)
-- ============================================================
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


-- ============================================================
-- 5. OTHERMANAGER (0..n per submission)
-- ============================================================
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


-- ============================================================
-- 6. OTHERMANAGER2 (0..n per submission)
-- ============================================================
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


-- ============================================================
-- 7. INFOTABLE (HOLDINGS) – HUGE TABLE
-- ============================================================
CREATE TABLE infotable (
  ACCESSION_NUMBER      VARCHAR(20) NOT NULL,
  INFOTABLE_SK          INT NOT NULL,

  NAMEOFISSUER          VARCHAR(255),
  TITLEOFCLASS          VARCHAR(100),
  CUSIP                 VARCHAR(20),
  FIGI                  VARCHAR(20), 
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

