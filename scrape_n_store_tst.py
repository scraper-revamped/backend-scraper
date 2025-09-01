from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from xpath import *
#from utils_consts import *
import time
from save_to_bucket import save_to_storage
import logging
# from bs4 import BeautifulSoup
import requests
import bs4
import tempfile
from pathlib import Path
import shutil


logging.basicConfig(level=logging.INFO)
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=1")
# chrome_options.add_argument("--disable-blink-features=AutomationControlled")  
chrome_options.page_load_strategy = 'none'


def post_process_results(term_tenders):
    logging.info("post processing results")
    if not term_tenders:
        print("No results found for the specified main activity.")
        return

    records = []
    for tender in term_tenders:
        record = {}
        for i, v in enumerate(tender):
            record[f'value_{i+1}'] = v
        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv('filtered_csv', index=False, encoding='utf-8-sig')
    df.columns = [
         "publish_date", "competition_type", "subject", "stakeholder", 
        "details", "main_activity", "time_left", "reference_number", "questions_deadline", 
        "proposal_deadline", "proposal_start_date", "useless_text", 
        "competition_documents_cost", "link","purpose"
    ]
    df = df.drop(columns=["details", "useless_text"])
    

    df['publish_date'] = df['publish_date'].str.replace('تاريخ النشر :', '')
    df["publish_date"] = pd.to_datetime(df["publish_date"])
    df['main_activity'] = df['main_activity'].str.replace('النشاط الأساسي', '')
    df['reference_number'] = df['reference_number'].str.replace('الرقم المرجعي', '')
    df['questions_deadline'] = df['questions_deadline'].str.replace('اخر موعد لإستلام الاستفسارات', '')
    df['proposal_deadline'] = df['proposal_deadline'].str.replace('آخر موعد لتقديم العروض', '')
    df['proposal_start_date'] = df['proposal_start_date'].str.replace('تاريخ ووقت فتح العروض', '')
    df["purpose"] = df["purpose"].str.replace("...عرض الأقل...", "", regex=False)
    #removing dupes
    df.drop_duplicates(subset='link', keep='first', inplace=True)   
    # Create a new column combining "subject" and "purpose"
    df["subject_purpose"] = df["subject"] + " " + df["purpose"]


    # Save to GCS bucket
    save_to_storage(df, "الاتصالات_وتقنية_المعلومات", "default")
    return df


def extract_purpose_from_url(term_tenders):
    for tender in term_tenders:
        link = tender[-1]
        try:
            # Send a GET request to fetch the page content
            response = requests.get(link)
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

            # Parse the HTML
            soup = bs4.BeautifulSoup(response.text, 'html.parser')
            # Locate the "الغرض من المنافسة" section
            purpose_section = soup.find('div', class_='col-4', string=lambda text: text and 'الغرض من المنافسة' in text)

            if purpose_section:
                # Find the corresponding information in the next column
                purpose_info = purpose_section.find_next_sibling('div', class_='col-8 etd-item-info')

                # Check if the expanded content is available
                purpose_span = purpose_info.find('span', id='purposeSpan')
                if purpose_span and purpose_span.has_attr('hidden'):
                    extracted_text = purpose_span.get_text(strip=True)
                else:
                    extracted_text = purpose_info.get_text(strip=True)
            else:
                extracted_text = "الغرض من المنافسة غير متوفر"

        except Exception as e:
            extracted_text = f"Error processing {link}: {e}"
        
        # Append the extracted text to the tender list
        tender.append(extracted_text)

    return term_tenders

def get_tenders_from_page(term_tenders, driver):
    logging.info("get tenders from page")
    parent_tender_divs = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[2]') #entire tenders 
    child_tender_divs = parent_tender_divs.find_elements(By.CLASS_NAME, "row") #each tender one by one 
    links = parent_tender_divs.find_elements(By.XPATH, "//a[contains(text(), 'التفاصيل')]") #### links for detailssss 
    links_arr = [el.get_property("href") for el in links] # links for all tafaseel 

    filtered_child_divs = []
    for div in child_tender_divs:
        if 'الرقم المرجعي' in div.text and 'تاريخ النشر' in div.text:
            filtered_child_divs.append(div)
    i = 0
    for div in filtered_child_divs:
        el = div.text.split('\n')
        el.append(links_arr[i])
        term_tenders.append(el)
        if 'تاريخ ووقت فتح العروض' not in div.text:
            el.insert(-3, "N/A")            
        i += 1
        
def start_parsing(term_tenders, driver, max_retries=3):
    logging.info("started parsing")
    current_page = 1
    try:
        pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[3]/div/nav/ul')
    except Exception:
        print("No pagination found, either no tenders or a single page for the main activity.")
        get_tenders_from_page(term_tenders, driver)
        if term_tenders:
            extract_purpose_from_url(term_tenders)
            post_process_results(term_tenders)
        else:
            print("No tenders found for the main activity1.")
        return

    pages = [int(el) for el in pages_elements.text.split('\n') if el.isdigit()]
    pages_passed = {0}
    print("Parsing results for the main activity.")

    while len(pages) > 0:
        time.sleep(3)
        print("Current page: ", current_page)
        pages_passed.add(current_page)

        if current_page in pages:
            success = False
            retries = 0
            while not success and retries < max_retries:
                try:
                    pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[3]/div/nav/ul')
                    buttons = pages_elements.find_elements(By.TAG_NAME, 'a')
                    for button in buttons:
                        if button.text.isdigit() and int(button.text) == current_page:
                            print(f"Trying to click page {current_page}, attempt {retries + 1}")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(2)
                            button.click()
                            time.sleep(5)  # wait for page to load

                            # confirm page changed (you can customize this logic)
                            new_pages_element = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[3]/div/nav/ul')
                            new_buttons = new_pages_element.find_elements(By.TAG_NAME, 'a')
                            if any(btn.text.isdigit() and int(btn.text) == current_page for btn in new_buttons):
                                success = True
                                print(f"Page {current_page} loaded successfully.")
                            break
                except Exception as e:
                    print(f"Retry {retries + 1} failed: {e}")
                retries += 1

            if not success:
                print(f"Failed to load page {current_page} after {max_retries} retries.")
                current_page += 1
                continue

        get_tenders_from_page(term_tenders, driver)

        # Refresh pagination
        pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[3]/div/nav/ul')
        pages = [int(el) for el in pages_elements.text.split('\n') if el.isdigit()]
        pages = set(pages) - pages_passed

        current_page += 1

    if term_tenders:
        extract_purpose_from_url(term_tenders)
        post_process_results(term_tenders)
    else:
        print("No tenders found for the main activity2.")

def setup_search(main_activityy):
    logging.info("Starting the scraper...")
    driver = webdriver.Chrome(options=chrome_options)
    # driver.set_page_load_timeout(300)  # Set timeout for page loading
    # driver.set_script_timeout(300) 
    driver.maximize_window()
    try:
        logging.info("Driver initialized, navigating to website...")
        website_url = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1"
        driver.get(website_url)
        logging.info("got etimad website successfully!!!")
        time.sleep(180)
        # expand search
        logging.info("pressing search button")
        search_button = driver.find_element(By.XPATH, "//*[@id='searchBtnColaps']")
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
        search_button.click()
        logging.info("search button OK!!")

        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(4)
        logging.info("pressing حالة المنافسة")
        status_button = driver.find_element(By.XPATH, "//*[@id='basicInfo']/div/div[2]/div/div/button")  
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_button)                      
        status_button.click()
        logging.info("حالة المنافسة OK!!")


        driver.execute_script("window.scrollBy(0, 50);")
        time.sleep(4)
        span_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[2]/div/div/div/ul/li[2]/a')
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", span_element)                                                                 
        span_element.click()

        # time.sleep(4)
        # status_button = driver.find_element(By.XPATH, "//*[@id='basicInfo']/div/div[2]/div/div/button")                        
        # status_button.click()

        driver.execute_script("window.scrollBy(0, 175);")
        time.sleep(4)
        main_activity = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/button')
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", main_activity) 
        main_activity.click()

        input_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/div/div/input')
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_element) 
        input_element.clear()
        input_element.send_keys(str(main_activityy))

        option_xpath = f"//li[contains(., '{main_activityy}')]"
        selected_option_element = driver.find_element(By.XPATH, option_xpath)
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_option_element)
        selected_option_element.click()

        # time.sleep(4)
        # main_activity = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/button')
        # main_activity.click()

        driver.execute_script("window.scrollBy(0, 50);")
        final_search_button = driver.find_element(By.XPATH, '//*[@id="searchBtn"]') 
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", final_search_button)
        final_search_button.click()
        time.sleep(4)

        term_tenders = []
        start_parsing(term_tenders, driver)
        
    except Exception as e:
        logging.error(f"An error occurred in scrape_store: {str(e)}")
    finally:
        # Guaranteed cleanup
        driver.quit()
        # if user_data_dir and os.path.exists(user_data_dir):
        #     shutil.rmtree(user_data_dir)

# if __name__ == "__main__":
#     setup_search("الاتصالات وتقنية المعلومات")