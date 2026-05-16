"""Quick smoke test for the Punjab mandi scraper."""
import sys
import os
from pathlib import Path

# Make sure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scrapers.punjab_mandi import scrape_punjab_mandi

prices = scrape_punjab_mandi()

print(f"\nTotal entries returned: {len(prices)}\n")
print(f"{'City':<16} {'Crop':<38} {'Today':>10}  {'Yesterday':>10}  {'Change':>8}  Unit")
print("-" * 95)
for p in prices:
    print(
        f"{p['city']:<16} {p['crop']:<38} "
        f"{p['price_today']:>10}  {p['price_yesterday']:>10}  "
        f"{p.get('change',''):>8}  {p['unit']}"
    )
