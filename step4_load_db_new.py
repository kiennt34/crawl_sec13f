#!/usr/bin/env python3
"""
Step 4 (Optimized): Load normalized data into MariaDB - FAST VERSION.

This script:
- Reads normalized file info from JSON (from step3) or scans staging directory
- Uses LOAD DATA INFILE (no LOCAL - files must be on DB server)
- Disables FOREIGN_KEY_CHECKS and UNIQUE_CHECKS for maximum speed
- Groups files by table type for batch processing
- Tracks imported ZIPs in database table (imported_zip_files) to avoid duplicates
- NOTE: Files are NOT renamed or moved - only data is loaded into database

Usage:
    # Start fresh (clear tracking table)
    python step4_load_db_new.py --staging-dir /path/to/staging --clear-imported
    
    # Force import even if already tracked
    python step4_load_db_new.py --staging-dir /path/to/staging --no-skip-imported
    
    # Normal usage (skip already imported)
    python step4_load_db_new.py --staging-dir /path/to/staging
    
    # Check what's already imported
    python step4_load_db_new.py --show-imported
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import pymysql

from config import Config
from db.connection import get_db_connection

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_connection_alive(conn: pymysql.Connection) -> bool:
    """
    Check if database connection is still alive.
    
    Args:
        conn: Database connection to check
        
    Returns:
        True if connection is alive, False otherwise
    """
    try:
        conn.ping(reconnect=False)
        return True
    except:
        return False


def ensure_connection(conn: pymysql.Connection) -> pymysql.Connection:
    """
    Ensure database connection is alive, reconnect if needed.
    
    Args:
        conn: Database connection (may be closed)
        
    Returns:
        Active database connection (either original or new)
    """
    if not is_connection_alive(conn):
        logger.warning("Database connection lost, reconnecting...")
        try:
            # Try to ping with reconnect
            conn.ping(reconnect=True)
            logger.info("Successfully reconnected to database")
        except Exception as e:
            logger.error(f"Failed to reconnect using ping: {e}")
            # If ping fails, get a fresh connection
            try:
                conn.close()
            except:
                pass
            conn = get_db_connection()
            logger.info("Created new database connection")
    return conn


class ProgressTracker:
    """Track loading progress with speed and ETA calculations."""
    
    def __init__(self, total_lines: int):
        self.total_lines = total_lines
        self.processed_lines = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_update_lines = 0
        
    def update(self, lines_processed: int) -> None:
        """Update progress with new lines processed."""
        self.processed_lines += lines_processed
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Calculate speed (lines per second)
        if elapsed > 0:
            overall_speed = self.processed_lines / elapsed
        else:
            overall_speed = 0
        
        # Calculate recent speed (last 10 seconds or so)
        recent_elapsed = current_time - self.last_update_time
        if recent_elapsed > 5:  # Update every 5 seconds
            recent_lines = self.processed_lines - self.last_update_lines
            recent_speed = recent_lines / recent_elapsed if recent_elapsed > 0 else 0
            self.last_update_time = current_time
            self.last_update_lines = self.processed_lines
        else:
            recent_speed = overall_speed
        
        # Calculate progress percentage
        progress_pct = (self.processed_lines / self.total_lines * 100) if self.total_lines > 0 else 0
        
        # Calculate ETA
        remaining_lines = self.total_lines - self.processed_lines
        if recent_speed > 0:
            eta_seconds = remaining_lines / recent_speed
        elif overall_speed > 0:
            eta_seconds = remaining_lines / overall_speed
        else:
            eta_seconds = 0
        
        # Format time
        def format_time(seconds: float) -> str:
            if seconds < 60:
                return f"{seconds:.0f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}h{minutes}m"
        
        # Format speed
        def format_speed(lines_per_sec: float) -> str:
            if lines_per_sec >= 1000000:
                return f"{lines_per_sec/1000000:.1f}M lines/s"
            elif lines_per_sec >= 1000:
                return f"{lines_per_sec/1000:.1f}K lines/s"
            else:
                return f"{lines_per_sec:.0f} lines/s"
        
        # Print progress
        print(
            f"\r[Progress] {progress_pct:.1f}% | "
            f"Lines: {self.processed_lines:,}/{self.total_lines:,} | "
            f"Speed: {format_speed(recent_speed)} | "
            f"Elapsed: {format_time(elapsed)} | "
            f"ETA: {format_time(eta_seconds)}",
            end="", flush=True
        )
    
    def finish(self) -> None:
        """Print final progress summary."""
        elapsed = time.time() - self.start_time
        overall_speed = self.processed_lines / elapsed if elapsed > 0 else 0
        
        def format_speed(lines_per_sec: float) -> str:
            if lines_per_sec >= 1000000:
                return f"{lines_per_sec/1000000:.1f}M lines/s"
            elif lines_per_sec >= 1000:
                return f"{lines_per_sec/1000:.1f}K lines/s"
            else:
                return f"{lines_per_sec:.0f} lines/s"
        
        def format_time(seconds: float) -> str:
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                return f"{hours}h{minutes}m{secs}s"
        
        print()  # New line after progress
        logger.info(
            f"Progress complete: {self.processed_lines:,}/{self.total_lines:,} lines "
            f"({self.processed_lines/self.total_lines*100:.1f}%) in {format_time(elapsed)} "
            f"at {format_speed(overall_speed)}"
        )


def count_lines_fast(file_path: Path) -> int:
    """
    Quickly count lines in a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Number of lines
    """
    try:
        with open(file_path, 'rb') as f:
            # Use buffered reading for speed
            count = 0
            buf_size = 1024 * 1024  # 1MB buffer
            while True:
                chunk = f.read(buf_size)
                if not chunk:
                    break
                count += chunk.count(b'\n')
            return count
    except Exception as e:
        logger.warning(f"Could not count lines in {file_path}: {e}, using 0")
        return 0


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
            "CUSIP", "FIGI", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL",
            "INVESTMENTDISCRETION", "OTHERMANAGERS", "VOTINGAUTH_SOLE",
            "VOTINGAUTH_SHARED", "VOTINGAUTH_NONE"
        ]
    }
    
    return column_lists.get(table_type, [])


def disable_checks(conn: pymysql.Connection) -> None:
    """
    Disable foreign key and unique checks for faster loading.
    
    Args:
        conn: Database connection
    """
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("SET UNIQUE_CHECKS = 0")
        conn.commit()
        logger.info("Disabled FOREIGN_KEY_CHECKS and UNIQUE_CHECKS")


def enable_checks(conn: pymysql.Connection) -> None:
    """
    Re-enable foreign key and unique checks.
    
    Args:
        conn: Database connection
    """
    with conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        cursor.execute("SET UNIQUE_CHECKS = 1")
        conn.commit()
        logger.info("Re-enabled FOREIGN_KEY_CHECKS and UNIQUE_CHECKS")


def load_data_file_fast(
    conn: pymysql.Connection,
    file_path: Path,
    table_name: str,
    columns: List[str],
    progress_tracker: Optional[ProgressTracker] = None,
    max_retries: int = 3,
    local_infile: bool = False
) -> Tuple[int, List[str], pymysql.Connection]:
    """
    Load a normalized TSV file into MariaDB using LOAD DATA INFILE (fast, no LOCAL).
    
    IMPORTANT: File must be accessible from the database server (not from client).
    - Files must be on the same machine as the DB server
    - Use absolute path that the DB server can access
    - Ensure secure_file_priv allows reading from the file's directory
    - This is much faster than LOAD DATA LOCAL INFILE
    
    Args:
        conn: Database connection
        file_path: Path to normalized TSV file (will be converted to absolute path)
        table_name: Target table name
        columns: List of column names
        progress_tracker: Optional progress tracker for reporting
        max_retries: Maximum number of retry attempts on connection loss
        
    Returns:
        Tuple of (rows_loaded, errors, connection)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get absolute path - DB server needs to access this file
    # The path must be accessible from the MariaDB server's perspective
    abs_path = file_path.resolve()
    
    # Build column list string
    columns_str = ", ".join(columns)
    
    # Build LOAD DATA query (NO LOCAL - file must be on server)
    # Using IGNORE to skip duplicate key errors (idempotent)
    if local_infile:
        load_sql = f"""
            LOAD DATA LOCAL INFILE %s
            IGNORE INTO TABLE {table_name}
            FIELDS TERMINATED BY '\\t'
            LINES TERMINATED BY '\\n'
            ({columns_str})
        """
    else:
        load_sql = f"""
            LOAD DATA INFILE %s
            IGNORE INTO TABLE {table_name}
            FIELDS TERMINATED BY '\\t'
            LINES TERMINATED BY '\\n'
            ({columns_str})
        """
    
    rows_loaded = 0
    errors = []
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Ensure connection is alive before operation
            conn = ensure_connection(conn)
            
            with conn.cursor() as cursor:
                # Execute LOAD DATA (file must be on DB server)
                cursor.execute(load_sql, (str(abs_path),))
                rows_loaded = cursor.rowcount
                
                conn.commit()
                
                # Update progress tracker
                if progress_tracker:
                    progress_tracker.update(rows_loaded)
                
                logger.debug(f"Loaded {rows_loaded:,} rows into {table_name} from {file_path.name}")
                break  # Success, exit retry loop
                
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
            retry_count += 1
            error_code = e.args[0] if e.args else 0
            
            # Check if it's a connection-related error
            if error_code in (0, 2013, 2006) and retry_count <= max_retries:  # Lost connection errors
                logger.warning(f"Connection lost while loading {file_path.name}: {e}, retry {retry_count}/{max_retries}")
                time.sleep(2 * retry_count)  # Exponential backoff
                try:
                    conn.close()
                except:
                    pass
                conn = get_db_connection()
                continue
            else:
                # Non-recoverable error or max retries exceeded
                error_msg = f"Error loading {file_path.name} into {table_name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                try:
                    conn.rollback()
                except:
                    pass
                raise
                
        except pymysql.Error as e:
            error_msg = f"Error loading {file_path.name} into {table_name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            try:
                conn.rollback()
            except:
                pass
            raise
    
    return rows_loaded, errors, conn


def load_table_batch(
    conn: pymysql.Connection,
    table_type: str,
    file_paths: List[Path],
    columns: List[str],
    progress_tracker: Optional[ProgressTracker] = None,
    local_infile: bool = False
) -> Dict[str, any]:
    """
    Load multiple files for the same table type in a batch.
    
    Args:
        conn: Database connection
        table_type: Table type name
        file_paths: List of file paths to load
        columns: List of column names
        progress_tracker: Optional progress tracker for reporting
        
    Returns:
        Dictionary with batch stats
    """
    batch_start = time.time()
    total_rows = 0
    files_loaded = 0
    all_errors = []
    
    logger.info(f"Loading {len(file_paths)} files into {table_type} table...")
    logger.info(f"Local infile mode: {'ENABLED' if local_infile else 'DISABLED'}")
    
    for idx, file_path in enumerate(file_paths, 1):
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            all_errors.append(f"File not found: {file_path}")
            continue
        
        try:
            rows_loaded, errors, conn = load_data_file_fast(
                conn, file_path, table_type, columns, progress_tracker, local_infile=local_infile
            )
            total_rows += rows_loaded
            files_loaded += 1
            if errors:
                all_errors.extend(errors)
        except Exception as e:
            logger.error(f"Failed to load {file_path.name}: {e}")
            all_errors.append(str(e))
            continue
    
    batch_time = time.time() - batch_start
    logger.info(
        f"Batch complete: {table_type} - {files_loaded}/{len(file_paths)} files, "
        f"{total_rows:,} rows in {batch_time:.1f}s"
    )
    
    return {
        "table_type": table_type,
        "files_processed": files_loaded,
        "files_total": len(file_paths),
        "rows_loaded": total_rows,
        "errors": all_errors,
        "time_seconds": batch_time
    }


def mark_zip_imported(conn: pymysql.Connection, zip_name: str) -> pymysql.Connection:
    """
    Mark a ZIP file as imported in the tracking table.
    
    Args:
        conn: Database connection
        zip_name: Name of the ZIP file
        
    Returns:
        Active database connection
    """
    # Ensure connection is alive
    conn = ensure_connection(conn)
    
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO imported_zip_files (zip_name, imported_at)
            VALUES (%s, NOW())
            ON DUPLICATE KEY UPDATE imported_at = NOW()
        """, (zip_name,))
        conn.commit()
        logger.debug(f"Marked {zip_name} as imported")
    return conn


def check_zip_imported(conn: pymysql.Connection, zip_name: str) -> Tuple[bool, pymysql.Connection]:
    """
    Check if a ZIP file has already been imported.
    
    Args:
        conn: Database connection
        zip_name: Name of the ZIP file
        
    Returns:
        Tuple of (is_imported, connection)
    """
    # Ensure connection is alive
    conn = ensure_connection(conn)
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM imported_zip_files WHERE zip_name = %s
        """, (zip_name,))
        result = cursor.fetchone()
        return result[0] > 0, conn


def list_imported_zips(conn: pymysql.Connection) -> List[str]:
    """
    List all imported ZIP files.
    
    Args:
        conn: Database connection
        
    Returns:
        List of imported ZIP names
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT zip_name, imported_at 
            FROM imported_zip_files 
            ORDER BY imported_at DESC
        """)
        results = cursor.fetchall()
        return [row[0] for row in results]


def clear_imported_zips(conn: pymysql.Connection) -> int:
    """
    Clear all imported ZIP file tracking records.
    
    Args:
        conn: Database connection
        
    Returns:
        Number of records deleted
    """
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM imported_zip_files")
        count = cursor.rowcount
        conn.commit()
        return count


def find_files_in_staging(staging_dir: Path, table_type: Optional[str] = None) -> Dict[str, List[Path]]:
    """
    Find normalized TSV files in staging directory.
    
    Args:
        staging_dir: Staging directory path
        table_type: Optional table type filter
        
    Returns:
        Dictionary mapping table_type -> list of file paths
    """
    files_by_table = defaultdict(list)
    
    pattern = "*_normalized.tsv"
    if table_type:
        pattern = f"*__{table_type.upper()}_normalized.tsv"
    
    for file_path in staging_dir.glob(pattern):
        # Extract table type from filename
        # Format: ZIPNAME__TABLETYPE_normalized.tsv
        name_parts = file_path.stem.split("__")
        if len(name_parts) >= 2:
            file_table_type = name_parts[1].lower().replace("_normalized", "")
            if not table_type or file_table_type == table_type.lower():
                files_by_table[file_table_type].append(file_path)
    
    return dict(files_by_table)


def main():
    """Main entry point for step 4 (optimized)."""
    parser = argparse.ArgumentParser(description="Load normalized data into MariaDB (FAST)")
    parser.add_argument(
        "--input",
        type=str,
        help="Input JSON file from step3 (optional if using --staging-dir)"
    )
    parser.add_argument(
        "--staging-dir",
        type=str,
        help="Staging directory with normalized TSV files (alternative to --input)"
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
        "--no-skip-imported",
        action="store_false",
        dest="skip_imported",
        help="Disable skip-imported check (force import even if already imported)"
    )
    parser.add_argument(
        "--clear-imported",
        action="store_true",
        help="Clear the imported_zip_files tracking table before starting (fresh start)"
    )
    parser.add_argument(
        "--table",
        type=str,
        help="Load only files for this table type (e.g., submission, infotable)"
    )
    parser.add_argument(
        "--disable-checks",
        action="store_true",
        default=True,
        help="Disable FOREIGN_KEY_CHECKS and UNIQUE_CHECKS for speed (default: True)"
    )
    parser.add_argument(
        "--total-lines",
        type=int,
        default=111335524,
        help="Total expected lines for progress tracking (default: 111335524)"
    )
    parser.add_argument(
        "--show-imported",
        action="store_true",
        help="Show list of already imported ZIPs and exit"
    )
    
    parser.add_argument(
        "--local-infile",
        action="store_true",
        default=False,
        help="Use LOAD DATA LOCAL INFILE for loading data (default: False)"
    )
    
    parser.add_argument(
        "--init-table-only",
        action="store_true",
        default=False,
        help="Initialize tables only without loading data (default: False)"
    )
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        # Determine file source
        if args.staging_dir:
            # Use staging directory directly
            staging_dir = Path(args.staging_dir)
            if not staging_dir.exists():
                logger.error(f"Staging directory not found: {staging_dir}")
                sys.exit(1)
            
            logger.info(f"Scanning staging directory: {staging_dir}")
            files_by_table = find_files_in_staging(staging_dir, args.table)
            
            # Convert to normalized_files format for compatibility
            normalized_files = []
            for table_type, file_paths in files_by_table.items():
                for file_path in file_paths:
                    normalized_files.append({
                        "normalized_path": str(file_path),
                        "table_type": table_type,
                        "original_path": str(file_path)  # Use same path for tracking
                    })
            
        elif args.input:
            # Read from JSON input
            input_path = Path(args.input)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                sys.exit(1)
            
            with open(input_path, 'r') as f:
                input_data = json.load(f)
            
            normalized_files = input_data.get("normalized_files", [])
        else:
            logger.error("Must provide either --input or --staging-dir")
            sys.exit(1)
        
        if not normalized_files:
            logger.warning("No normalized files found")
            sys.exit(1)
        
        # Filter by table type if requested
        if args.table:
            normalized_files = [
                nf for nf in normalized_files
                if nf.get("table_type", "").lower() == args.table.lower()
            ]
            logger.info(f"Filtered to {len(normalized_files)} files for table '{args.table}'")
        
        # Group files by table type for batch processing
        files_by_table: Dict[str, List[Dict]] = defaultdict(list)
        for file_info in normalized_files:
            table_type = file_info.get("table_type", "unknown")
            if table_type != "unknown":
                files_by_table[table_type].append(file_info)
        
        logger.info(f"Found files for {len(files_by_table)} table types")
        for table_type, files in files_by_table.items():
            logger.info(f"  {table_type}: {len(files)} files")
        
        # Connect to database
        logger.info("Connecting to database...")
        conn = get_db_connection()
        
        try:
            # Ensure tracking table exists
            ensure_tracking_table(conn)
            
            # Clear imported tracking if requested (fresh start)
            if args.clear_imported:
                count = clear_imported_zips(conn)
                logger.info(f"Cleared {count} imported ZIP tracking records (fresh start)")
                print(f"✓ Cleared {count} imported ZIP records - starting fresh")
            
            # Show imported ZIPs if requested
            if args.show_imported:
                imported_zips = list_imported_zips(conn)
                print(f"\nAlready imported ZIPs ({len(imported_zips)}):")
                for zip_name in imported_zips:
                    print(f"  - {zip_name}")
                sys.exit(0)
            
            # Initialize progress tracker
            progress_tracker = ProgressTracker(args.total_lines)
            logger.info(f"Progress tracking initialized for {args.total_lines:,} total lines")
            print()  # Empty line for progress display
            
            # Disable checks for speed
            if args.disable_checks:
                disable_checks(conn)
            
            # Process files by table type (batch processing)
            load_results = []
            total_rows_loaded = 0
            zips_imported = set()
            
            # Process tables in order: submission first (for FK dependencies)
            table_order = ["submission", "coverpage", "signature", "summarypage", 
                          "othermanager", "othermanager2", "infotable"]
            
            for table_type in table_order:
                if table_type not in files_by_table:
                    continue
                
                file_infos = files_by_table[table_type]
                columns = get_table_column_list(table_type)
                
                if not columns:
                    logger.warning(f"No column list for table type: {table_type}")
                    continue
                
                # Collect file paths
                file_paths = []
                zip_names_for_table = set()
                
                for file_info in file_infos:
                    normalized_path = Path(file_info["normalized_path"])
                    
                    if not normalized_path.exists():
                        logger.warning(f"File not found: {normalized_path}")
                        continue
                    
                    # Extract ZIP name for tracking
                    # Try to extract from normalized_path first (most reliable)
                    zip_name = "unknown"
                    normalized_filename = normalized_path.name
                    
                    # Pattern: ZIPNAME__TABLETYPE_normalized.tsv
                    if "__" in normalized_filename:
                        zip_name = normalized_filename.split("__")[0]
                        logger.debug(f"Extracted ZIP name '{zip_name}' from filename '{normalized_filename}'")
                    else:
                        # Fallback to original_path if available
                        original_path = file_info.get("original_path", "")
                        if original_path and "__" in Path(original_path).name:
                            zip_name = Path(original_path).name.split("__")[0]
                            logger.debug(f"Extracted ZIP name '{zip_name}' from original_path '{original_path}'")
                        else:
                            logger.warning(f"Could not extract ZIP name from '{normalized_filename}' (no '__' separator found)")
                    
                    # Check if ZIP already imported (if skip_imported is enabled)
                    if args.skip_imported and zip_name != "unknown":
                        is_imported, conn = check_zip_imported(conn, zip_name)
                        if is_imported:
                            logger.info(f"Skipping {normalized_path.name} (ZIP '{zip_name}' already imported)")
                            continue
                        else:
                            logger.debug(f"ZIP '{zip_name}' not yet imported, will process {normalized_path.name}")
                    
                    file_paths.append(normalized_path)
                    if zip_name != "unknown":
                        zip_names_for_table.add(zip_name)
                
                if not file_paths:
                    logger.info(f"No files to load for {table_type}")
                    continue
                
                # Load batch
                try:
                    batch_result = load_table_batch(
                        conn, table_type, file_paths, columns, progress_tracker, local_infile=args.local_infile
                    )
                    load_results.append(batch_result)
                    total_rows_loaded += batch_result["rows_loaded"]
                    zips_imported.update(zip_names_for_table)
                except Exception as e:
                    logger.error(f"Failed to load batch for {table_type}: {e}")
                    load_results.append({
                        "table_type": table_type,
                        "files_processed": 0,
                        "files_total": len(file_paths),
                        "rows_loaded": 0,
                        "errors": [str(e)],
                        "time_seconds": 0
                    })
            
            # Finish progress tracking
            progress_tracker.finish()
            
            # Re-enable checks
            if args.disable_checks:
                enable_checks(conn)
            
            # Mark all processed ZIPs as imported
            for zip_name in zips_imported:
                conn = mark_zip_imported(conn, zip_name)
            
            # Prepare output data
            total_time = time.time() - start_time
            output_data = {
                "input_file": args.input or str(args.staging_dir),
                "loaded_at": None,
                "files_loaded": sum(r.get("files_processed", 0) for r in load_results),
                "total_rows_loaded": total_rows_loaded,
                "zips_imported": len(zips_imported),
                "total_time_seconds": total_time,
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
            
            logger.info(f"Step 4 complete: Loaded {output_data['files_loaded']} files, {total_rows_loaded:,} rows in {total_time:.1f}s")
            logger.info(f"Output written to: {output_path}")
            
            # Print summary
            print(f"\n✓ Step 4 Complete (Optimized):")
            print(f"  Files loaded: {output_data['files_loaded']}")
            print(f"  Rows loaded: {total_rows_loaded:,}")
            print(f"  ZIPs imported: {len(zips_imported)}")
            print(f"  Total time: {total_time:.1f}s")
            print(f"  Output: {output_path}")
        
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Step 4 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

