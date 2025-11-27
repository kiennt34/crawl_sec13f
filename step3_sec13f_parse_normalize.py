#!/usr/bin/env python3
"""
Step 3: Parse and normalize tab-delimited files (.tsv or .txt).

This script:
- Reads extracted data files (.tsv/.txt) from JSON (from step2)
- Parses tab-delimited files
- Normalizes data (dates, numbers, nulls)
- Writes normalized TSV files to data/staging/ for LOAD DATA

Usage:
    python step3_parse_normalize.py [--input extracted_files.json] [--output normalized_files.json]
"""
import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> Optional[str]:
    """
    Convert date from DD-MON-YYYY to YYYY-MM-DD format.
    
    Args:
        date_str: Date string in DD-MON-YYYY format
        
    Returns:
        Date string in YYYY-MM-DD format, or None if invalid
    """
    if not date_str or date_str.strip() == '':
        return None
    
    date_str = date_str.strip()
    
    # Try DD-MON-YYYY format
    try:
        dt = datetime.strptime(date_str, "%d-%b-%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # Try DD-MON-YY format
    try:
        dt = datetime.strptime(date_str, "%d-%b-%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # Try YYYY-MM-DD (already normalized)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def normalize_value(value: str, field_type: str = "string") -> Any:
    """
    Normalize a field value.
    
    Args:
        value: Raw field value
        field_type: Expected type (string, int, bigint, date)
        
    Returns:
        Normalized value (None for empty/null)
    """
    if not value or value.strip() == '':
        return None
    
    value = value.strip()
    
    if field_type == "date":
        return parse_date(value)
    elif field_type == "int":
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Could not convert to int: {value}")
            return None
    elif field_type == "bigint":
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Could not convert to bigint: {value}")
            return None
    else:
        # String - just return stripped value
        return value


def get_field_types(table_type: str) -> Dict[str, str]:
    """
    Get field type mapping for a table.
    
    Args:
        table_type: Table type name
        
    Returns:
        Dictionary mapping field names to types
    """
    # Define field types based on schema
    field_types = {
        "submission": {
            "ACCESSION_NUMBER": "string",
            "CIK": "bigint",
            "FILER_NAME": "string",
            "SUBMISSIONTYPE": "string",
            "REPORTCALENDARORQUARTER": "date",
            "PERIODOFREPORT": "date",
            "FILING_DATE": "date",
            "FILED_AS_OF_DATE": "date",
            "EFFECTIVE_DATE": "date"
        },
        "coverpage": {
            "ACCESSION_NUMBER": "string",
            "NAME": "string",
            "STREET1": "string",
            "STREET2": "string",
            "CITY": "string",
            "STATEORCOUNTRY": "string",
            "ZIPCODE": "string",
            "PHONE": "string",
            "TYPEOFREPORT": "string",
            "FORM13F_FILE_NUMBER": "string"
        },
        "signature": {
            "ACCESSION_NUMBER": "string",
            "NAME": "string",
            "TITLE": "string",
            "PHONE": "string",
            "CITY": "string",
            "STATEORCOUNTRY": "string",
            "SIGNATUREDATE": "date"
        },
        "summarypage": {
            "ACCESSION_NUMBER": "string",
            "OTHER_INCLUDED_MANAGERS": "int",
            "TABLE_ENTRY_TOTAL": "int",
            "TABLE_VALUE_TOTAL": "bigint"
        },
        "othermanager": {
            "ACCESSION_NUMBER": "string",
            "OTHERMANAGER_SK": "int",
            "SEQUENCENUMBER": "int",
            "NAME": "string",
            "CIK": "bigint"
        },
        "othermanager2": {
            "ACCESSION_NUMBER": "string",
            "SEQUENCENUMBER": "int",
            "CIK": "bigint",
            "NAME": "string"
        },
        "infotable": {
            "ACCESSION_NUMBER": "string",
            "INFOTABLE_SK": "int",
            "NAMEOFISSUER": "string",
            "TITLEOFCLASS": "string",
            "CUSIP": "string",
            "VALUE": "bigint",
            "SSHPRNAMT": "bigint",
            "SSHPRNAMTTYPE": "string",
            "PUTCALL": "string",
            "INVESTMENTDISCRETION": "string",
            "OTHERMANAGERS": "string",
            "VOTINGAUTH_SOLE": "bigint",
            "VOTINGAUTH_SHARED": "bigint",
            "VOTINGAUTH_NONE": "bigint"
        }
    }
    
    return field_types.get(table_type, {})


def parse_and_normalize_file(
    input_path: Path,
    table_type: str,
    output_path: Path
) -> Dict[str, Any]:
    """
    Parse and normalize a tab-delimited file (.tsv or .txt).
    
    Args:
        input_path: Path to input data file (.tsv or .txt)
        table_type: Type of table (submission, coverpage, etc.)
        output_path: Path to write normalized TSV
        
    Returns:
        Dictionary with stats: {rows_processed, rows_written, errors}
    """
    field_types = get_field_types(table_type)
    
    if not field_types:
        logger.warning(f"Unknown table type: {table_type}, treating all fields as strings")
    
    rows_processed = 0
    rows_written = 0
    errors = []
    
    try:
        with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
            # Read as tab-delimited
            reader = csv.DictReader(infile, delimiter='\t')
            
            # Get field names from header
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValueError("No header row found")
            
            # Write normalized file
            with open(output_path, 'w', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter='\t', lineterminator='\n')
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    rows_processed += 1
                    
                    try:
                        # Normalize each field
                        normalized_row = []
                        for field_name in fieldnames:
                            raw_value = row.get(field_name, '')
                            field_type = field_types.get(field_name, "string")
                            normalized_value = normalize_value(raw_value, field_type)
                            
                            # Convert None to \N for LOAD DATA
                            if normalized_value is None:
                                normalized_row.append('\\N')
                            else:
                                normalized_row.append(str(normalized_value))
                        
                        writer.writerow(normalized_row)
                        rows_written += 1
                        
                    except Exception as e:
                        error_msg = f"Error processing row {row_num}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        continue
        
        logger.info(f"Normalized {input_path.name}: {rows_written}/{rows_processed} rows")
        
    except Exception as e:
        error_msg = f"Error processing file {input_path.name}: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        raise
    
    return {
        "rows_processed": rows_processed,
        "rows_written": rows_written,
        "errors": errors
    }


def main():
    """Main entry point for step 3."""
    parser = argparse.ArgumentParser(description="Parse and normalize text files")
    parser.add_argument(
        "--input",
        type=str,
        default="extracted_files.json",
        help="Input JSON file from step2 (default: extracted_files.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="normalized_files.json",
        help="Output JSON file path (default: normalized_files.json)"
    )
    parser.add_argument(
        "--table-filter",
        type=str,
        help="Process only files for this table type (for testing)"
    )
    
    args = parser.parse_args()
    
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
        
        extracted_files = input_data.get("extracted_files", [])
        
        if not extracted_files:
            logger.warning("No extracted files found in input")
            sys.exit(1)
        
        # Filter by table type if requested
        if args.table_filter:
            extracted_files = [
                ef for ef in extracted_files
                if ef.get("table_type", "").lower() == args.table_filter.lower()
            ]
            logger.info(f"Filtered to {len(extracted_files)} files for table '{args.table_filter}'")
        
        # Process each file
        normalized_files = []
        total_rows = 0
        total_written = 0
        
        for file_info in extracted_files:
            extracted_path = Path(file_info["extracted_path"])
            table_type = file_info.get("table_type", "unknown")
            
            if not extracted_path.exists():
                logger.warning(f"File not found: {extracted_path}")
                continue
            
            # Skip unknown table types
            if table_type == "unknown":
                logger.warning(f"Skipping unknown table type: {extracted_path.name}")
                continue
            
            # Create output path
            output_filename = f"{extracted_path.stem}_normalized.tsv"
            output_path = Config.STAGING_DIR / output_filename
            
            try:
                stats = parse_and_normalize_file(extracted_path, table_type, output_path)
                
                normalized_files.append({
                    "original_path": str(extracted_path),
                    "normalized_path": str(output_path),
                    "table_type": table_type,
                    "rows_processed": stats["rows_processed"],
                    "rows_written": stats["rows_written"],
                    "errors": stats["errors"]
                })
                
                total_rows += stats["rows_processed"]
                total_written += stats["rows_written"]
                
            except Exception as e:
                logger.error(f"Failed to normalize {extracted_path.name}: {e}")
                continue
        
        # Prepare output data
        output_data = {
            "input_file": str(input_path),
            "processed_at": None,
            "files_processed": len(normalized_files),
            "total_rows_processed": total_rows,
            "total_rows_written": total_written,
            "normalized_files": normalized_files
        }
        
        # Add timestamp
        from datetime import datetime
        output_data["processed_at"] = datetime.utcnow().isoformat()
        
        # Write output JSON
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"Step 3 complete: Normalized {len(normalized_files)} files, {total_written:,} rows")
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(f"\n✓ Step 3 Complete:")
        print(f"  Files processed: {len(normalized_files)}")
        print(f"  Rows processed: {total_rows:,}")
        print(f"  Rows written: {total_written:,}")
        print(f"  Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Step 3 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

