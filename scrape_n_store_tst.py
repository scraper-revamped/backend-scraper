from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import os
from xpath import *
#from utils_consts import *
import time
from save_to_bucket import save_to_storage, prune_debug_snapshots
from alerting import send_failure_alert
import logging
# from bs4 import BeautifulSoup
import requests
import bs4
import tempfile
from pathlib import Path
import shutil


logging.basicConfig(level=logging.INFO)

# Keep the UA aligned with a current Chrome major - a stale UA (the code once
# pinned Chrome/91) mismatches the Client Hints Chrome actually sends and reads
# as a bot signal. Bump this when Chrome jumps a major version.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")


def build_driver():
    """Build a headless Chrome WebDriver.

    Selenium Manager auto-provisions a matching ChromeDriver for the installed
    Chrome, so no driver binary is bundled. Runs headless by default; set the
    env var HEADLESS=0 to launch a VISIBLE browser for local debugging.
    """
    options = webdriver.ChromeOptions()
    if os.getenv("HEADLESS") != "0":
        options.add_argument("--headless=new")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=1")
    # Light automation-fingerprint reduction (harmless if the WAF isn't blocking).
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.page_load_strategy = 'none'
    return webdriver.Chrome(options=options)

# --- Robust selectors -------------------------------------------------------
# Results and pagination are injected into #cardsresult by the site's front-end
# bundle (bundle.js + vue-app/pagination.js). The pagination <ul> is rendered by
# a Vue template ONLY when there is more than one page (v-if="totalPages > 1"),
# with class "pagination". Selecting by class/id instead of positional div[N]
# indices makes the scraper resilient to front-end layout/version changes.
RESULTS_CONTAINER_ID = "cardsresult"
PAGINATION_UL_CSS = "#cardsresult ul.pagination"
TENDER_ROW_LABELS = ("الرقم المرجعي", "تاريخ النشر")
NO_RESULTS_MARKERS = ("لا توجد بيانات", "لا توجد نتائج")
DEBUG_BUCKET = "scraping_revamped_4"


class NoTendersError(RuntimeError):
    """Raised when a scrape run completes but extracts zero tenders, so callers
    (and monitoring) can distinguish an empty run from a real success."""


def wait_for_results(driver, timeout=120):
    """Block until the AJAX-loaded tender cards are actually present in
    #cardsresult, instead of relying on a fixed sleep. Returns True if tender
    rows rendered, False if the site explicitly reported no results or timed out."""
    logging.info("waiting for results to render (up to %ss)...", timeout)
    end = time.time() + timeout
    while time.time() < end:
        try:
            text = driver.find_element(By.ID, RESULTS_CONTAINER_ID).text
            if all(lbl in text for lbl in TENDER_ROW_LABELS):
                logging.info("results rendered successfully")
                return True
            if any(marker in text for marker in NO_RESULTS_MARKERS):
                logging.warning("site reported no results (placeholder shown)")
                return False
        except Exception as e:
            logging.info("still waiting for results (%s)", e.__class__.__name__)
        time.sleep(3)
    logging.error("timed out after %ss waiting for results to render", timeout)
    return False


def save_debug_snapshot(driver, reason):
    """Best-effort dump of the current page HTML + screenshot to GCS so a future
    empty/failed run can be diagnosed from the actual rendered DOM. Never raises."""
    try:
        from google.cloud import storage
        ts = time.strftime("%Y-%m-%dT%H-%M-%S")
        prefix = f"debug/{ts}_{reason}"
        bucket = storage.Client().bucket(DEBUG_BUCKET)
        bucket.blob(prefix + ".html").upload_from_string(
            driver.page_source, content_type="text/html; charset=utf-8")
        bucket.blob(prefix + ".png").upload_from_string(
            driver.get_screenshot_as_png(), content_type="image/png")
        logging.info("saved debug snapshot to gs://%s/%s.[html|png]", DEBUG_BUCKET, prefix)
        # Trim old snapshots so the debug/ folder doesn't grow forever.
        prune_debug_snapshots(DEBUG_BUCKET)
    except Exception as e:
        logging.error("failed to save debug snapshot: %s", e)


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
    #removing dupes - dedupe on reference_number (unique per tender). Using 'link'
    # would wrongly collapse all link-less tenders (e.g. شراء مباشر) into one,
    # since they now share an empty link.
    df.drop_duplicates(subset='reference_number', keep='first', inplace=True)
    # Create a new column combining "subject" and "purpose"
    df["subject_purpose"] = df["subject"] + " " + df["purpose"]


    # Save to GCS bucket (skippable for local debugging without GCP credentials)
    if os.getenv("SKIP_UPLOAD") == "1":
        logging.info("SKIP_UPLOAD=1 set; skipping GCS upload. Parsed %d rows.", len(df))
        return df
    save_to_storage(df, "الاتصالات_وتقنية_المعلومات", "default")
    return df


def extract_purpose_from_url(term_tenders):
    for tender in term_tenders:
        link = tender[-1]
        if not link:
            # Link-less tender (e.g. شراء مباشر) - no detail page to fetch.
            tender.append("الغرض من المنافسة غير متوفر")
            continue
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
    parent_tender_divs = driver.find_element(By.ID, RESULTS_CONTAINER_ID) #entire tenders
    child_tender_divs = parent_tender_divs.find_elements(By.CLASS_NAME, "row") #each tender one by one

    filtered_child_divs = []
    for div in child_tender_divs:
        text = div.text
        # A single tender card contains the reference-number label exactly ONCE.
        # find_elements(CLASS_NAME,"row") also matches an outer WRAPPER .row that
        # holds every card - its text contains the labels many times and would
        # become one giant row (e.g. 80 columns -> "Length mismatch"). Requiring
        # exactly one reference number keeps only individual tender cards.
        if text.count('الرقم المرجعي') == 1 and 'تاريخ النشر' in text:
            filtered_child_divs.append(div)

    for div in filtered_child_divs:
        el = div.text.split('\n')
        # Grab THIS row's detail link with a relative './/a' (scoped to the row).
        # Some tenders (e.g. شراء مباشر / direct purchase) have no "التفاصيل" link,
        # so fall back to "". The old code used a document-wide '//a' list indexed
        # by row position, which threw "list index out of range" as soon as a row
        # had no link (more rows than links).
        row_links = div.find_elements(By.XPATH, ".//a[contains(text(), 'التفاصيل')]")
        el.append(row_links[0].get_property("href") if row_links else "")
        term_tenders.append(el)
        if 'تاريخ ووقت فتح العروض' not in div.text:
            el.insert(-3, "N/A")
        
def start_parsing(term_tenders, driver, max_retries=3):
    logging.info("started parsing")
    current_page = 1
    try:
        pages_elements = driver.find_element(By.CSS_SELECTOR, PAGINATION_UL_CSS)
    except NoSuchElementException:
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
                    pages_elements = driver.find_element(By.CSS_SELECTOR, PAGINATION_UL_CSS)
                    buttons = pages_elements.find_elements(By.TAG_NAME, 'a')
                    for button in buttons:
                        if button.text.isdigit() and int(button.text) == current_page:
                            print(f"Trying to click page {current_page}, attempt {retries + 1}")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(2)
                            button.click()
                            time.sleep(5)  # wait for page to load

                            # confirm page changed (you can customize this logic)
                            new_pages_element = driver.find_element(By.CSS_SELECTOR, PAGINATION_UL_CSS)
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

        # Refresh pagination. If the <ul> is momentarily gone (single page left,
        # or a Vue re-render), stop paging gracefully and keep what we collected
        # instead of crashing the whole run and losing every scraped tender.
        try:
            pages_elements = driver.find_element(By.CSS_SELECTOR, PAGINATION_UL_CSS)
            pages = [int(el) for el in pages_elements.text.split('\n') if el.isdigit()]
            pages = set(pages) - pages_passed
        except NoSuchElementException:
            print("Pagination no longer present; finishing after current page.")
            break

        current_page += 1

    if term_tenders:
        extract_purpose_from_url(term_tenders)
        post_process_results(term_tenders)
    else:
        print("No tenders found for the main activity2.")

def setup_search(main_activityy):
    logging.info("Starting the scraper...")
    driver = build_driver()
    # Viewport is set via the --window-size flag (headless has no window manager
    # to maximize).
    try:
        logging.info("Driver initialized, navigating to website...")
        website_url = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1"
        driver.get(website_url)
        logging.info("got etimad website successfully!!!")
        # Initial settle/lookup-load wait. Long in prod; override for local
        # debugging with INITIAL_WAIT (e.g. INITIAL_WAIT=15).
        initial_wait = int(os.getenv("INITIAL_WAIT", "180"))
        logging.info("waiting %ss for page/lookups to settle...", initial_wait)
        time.sleep(initial_wait)
        # expand search
        logging.info("pressing search button")
        search_button = driver.find_element(By.XPATH, "//*[@id='searchBtnColaps']")
        # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
        search_button.click()
        logging.info("search button OK!!")

        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(10)
        logging.info("pressing حالة المنافسة")
        status_button = driver.find_element(By.XPATH, "//*[@id='basicInfo']/div/div[2]/div/div/button")  
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_button)                      
        status_button.click()
        logging.info("حالة المنافسة OK!!")


        driver.execute_script("window.scrollBy(0, 150);")#was 100
        time.sleep(10)
        logging.info("pressing المنافسات النشطة")
        span_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[2]/div/div/div/ul/li[2]/a')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", span_element)                                                                 
        span_element.click()
        logging.info("OK المنافسات النشطة!!")

        # time.sleep(4)
        # status_button = driver.find_element(By.XPATH, "//*[@id='basicInfo']/div/div[2]/div/div/button")                        
        # status_button.click()

        driver.execute_script("window.scrollBy(0, 150);")#was 175
        time.sleep(10)
        logging.info("pressing النشاط الاساسي")
        main_activity = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/button')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", main_activity)
        main_activity.click()
        logging.info("OK !! النشاط الاساسي")

        # The activity dropdown is filled by an AJAX lookup (GetMainActivitiesAsync)
        # that the WAF has been rejecting - when it fails the list is empty, the
        # selection silently no-ops, and the search returns "no data". Wait for
        # real options to appear; if they never load, fail loudly with a snapshot
        # instead of running a filterless search.
        def _activities_loaded(d):
            opts = d.find_elements(By.CSS_SELECTOR, "#activitiesList option")
            return any((o.get_attribute("value") or "").strip() not in ("", "0") for o in opts)
        try:
            WebDriverWait(driver, 60).until(_activities_loaded)
            logging.info("activity lookup populated OK")
        except TimeoutException:
            logging.error("activity dropdown never populated - lookup likely blocked by WAF")
            save_debug_snapshot(driver, "activity_lookup_empty")
            raise NoTendersError(
                "Main-activity dropdown never populated (GetMainActivitiesAsync "
                "likely rejected by the WAF); cannot apply the IT filter.")

        logging.info("Inputting الاتصالات و تقنية المعلومات")
        input_element = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/div/div/input')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_element) 
        input_element.clear()
        input_element.send_keys(str(main_activityy))
        

        option_xpath = f"//li[contains(., '{main_activityy}')]"
        selected_option_element = driver.find_element(By.XPATH, option_xpath)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_option_element)
        selected_option_element.click()
        logging.info("OK!! الاتصالات و تقنية المعلومات")

        # time.sleep(4)
        # main_activity = driver.find_element(By.XPATH, '//*[@id="basicInfo"]/div/div[4]/div/div/button')
        # main_activity.click()

        driver.execute_script("window.scrollBy(0, 50);")
        logging.info("pressing البحث")
        final_search_button = driver.find_element(By.XPATH, '//*[@id="searchBtn"]') 
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", final_search_button)
        time.sleep(3)
        # final_search_button.click()
        driver.execute_script("arguments[0].click();", final_search_button)
        logging.info("OK!! البحث")

        # Wait for the AJAX-rendered result cards instead of a fixed sleep. If they
        # never render, capture a snapshot and fail loudly rather than silently
        # "succeeding" with an empty result (which is what caused the empty emails).
        if not wait_for_results(driver, timeout=120):
            save_debug_snapshot(driver, "no_results_after_search")
            raise NoTendersError(
                "Results did not render after search - possible site/front-end "
                "change, slow load, or WAF block. See debug snapshot in GCS.")

        term_tenders = []
        start_parsing(term_tenders, driver)

        if not term_tenders:
            save_debug_snapshot(driver, "zero_tenders_parsed")
            raise NoTendersError(
                "Search results rendered but zero tenders were parsed - the card "
                "layout/labels may have changed. See debug snapshot in GCS.")

    except Exception as e:
        logging.error(f"An error occurred in scrape_store: {str(e)}")
        # Always capture the live DOM for ANY failure so it can be diagnosed from
        # the actual page instead of guessing from the stack trace.
        save_debug_snapshot(driver, "run_exception")
        # Alert immediately on any failure/empty run so subscribers never get
        # empty emails without us noticing. Best-effort; never masks the error.
        png = None
        try:
            png = driver.get_screenshot_as_png()
        except Exception:
            pass
        send_failure_alert(
            subject=f"[Tender Scraper] Run FAILED for {main_activityy}",
            body=(
                "The tender scraper failed or returned no tenders.\n\n"
                f"Activity: {main_activityy}\n"
                f"Error: {e}\n\n"
                f"Debug snapshot (if captured): gs://{DEBUG_BUCKET}/debug/\n"
            ),
            png_bytes=png,
        )
        raise  # propagate so app.py reports failure instead of a false success
    finally:
        # Guaranteed cleanup
        driver.quit()
        # if user_data_dir and os.path.exists(user_data_dir):
        #     shutil.rmtree(user_data_dir)

# if __name__ == "__main__":
#     setup_search("الاتصالات وتقنية المعلومات")