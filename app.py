
# import streamlit as st
# from scrape_n_store import setup_search
# import os
# import logging

# logging.basicConfig(level=logging.INFO)
# # def main():
# st.title("Web Scraping App")
# try:
#     logging.info("Starting scraping process in streamlit...")
#     with st.spinner("Scraping in progress..."):
#         main_activity = "الاتصالات وتقنية المعلومات"
#         setup_search(main_activity)
#     st.success("Scraping completed successfully!")
#     logging.info("Scraping completed successfully!")
    
# except Exception as e:
#     st.error(f"An error occurred: {str(e)}")
#     logging.error(f"Error occurred: {str(e)}")

# if __name__ == "__main__":
#     main()


from flask import Flask, render_template, request, redirect, url_for
import os
import logging
from scrape_n_store import setup_search

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        logging.info("Starting scraping process in Flask...")
        main_activity = "الاتصالات وتقنية المعلومات"
        setup_search(main_activity)
        
        # Render success message in the template
        logging.info("Scraping completed successfully!")
        return render_template('index.html', message="Scraping completed successfully!", error=False)
    
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return render_template('index.html', message=f"An error occurred: {str(e)}", error=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
 