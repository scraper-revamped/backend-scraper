"""Local, NON-headless debug runner for the scraper.

Opens a real visible Chrome (via undetected-chromedriver) so you can watch the
whole flow - useful for confirming whether the activity dropdown populates on
your machine (residential IP) vs on Cloud Run (datacenter IP).

Usage (PowerShell, from the backend-scraper folder):
    $env:INITIAL_WAIT = "15"      # shorten the 180s startup wait for debugging
    python run_local.py

Notes:
- Leave HEADLESS unset so the browser is visible.
- The final step uploads to Google Cloud Storage and will fail locally without
  credentials - that's expected and happens AFTER the scraping/dropdown part you
  care about. Set SKIP_UPLOAD=1 to stop before the upload.
"""
import logging
from scrape_n_store_tst import setup_search

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    setup_search("الاتصالات وتقنية المعلومات")
