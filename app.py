
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


from flask import Flask, render_template, request
import os
import logging
from scrape_n_store2 import setup_search

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET'])
def index():
    try:
        logging.info("Starting scraping process in Flask...")

        # Automatically start scraping when the user visits the page
        main_activity = "الاتصالات وتقنية المعلومات"
        setup_search(main_activity)

        # Logging and render the success message on the page
        logging.info("Scraping completed successfully!")
        return render_template('index.html', message="Scraping completed successfully!", error=False)
    
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return render_template('index.html', message=f"An error occurred: {str(e)}", error=True)

if __name__ == '__main__':
    # Set the host to 0.0.0.0 and port to 8080
    app.run(host='0.0.0.0', port=8080, debug=True)
