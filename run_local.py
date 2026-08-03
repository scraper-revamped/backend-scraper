"""Local debug runner for the scraper.

Runs the full scrape flow locally so you can watch it - useful for confirming
the activity dropdown populates and tenders are parsed.

Usage (PowerShell, from the backend-scraper folder):
    $env:HEADLESS = "0"           # launch a VISIBLE browser (default is headless)
    $env:INITIAL_WAIT = "15"      # shorten the 180s startup wait for debugging
    $env:SKIP_UPLOAD = "1"        # stop before the GCS upload (no creds needed)
    python run_local.py
"""
import logging
from scrape_n_store_tst import setup_search

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    setup_search("الاتصالات وتقنية المعلومات")
