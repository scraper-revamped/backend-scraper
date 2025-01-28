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

logging.basicConfig(level=logging.INFO)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=1")

def post_process_results(term_tenders):
    logging.info("got etimad website successfully!!!")
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
        "competition_documents_cost", "link"
    ]
    df = df.drop(columns=["details", "useless_text"])


    df['publish_date'] = df['publish_date'].str.replace('تاريخ النشر :', '')
    df["publish_date"] = pd.to_datetime(df["publish_date"])
    df['main_activity'] = df['main_activity'].str.replace('النشاط الأساسي', '')
    df['reference_number'] = df['reference_number'].str.replace('الرقم المرجعي', '')
    df['questions_deadline'] = df['questions_deadline'].str.replace('اخر موعد لإستلام الاستفسارات', '')
    df['proposal_deadline'] = df['proposal_deadline'].str.replace('آخر موعد لتقديم العروض', '')
    df['proposal_start_date'] = df['proposal_start_date'].str.replace('تاريخ ووقت فتح العروض', '')

    # Save to GCS bucket
    save_to_storage(df, "الاتصالات_وتقنية_المعلومات", "default")
    return df

def get_tenders_from_page(term_tenders, driver):
    logging.info("get tenders from page")
    parent_tender_divs = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[1]')
    child_tender_divs = parent_tender_divs.find_elements(By.CLASS_NAME, "row")
    links = parent_tender_divs.find_elements(By.XPATH, "//a[contains(text(), 'التفاصيل')]")
    links_arr = [el.get_property("href") for el in links]
    
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
        
def start_parsing(term_tenders, driver):
    logging.info("started parsing")
    current_page = 1
    try:
        pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[2]/div/nav/ul')
    except Exception as e:
        print("No pagination found, either no tenders or a single page for the main activity.")
        get_tenders_from_page(term_tenders, driver)  
        if term_tenders:  
            post_process_results(term_tenders)
        else:
            print("No tenders found for the main activity.")
        return

    pages = [int(el) for el in pages_elements.text.split('\n') if el.isdigit()]
    pages_passed = {0}
    print("Parsing results for the main activity.")

    while len(pages) > 0:
        print("Current page: ", current_page)
        pages_passed.add(current_page)
        print('--')
        print("Pages detected", pages)
        
        if current_page in pages:
            pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[2]/div/nav/ul')
            buttons = pages_elements.find_elements(By.TAG_NAME, 'a')
            
            for button in buttons:
                if int(button.text) == current_page:
                    print(button.text)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(4)
                    button.click()
                    print(current_page, " clicked")
                    time.sleep(4)
                    pages_elements = driver.find_element(By.XPATH, '//*[@id="cardsresult"]/div[2]/div/nav/ul')
                    pages = [int(el) for el in pages_elements.text.split('\n') if el.isdigit()]
        
        get_tenders_from_page(term_tenders, driver)
        pages = set(pages) - pages_passed
        print("pages: ", pages)
        current_page += 1

    if term_tenders:  
        post_process_results(term_tenders)
    else:
        print("No tenders found for the main activity.")

    return
def setup_search(main_activityy):
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    try:
        print("getting etimad website..")
        website_url = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1"
        driver.get(website_url)
        print("got etimad website successfully!!!")
        logging.info("got etimad website successfully!!!")

        
        # expand search
        search_button = driver.find_element(By.XPATH, "//*[@id='searchBtnColaps']")
        search_button.click()

        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(4)
        status_button = driver.find_element(By.XPATH, "//*[@id='basicInfo']/div/div[2]/div/div/button")                        
        status_button.click()

        driver.execute_script("window.scrollBy(0, 50);")
        time.sleep(4)
        span_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[2]/div/div/div/ul/li[2]/a')                                                                 
        span_element.click()

        driver.execute_script("window.scrollBy(0, 175);")
        time.sleep(4)
        main_activity = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/button')
        main_activity.click()

        input_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/div/div/input')
        input_element.clear()
        input_element.send_keys(str(main_activityy))

        option_xpath = f"//li[contains(., '{main_activityy}')]"
        selected_option_element = driver.find_element(By.XPATH, option_xpath)
        selected_option_element.click()

        driver.execute_script("window.scrollBy(0, 50);")
        final_search_button = driver.find_element(By.XPATH, '//*[@id="searchBtn"]') 
        final_search_button.click()
        time.sleep(4)

        term_tenders = []
        start_parsing(term_tenders, driver)
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

# if __name__ == "__main__":
#     setup_search("الاتصالات وتقنية المعلومات")