# from flask import Flask, request
# from scrape_n_store import setup_search
# import os
# import logging

# app = Flask(__name__)

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# @app.route('/', methods=['GET', 'POST'])
# def run_scraper():
#     app.logger.info("Scraper started.")
#     try:
#         setup_search("الاتصالات وتقنية المعلومات")
#         app.logger.info("Scraping completed successfully.")
#         return "Scraping completed successfully.", 200
#     except Exception as e:
#         app.logger.error(f"An error occurred: {str(e)}")
#         return f"An error occurred: {str(e)}", 500

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


import streamlit as st
from scrape_n_store import setup_search
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def run_scraper():
    st.write("Scraper started.")
    try:
        setup_search("الاتصالات وتقنية المعلومات")
        st.write("Scraping completed successfully.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Streamlit UI
st.title("Web Scraping App")
st.write("This app scrapes tenders from the Etimad website.")

# Automatically run the scraper when the app is loaded
# if __name__ == '__main__':
run_scraper()
