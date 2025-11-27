SELECT
  NAMEOFISSUER,
  CUSIP,
  SUM(SSHPRNAMT) AS shares,
  SUM(VALUE) AS value
FROM infotable i
JOIN submission s USING (ACCESSION_NUMBER)
WHERE s.CIK = :cik
  AND s.PERIODOFREPORT >= '2023-01-01'
GROUP BY NAMEOFISSUER, CUSIP;

select * from submission s
JOIN sec13f.coverpage c 
ON s.accession_number = c.ACCESSION_NUMBER ;

SELECT NAMEOFISSUER, CUSIP, SUM(VALUE) AS total_value
FROM infotable
WHERE CUSIP = '037833100' and value is not null
GROUP BY NAMEOFISSUER, CUSIP
ORDER BY total_value DESC;

select count(*) from infotable where value is null; -- 106.704.841
 SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE sec13f.submission;
SET FOREIGN_KEY_CHECKS = 1;