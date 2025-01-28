from flask import Flask, request
from scrape_n_store import setup_search
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def run_scraper():
    app.logger.info("Scraper started.")
    try:
        setup_search("الاتصالات وتقنية المعلومات")
        app.logger.info("Scraping completed successfully.")
        return "Scraping completed successfully.", 200
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))