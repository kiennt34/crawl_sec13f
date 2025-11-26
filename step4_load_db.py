#!/usr/bin/env python3
"""
Step 4: Load normalized data into MariaDB.

This script:
- Reads normalized file info from JSON (from step3)
- Uses LOAD DATA LOCAL INFILE to bulk load into MariaDB
- Tracks imported files to avoid duplicates
- Creates tracking table if needed

Usage:
    python step4_load_db.py [--input normalized_files.json] [--output load_results.json]
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pymysql

from config import Config
from db.connection import get_db_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_tracking_table(conn: pymysql.Connection) -> None:
    """
    Ensure the imported_zip_files tracking table exists.
    
    Args:
        conn: Database connection
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imported_zip_files (
                zip_name VARCHAR(255) PRIMARY KEY,
                imported_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.debug("Tracking table ensured")


def get_table_column_list(table_type: str) -> List[str]:
    """
    Get column list for a table type.
    
    Args:
        table_type: Table type name
        
    Returns:
        List of column names in order
    """
    column_lists = {
        "submission": [
            "ACCESSION_NUMBER", "CIK", "FILER_NAME", "SUBMISSIONTYPE",
            "REPORTCALENDARORQUARTER", "PERIODOFREPORT", "FILING_DATE",
            "FILED_AS_OF_DATE", "EFFECTIVE_DATE"
        ],
        "coverpage": [
            "ACCESSION_NUMBER", "NAME", "STREET1", "STREET2", "CITY",
            "STATEORCOUNTRY", "ZIPCODE", "PHONE", "TYPEOFREPORT",
            "FORM13F_FILE_NUMBER"
        ],
        "signature": [
            "ACCESSION_NUMBER", "NAME", "TITLE", "PHONE", "CITY",
            "STATEORCOUNTRY", "SIGNATUREDATE"
        ],
        "summarypage": [
            "ACCESSION_NUMBER", "OTHER_INCLUDED_MANAGERS", "TABLE_ENTRY_TOTAL",
            "TABLE_VALUE_TOTAL"
        ],
        "othermanager": [
            "ACCESSION_NUMBER", "OTHERMANAGER_SK", "SEQUENCENUMBER", "NAME", "CIK"
        ],
        "othermanager2": [
            "ACCESSION_NUMBER", "SEQUENCENUMBER", "CIK", "NAME"
        ],
        "infotable": [
            "ACCESSION_NUMBER", "INFOTABLE_SK", "NAMEOFISSUER", "TITLEOFCLASS",
            "CUSIP", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL",
            "INVESTMENTDISCRETION", "OTHERMANAGERS", "VOTINGAUTH_SOLE",
            "VOTINGAUTH_SHARED", "VOTINGAUTH_NONE"
        ]
    }
    
    return column_lists.get(table_type, [])


def load_data_file(
    conn: pymysql.Connection,
    file_path: Path,
    table_name: str,
    columns: List[str]
) -> Dict[str, any]:
    """
    Load a normalized TSV file into MariaDB using LOAD DATA LOCAL INFILE.
    
    Args:
        conn: Database connection
        file_path: Path to normalized TSV file
        table_name: Target table name
        columns: List of column names
        
    Returns:
        Dictionary with load stats: {rows_loaded, errors}
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Build column list string
    columns_str = ", ".join(columns)
    
    # Build LOAD DATA query
    # Note: LOCAL keyword requires local_infile to be enabled
    # Using IGNORE to skip duplicate key errors (idempotent)
    load_sql = f"""
        LOAD DATA LOCAL INFILE %s
        IGNORE INTO TABLE {table_name}
        FIELDS TERMINATED BY '\\t'
        LINES TERMINATED BY '\\n'
        ({columns_str})
    """
    
    rows_loaded = 0
    errors = []
    
    try:
        with conn.cursor() as cursor:
            # Enable local_infile
            # Seted in mariaDB server config, uncomment if needed
            #cursor.execute("SET GLOBAL local_infile = 1")
            #cursor.execute("SET SESSION local_infile = 1")
            
            # Execute LOAD DATA
            cursor.execute(load_sql, (str(file_path),))
            rows_loaded = cursor.rowcount
            
            conn.commit()
            logger.info(f"Loaded {rows_loaded:,} rows into {table_name} from {file_path.name}")
            
    except pymysql.Error as e:
        error_msg = f"Error loading {file_path.name} into {table_name}: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        conn.rollback()
        raise
    
    return {
        "rows_loaded": rows_loaded,
        "errors": errors
    }


def mark_zip_imported(conn: pymysql.Connection, zip_name: str) -> None:
    """
    Mark a ZIP file as imported in the tracking table.
    
    Args:
        conn: Database connection
        zip_name: Name of the ZIP file
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO imported_zip_files (zip_name, imported_at)
            VALUES (%s, NOW())
            ON DUPLICATE KEY UPDATE imported_at = NOW()
        """, (zip_name,))
        conn.commit()
        logger.debug(f"Marked {zip_name} as imported")


def check_zip_imported(conn: pymysql.Connection, zip_name: str) -> bool:
    """
    Check if a ZIP file has already been imported.
    
    Args:
        conn: Database connection
        zip_name: Name of the ZIP file
        
    Returns:
        True if already imported, False otherwise
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM imported_zip_files WHERE zip_name = %s
        """, (zip_name,))
        result = cursor.fetchone()
        return result[0] > 0


def main():
    """Main entry point for step 4."""
    parser = argparse.ArgumentParser(description="Load normalized data into MariaDB")
    parser.add_argument(
        "--input",
        type=str,
        default="normalized_files.json",
        help="Input JSON file from step3 (default: normalized_files.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="load_results.json",
        help="Output JSON file path (default: load_results.json)"
    )
    parser.add_argument(
        "--skip-imported",
        action="store_true",
        default=True,
        help="Skip ZIPs that are already imported (default: True)"
    )
    parser.add_argument(
        "--table-filter",
        type=str,
        help="Load only files for this table type (for testing)"
    )
    
    args = parser.parse_args()
    
    try:
        # Read input JSON
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            sys.exit(1)
        
        with open(input_path, 'r') as f:
            input_data = json.load(f)
        
        normalized_files = input_data.get("normalized_files", [])
        
        if not normalized_files:
            logger.warning("No normalized files found in input")
            sys.exit(1)
        
        # Filter by table type if requested
        if args.table_filter:
            normalized_files = [
                nf for nf in normalized_files
                if nf.get("table_type", "").lower() == args.table_filter.lower()
            ]
            logger.info(f"Filtered to {len(normalized_files)} files for table '{args.table_filter}'")
        
        # Connect to database
        logger.info("Connecting to database...")
        conn = get_db_connection()
        
        try:
            # Ensure tracking table exists
            ensure_tracking_table(conn)
            
            # Group files by ZIP to track imports
            files_by_zip: Dict[str, List[Dict]] = {}
            for file_info in normalized_files:
                # Extract ZIP name from original path
                original_path = file_info.get("original_path", "")
                # Try to extract ZIP name from path
                zip_name = "unknown"
                if "__" in Path(original_path).name:
                    zip_name = Path(original_path).name.split("__")[0]
                
                if zip_name not in files_by_zip:
                    files_by_zip[zip_name] = []
                files_by_zip[zip_name].append(file_info)
            
            # Process each file
            load_results = []
            total_rows_loaded = 0
            zips_imported = set()
            
            for file_info in normalized_files:
                normalized_path = Path(file_info["normalized_path"])
                table_type = file_info.get("table_type", "unknown")
                
                if not normalized_path.exists():
                    logger.warning(f"File not found: {normalized_path}")
                    continue
                
                if table_type == "unknown":
                    logger.warning(f"Skipping unknown table type: {normalized_path.name}")
                    continue
                
                # Get column list
                columns = get_table_column_list(table_type)
                if not columns:
                    logger.warning(f"No column list for table type: {table_type}")
                    continue
                
                # Extract ZIP name for tracking
                original_path = file_info.get("original_path", "")
                zip_name = "unknown"
                if "__" in Path(original_path).name:
                    zip_name = Path(original_path).name.split("__")[0]
                
                # Check if ZIP already imported (if skip_imported is enabled)
                if args.skip_imported and zip_name != "unknown":
                    if check_zip_imported(conn, zip_name):
                        logger.info(f"Skipping {normalized_path.name} (ZIP {zip_name} already imported)")
                        continue
                
                try:
                    # Load data
                    stats = load_data_file(conn, normalized_path, table_type, columns)
                    
                    load_results.append({
                        "normalized_path": str(normalized_path),
                        "table_type": table_type,
                        "rows_loaded": stats["rows_loaded"],
                        "errors": stats["errors"]
                    })
                    
                    total_rows_loaded += stats["rows_loaded"]
                    
                    # Mark ZIP as imported if we've processed all its files
                    if zip_name != "unknown":
                        zips_imported.add(zip_name)
                    
                except Exception as e:
                    logger.error(f"Failed to load {normalized_path.name}: {e}")
                    load_results.append({
                        "normalized_path": str(normalized_path),
                        "table_type": table_type,
                        "rows_loaded": 0,
                        "errors": [str(e)]
                    })
                    continue
            
            # Mark all processed ZIPs as imported
            for zip_name in zips_imported:
                mark_zip_imported(conn, zip_name)
            
            # Prepare output data
            output_data = {
                "input_file": str(input_path),
                "loaded_at": None,
                "files_loaded": len(load_results),
                "total_rows_loaded": total_rows_loaded,
                "zips_imported": len(zips_imported),
                "load_results": load_results
            }
            
            # Add timestamp
            from datetime import datetime
            output_data["loaded_at"] = datetime.utcnow().isoformat()
            
            # Write output JSON
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            logger.info(f"Step 4 complete: Loaded {len(load_results)} files, {total_rows_loaded:,} rows")
            logger.info(f"Output written to: {output_path}")
            
            # Print summary
            print(f"\n✓ Step 4 Complete:")
            print(f"  Files loaded: {len(load_results)}")
            print(f"  Rows loaded: {total_rows_loaded:,}")
            print(f"  ZIPs imported: {len(zips_imported)}")
            print(f"  Output: {output_path}")
        
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Step 4 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

