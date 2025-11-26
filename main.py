#!/usr/bin/env python3
"""
Main orchestrator script to run all ETL steps sequentially.

This script can be used to run the full pipeline, but the individual
step scripts (step1_crawl.py, step2_download_extract.py, etc.) are
designed to be run independently for workflow automation (e.g., n8n).

Usage:
    python main.py [--step N] [--all]
"""
import argparse
import logging
import subprocess
import sys
from pathlib import Path

from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_step(step_num: int, args: list = None) -> bool:
    """
    Run a specific step script.
    
    Args:
        step_num: Step number (1-4)
        args: Additional arguments to pass to the script
        
    Returns:
        True if successful, False otherwise
    """
    step_scripts = {
        1: "step1_crawl.py",
        2: "step2_download_extract.py",
        3: "step3_parse_normalize.py",
        4: "step4_load_db.py"
    }
    
    if step_num not in step_scripts:
        logger.error(f"Invalid step number: {step_num}. Must be 1-4.")
        return False
    
    script_name = step_scripts[step_num]
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        logger.error(f"Step script not found: {script_path}")
        return False
    
    logger.info(f"Running step {step_num}: {script_name}")
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        logger.info(f"Step {step_num} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Step {step_num} failed with exit code {e.returncode}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run SEC 13F ETL pipeline steps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all steps sequentially
  python main.py --all
  
  # Run a specific step
  python main.py --step 1
  
  # Run step 2 with custom arguments
  python main.py --step 2 -- --zip-filter 2025
        """
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run a specific step (1-4)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all steps sequentially"
    )
    parser.add_argument(
        "--args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to the step script"
    )
    
    args = parser.parse_args()
    
    # Ensure directories exist
    Config.ensure_directories()
    
    if args.all:
        # Run all steps
        logger.info("Running full ETL pipeline (all steps)")
        success = True
        for step in [1, 2, 3, 4]:
            if not run_step(step):
                logger.error(f"Pipeline failed at step {step}")
                success = False
                break
        if success:
            logger.info("Full pipeline completed successfully")
            sys.exit(0)
        else:
            sys.exit(1)
    elif args.step:
        # Run specific step
        success = run_step(args.step, args.args)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

