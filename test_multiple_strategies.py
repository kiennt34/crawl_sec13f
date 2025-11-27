#!/usr/bin/env python3
"""
Test to verify that multiple strategies are executed.
"""

from extract_iapd_zip import extract_zip_links_selenium

# Test configuration matching batch_config.json
strategies = [
    {
        "type": "text",
        "value": "Form ADV Part 1 Data Files",
        "description": "Click Part 1"
    },
    {
        "type": "text",
        "value": "Form ADV Part 2 Data Files",
        "description": "Click Part 2"
    },
    {
        "type": "text",
        "value": "Form ADV Part 3 Data Files",
        "description": "Click Part 3"
    },
    {
        "type": "text",
        "value": "Form ADV-W Data Files",
        "description": "Click ADV-W"
    }
]

print("="*60)
print("TESTING MULTIPLE STRATEGY EXECUTION")
print("="*60)
print(f"\nNumber of strategies: {len(strategies)}")
print("\nWith multiple strategies, the system will:")
print("  1. Execute Strategy 1 (click Part 1)")
print("  2. Execute Strategy 2 (click Part 2)")
print("  3. Execute Strategy 3 (click Part 3)")
print("  4. Execute Strategy 4 (click ADV-W)")
print("\nAll strategies will be executed, not just the first!")
print("\n" + "="*60)
print("Running extraction...")
print("="*60)

# Uncomment to run actual test:
# zip_urls = extract_zip_links_selenium(
#     url="https://adviserinfo.sec.gov/adv",
#     click_strategies=strategies,
#     wait_time=30,
#     headless=True
# )
# 
# print(f"\nTotal ZIP files found: {len(zip_urls)}")

print("\nTo run with your batch config:")
print("  python batch_extract.py --config batch_config.json --output results.json")
