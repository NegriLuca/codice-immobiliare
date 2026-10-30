from selenium import webdriver # Navegador
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)

import undetected_chromedriver as uc
import random
from datetime import datetime, timedelta
import time
import re
import pandas as pd
import os
from tqdm import tqdm
from itertools import product
import pickle
import locale

# Set locale to get month names in Italian if needed

locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

def try_click_multiple_xpaths(driver, xpaths, retries=3, timeout=10):
    """
    Attempts to click on elements from a list of XPaths. If one XPath fails, it moves to the next.
    Args:
    - driver: WebDriver instance
    - xpaths: List of XPaths to attempt clicks on
    - retries: Number of retries for each XPath (default is 3)
    - timeout: Timeout in seconds to wait for the element to be clickable (default is 10 seconds)
    """
    for xpath in xpaths:
        attempt = 0
        while attempt < retries:
            try:
                # Wait until the element is clickable
                element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                element.click()  # Click the element
                print(f"Successfully clicked on element: {xpath}")
                return True  # Exit after successful click
            except Exception as e:
                attempt += 1
                print(f"Attempt {attempt}/{retries} failed for XPath {xpath}")
                time.sleep(1)  # Wait before retrying the same XPath

    # If no XPath was successful
    print("Failed to click on any of the provided XPaths.")
    return False

def generate_random_stay_dates(
    start_from_days=2,
    months_ahead=6,
    stays_per_month=6,
    seed=None
):
    """
    Generate random single-night stay date tuples (start_date, end_date).

    Args:
        start_from_days (int): Number of days from today to start generating dates.
        months_ahead (int): How many months ahead to cover.
        stays_per_month (int): Number of stays to generate per month.
        seed (int or None): Random seed for reproducibility.

    Returns:
        List of (start_date, end_date) tuples in 'YYYY-MM-DD' format.
    """
    if seed is not None:
        random.seed(seed)

    today = datetime.today() + timedelta(days=start_from_days)
    random_date_tuples = []

    for month_offset in range(months_ahead):
        current_month = (today.month + month_offset - 1) % 12 + 1
        current_year = today.year + (today.month + month_offset - 1) // 12

        # Generate dates for the month
        start_of_month = datetime(current_year, current_month, 1)
        if current_month == 12:
            start_of_next_month = datetime(current_year + 1, 1, 1)
        else:
            start_of_next_month = datetime(current_year, current_month + 1, 1)
        days_in_month = (start_of_next_month - start_of_month).days

        dates = [start_of_month + timedelta(days=i) for i in range(days_in_month) if start_of_month + timedelta(days=i) >= today]

        weekdays = [d for d in dates if d.weekday() < 4]  # Monday-Thursday
        fridays = [d for d in dates if d.weekday() == 4]
        saturdays = [d for d in dates if d.weekday() == 5]

        selected = []
        selected += random.sample(weekdays, min(2, len(weekdays)))
        selected += random.sample(fridays, min(2, len(fridays)))
        selected += random.sample(saturdays, min(2, len(saturdays)))

        month_tuples = [(d.strftime('%Y-%m-%d'), (d + timedelta(days=1)).strftime('%Y-%m-%d')) for d in selected]
        random_date_tuples.extend(month_tuples)

    return random_date_tuples

def open_calendar(driver):
    calendar_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="searchbox-dates-container"]'))
    )
    calendar_btn.click()
    time.sleep(0.5)


def select_dates(driver, start_date_str, end_date_str):

    def get_visible_months():
        # Read all <h3> month headers
        months = driver.find_elements(By.CSS_SELECTOR, 'h3.e1eebb6a1e.ee7ec6b631')
        return [m.text.lower() for m in months if m.text.strip()]

    def go_to_month(target_date):
        # Create "agosto 2025" string
        months_it = [
            "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
        ]
        target_month_str = f"{months_it[target_date.month - 1]} {target_date.year}"
        print(f"Looking for: {target_month_str}")

        for i in range(12):
            visible = get_visible_months()
            print(f"[{i}] Visible months: {visible}")
            if any(target_month_str in m for m in visible):
                return
            next_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="mese successivo"]'))
            )
            next_btn.click()
            time.sleep(0.6)
        raise Exception(f"Could not find month: {target_month_str}")

    def click_date(date_str):
        elem = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'span[data-date="{date_str}"]'))
        )
        elem.click()

    # Parse strings to datetime
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Run
    go_to_month(start_date)
    click_date(start_date_str)
    go_to_month(end_date)
    click_date(end_date_str)

def dismiss_cookie_banner(driver):
    try:
        consent_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        consent_btn.click()
        print("Cookie banner dismissed.")
        time.sleep(0.5)
    except TimeoutException:
        print("No cookie banner found.")

def retrying_find_click(driver, by, value):
    attempts = 0
    while attempts < 5:
        try:
            element = driver.find_element(by, value)
            element.click()
            break
        except StaleElementReferenceException:
            attempts += 1
            
def scroll_to_load(driver, scrolls=10, pause=1.5):
    """
    Scrolls down the page a few times to trigger initial lazy load.
    """
    print(f"📜 Scrolling {scrolls} times to trigger lazy loading...")
    for i in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        
def load_all_results(driver, max_clicks=20):
    for i in range(max_clicks):
        try:
            print(f"[{i}] Checking for 'Carica più risultati' button...")
            load_more_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "Carica più risultati")]]'))
            )
            load_more_btn.click()
            print(f"[{i}] Clicked. Waiting for more results to load...")
            time.sleep(2)  # Adjust as needed depending on connection
        except TimeoutException:
            print("No more 'Carica più risultati' button found.")
            break
        except ElementClickInterceptedException:
            print("Button found but not clickable — retrying after scrolling...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_btn)
            time.sleep(1)
            load_more_btn.click()
            
            
def get_all_prices(driver):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-testid="price-and-discounted-price"]'))
    )
    price_elems = driver.find_elements(By.CSS_SELECTOR, 'span[data-testid="price-and-discounted-price"]')
    prices = [elem.text.strip() for elem in price_elems if elem.text.strip()]
    numeric_prices = [int(re.sub(r"[^\d]", "", p)) for p in prices]

    return numeric_prices
    
    
    
def extract_listing_info(driver, get_dates):
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-testid="property-card"]'))
    )
    listings = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="property-card"]')
    
    results = []
    print(len(listings))
    for i, listing in tqdm(enumerate(listings)):
        if get_dates:
            try:
                price = listing.find_element(By.CSS_SELECTOR, 'span[data-testid="price-and-discounted-price"]').text.strip()
            except:
                price = None
        else:
            price=None
        try:
            location = listing.find_element(By.CSS_SELECTOR, 'span[data-testid="address"]').text.strip()
        except:
            location = None
        try:
            distance = listing.find_element(By.CSS_SELECTOR, 'span[data-testid="distance"]').text.strip()
        except:
            distance = None
        try:
            title = listing.find_element(By.CSS_SELECTOR, 'div[data-testid="title"]').text.strip()
        except:
            title = None
        try:
            link_element = listing.find_element(By.CSS_SELECTOR, 'a[data-testid="title-link"]')
            href = link_element.get_attribute("href")
        except:
            href = None
            
        results.append({
            "title": title,
            "link": href,
            "price": price,
            "location": location,
            "distance_from_center": distance
        })
    return results


def click_filter_by_name(driver, filter_text, timeout=5):
    """
    Clicks a filter checkbox that exactly matches the provided visible label text.
    Ignores elements in the sort-by ("Ordina per") section.
    """
    try:
        print(f"🔍 Trying to click filter: '{filter_text}'")

        # XPath that finds exact text inside filters (case-sensitive)
        xpath = (
            f'//div[@data-testid="filters-group-label-content" and normalize-space(text())="{filter_text}"]'
            f'/ancestor::label[1]'
        )

        label_elem = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

        # 🛑 Check if the label is inside the sort section (like "Ordina per")
        parent_sort_section = label_elem.find_elements(By.XPATH, './ancestor::span[contains(@class, "cac967781c")]')
        if parent_sort_section:
            print(f"⚠️ Skipping '{filter_text}' because it belongs to sort section.")
            return False

        # ✅ Scroll and click
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label_elem)
        label_elem.click()
        print(f"✅ Clicked filter: '{filter_text}'")
        return True

    except TimeoutException:
        print(f"❌ Filter '{filter_text}' not found in timeout.")
        return False
    except Exception as e:
        print(f"❌ Error while clicking filter '{filter_text}': {e}")
        return False

# Mode = "Weekend", "Week", "Month" (default )
#Se index = 1 mese corrente, 2 = M+1 etc
def flexible_data(driver, Mode, index):
    """
    Select flexible dates (Weekend, Week, or Month) and apply the date selection based on the index.
    Args:
    - driver: WebDriver instance
    - Mode: Mode of flexible dates ("Weekend", "Week", or "Month")
    - index: Index of the date to be selected
    """
    x_path1 = "/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[1]/ul/li[2]/button"
    x_path2 = "/html/body/div[3]/div[2]/div/div/form/div/div[2]/div/div/div/nav/div[1]/ul/li[2]/button"

    try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
    
    # Determine the appropriate mode to click (Weekend, Week, or Month)
    if Mode == "Weekend":
        # Click on "Weekend"
        
        x_path1 = "/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[1]/div/fieldset/div/div[1]/label/span[3]/div"           
        x_path2 = "/html/body/div[3]/div[2]/div/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[1]/div/fieldset/div/div[1]/label/span[2]"
        try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
    elif Mode == "Week":
        # Click on "1 settimana" (1 week)
        x_path = "/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[1]/div/fieldset/div/div[2]/label/span[2]"
    else:
        # Click on "1 mese" (1 month)
        x_path = "/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[1]/div/fieldset/div/div[3]/label/span[2]"
        
    # Select the date based on the given index
    x_path1 = f"/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[2]/div/fieldset/div/ul/li[{index}]/label/span/span/div"
    x_path2 = f"/html/body/div[3]/div[2]/div/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[1]/div[2]/div/fieldset/div/ul/li[{index}]/label/span/span/div"
    try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
    
    # Click on the "Select dates" button
    x_path1 = "/html/body/div[3]/div[2]/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[2]/button/span"
    x_path2 = "/html/body/div[3]/div[2]/div/div/form/div/div[2]/div/div/div/nav/div[3]/div/div[2]/button/span"
    try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
    
def get_selected_dates(driver, timeout=5):
    """
    Returns the selected dates or flexible period text from the Booking.com date picker field.
    Handles both fixed dates and flexible dates.
    """
    try:
        # Wait for the main container
        container = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.a8887b152e.c7ce171153'))
        )

        try:
            # Try to get fixed start and end dates
            start_date = container.find_element(By.CSS_SELECTOR, 'span[data-testid="date-display-field-start"]').text.strip()
            end_date = container.find_element(By.CSS_SELECTOR, 'span[data-testid="date-display-field-end"]').text.strip()
            print(f"📅 Selected fixed dates: {start_date} → {end_date}")
            return {
                "mode": "fixed",
                "start_date": start_date,
                "end_date": end_date
            }
        except:
            # If no start/end spans, fall back to generic flexible text
            flexible_text = container.text.strip()
            print(f"📅 Selected flexible period: {flexible_text}")
            return {
                "mode": "flexible",
                "text": flexible_text
            }

    except TimeoutException:
        print("⚠️ Date picker field not found.")
        return None

def close_login_popup(driver, timeout=3):
    """
    Clicks the 'Ignore login info' popup button if it appears.
    """
    try:
        close_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Ignora le informazioni sull\'accesso."]'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", close_btn)
        close_btn.click()
        print("✅ Closed login popup.")
    except TimeoutException:
        print("ℹ️ Login popup not shown (nothing to close).")


def initialize_driver():
    # Setup Chrome options
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920x1080")

    # options.add_argument("--headless")  # Optional: hide the browser

    # This automatically finds the correct version of ChromeDriver
    driver = uc.Chrome(version_main=135, options=options)

    # Add any options you need, e.g.:
    # chrome_options.add_argument("--headless")

    # Allow automatic downloads to a custom path
    driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

    # Set timeouts
    driver.implicitly_wait(2)
    driver.set_script_timeout(900)
    driver.set_page_load_timeout(900)
    return driver

def run_scraper(place, 
               get_dates,
               flexible_dates,
               start_date,
               end_date,
               mode,
               index,
               folder_output):
    driver = initialize_driver()
    driver.get("https://www.booking.com/")

    dismiss_cookie_banner(driver)
    time.sleep(2)

    #Insert Location
    location_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div[2]/div/form/div/div[1]/div/div/div[1]/div/div/input")))
    location_input.send_keys(place)

    #Click sul primo elemento
    retrying_find_click(driver,By.CLASS_NAME, 'a3332d346a')
    time.sleep(2)

    if get_dates:
        if not flexible_dates:
            select_dates(driver, start_date, end_date)
            time.sleep(2)
        else:
            flexible_data(driver, mode, index)
            time.sleep(2)

    period = get_selected_dates(driver)

    # Click the Search button
    retrying_find_click(driver,By.XPATH, '/html/body/div[3]/div[2]/div/form/div/div[4]/button')
    time.sleep(2)

    # Remove Genius banner
    try:
        x_path = "/html/body/div[18]/div/div/div/div[1]/div[1]/div/button"
        retrying_find_click(driver,By.XPATH, x_path)
    except:
        pass

    close_login_popup(driver, 5)

    # Click multiple filters
    for f in ["Appartamenti", "Case e interi appartamenti", "Fai da te: cucina/angolo cottura", "Bagno privato", "Le nostre scelte top"]:
        click_filter_by_name(driver, f)
        time.sleep(2)

    scroll_to_load(driver, scrolls=3, pause=1.5)
    load_all_results(driver, max_clicks=10)
    time.sleep(2)

    p = extract_listing_info(driver, get_dates)
    time.sleep(2)

    driver.quit()

    df = pd.DataFrame(p)
    df_filtered = df[df['location']==place]

    if get_dates:
        if period['mode']=='fixed':
            name = f"{place}_{period['start_date']}_{period['end_date']}.xlsx"
        else:
            name = f"{place}_{period['text']}.xlsx"
    else:
        name = f"{place}.xlsx"
    name = os.path.join(folder_output, name)
    with pd.ExcelWriter(name, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='All', index=False)
        df_filtered.to_excel(writer, sheet_name='Filtered', index=False)

        
def go_to_first_month(driver, wait, max_clicks=6):
    """
    Clicks the 'Mese precedente' button up to max_clicks times,
    or stops if the button becomes unclickable.
    """
    prev_btn_xpath = '//button[@aria-label="Mese precedente"]'

    for i in range(max_clicks):
        try:
            print(f"⬅️ Clicking 'Mese precedente' ({i+1}/{max_clicks})...")
            prev_button = wait.until(EC.element_to_be_clickable((By.XPATH, prev_btn_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", prev_button)
            prev_button.click()
            time.sleep(1)
        except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException):
            print("✅ Reached first visible month or button is not clickable anymore.")
            break
            
def extract_calendar_prices(driver, wait, max_rounds=3, max_clicks_back = 6):
    results = []
    go_to_first_month(driver, wait, max_clicks = max_clicks_back)

    for round_num in range(max_rounds):
        print(f"Scraping round {round_num + 1}...")

        # Wait for the calendar root to be present
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="searchbox-datepicker-calendar"]')))
            calendar_root = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="searchbox-datepicker-calendar"]')
        except TimeoutException:
            print("❌ Calendar root not found.")
            break

        # Get all month tables (each month = one table)
        month_tables = calendar_root.find_elements(By.CSS_SELECTOR, 'table[role="grid"]')

        for table in month_tables:
            day_cells = table.find_elements(By.CSS_SELECTOR, 'td[role="gridcell"]')

            for cell in day_cells:
                try:
                    span = cell.find_element(By.CSS_SELECTOR, 'span[data-date]')
                    date = span.get_attribute("data-date")

                    # Try to get the price
                    try:
                        price_span = cell.find_element(By.CSS_SELECTOR, 'span.e7362e5f34')
                        price = price_span.text.strip()
                        if price == '—':
                            price = None
                    except NoSuchElementException:
                        price = None

                    results.append((date, price))

                except NoSuchElementException:
                    continue

        # Click the "mese successivo" button twice to go to next set of months
        try:
            next_btn_xpath = '//button[@aria-label="mese successivo"]'
            for _ in range(2):
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, next_btn_xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                next_button.click()
                time.sleep(1)
        except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException):
            print("✅ No more 'mese successivo' button — calendar finished.")
            break

    return results
   
def extract_address_from_xpath(driver, xpath):
    try:
        # Find the element using XPath
        element = driver.find_element(By.XPATH, xpath)
        
        # Use 'innerText' to extract the full text, then strip leading/trailing whitespace
        full_text = element.get_property("innerText").strip()
        if not full_text:
            full_text = element.text.strip()
        # Check if there is text and split it based on newline, take the first part (address)
        if full_text:
            address = full_text.split('\n')[0]
            return address
        return None
    except NoSuchElementException:
        # Return None if the element is not found
        return None
    
def run_full_date_scraper(places, 
                          folder_output,
                          filename, 
                          max_clicks = 20,
                          indexes_range = (1,6)):
    
    current_date = datetime.now().strftime("%d-%m-%Y")

    get_dates = True
    flexible_dates = True
    modes = ["Weekend", "Week"]
    indexes = range(*indexes_range)
    
    name = os.path.join(folder_output, f"{current_date}_properties_scraped_{filename}.pkl")
    if os.path.exists(name):
        with open(name, "rb") as fp:
            all_properties = pickle.load(fp)
    else:
        all_properties = {}

    for place, mode, index in product(places, modes, indexes):
        print(f"Running scraper with mode={mode} and index={index}")

        driver = initialize_driver()
        driver.get("https://www.booking.com/")
        
        time.sleep(3)
        dismiss_cookie_banner(driver)
        time.sleep(3)

        #Insert Location
        try:
            location_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, 
            "/html/body/div[3]/div[2]/div/div/form/div/div[1]/div/div/div[1]/div/div/input")))
        except:
            location_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[3]/div[2]/div/form/div/div[1]/div/div/div[1]/div/div/input")))
        
        location_input.send_keys(place)
        time.sleep(5)
        #xpath = f"//div[@role='button' and .//div[text()={place.split(',')[0]}]]"

        #Click sul primo elemento
        first_element_xpath_1 = "/html/body/div[3]/div[2]/div/div/form/div/div[1]/div/div/div[2]/div/div/ul/li[1]/div"
        first_element_xpath_2 = "/html/body/div[3]/div[2]/div/form/div/div[1]/div/div/div[2]/div/div/ul/li[1]/div/div"
        try:
            retrying_find_click(driver,By.XPATH, first_element_xpath_2)
        except:
            retrying_find_click(driver,By.XPATH, first_element_xpath_1)
        time.sleep(2)
        
        if get_dates:
            if not flexible_dates:
                open_calendar(driver)
                select_dates(driver, start_date, end_date)
            else:
                flexible_data(driver, mode, index)
                
        time.sleep(2)
        period = get_selected_dates(driver)
        
        time.sleep(2)
        x_path1 = "/html/body/div[3]/div[2]/div/form/fieldset/div[2]/label/span[2]"
        x_path2 = "/html/body/div[3]/div[2]/div/div/form/fieldset/div[2]/label/span[2]"
        try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
        time.sleep(2)

        # Click the Search button
        x_path2 = "/html/body/div[3]/div[2]/div/div/form/div/div[4]/button"
        x_path1 = '/html/body/div[3]/div[2]/div/form/div/div[4]/button'
        try_click_multiple_xpaths(driver, [x_path1, x_path2], retries=1)
        time.sleep(2)

        # Remove Genius banner
        try:
            x_path = "/html/body/div[18]/div/div/div/div[1]/div[1]/div/button"
            retrying_find_click(driver,By.XPATH, x_path)
        except:
            pass

        close_login_popup(driver, 5)

        # Click multiple filters
        for f in ["Appartamenti", "Case e interi appartamenti", "Fai da te: cucina/angolo cottura", "Bagno privato"]:
            click_filter_by_name(driver, f)
            time.sleep(2)

        try:
            scroll_to_load(driver, scrolls=5, pause=1.5)
            load_all_results(driver, max_clicks=max_clicks)
            time.sleep(2)
        except:
            print("Couldn't load more results")
            
        property_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="title-link"]')]
        wait = WebDriverWait(driver, 10)

        # Loop over each property
        for idx, raw_url in enumerate(property_links):    
            clean_url = raw_url.split('?')[0]  # Strip tracking params
            if clean_url in all_properties:
                print(f"\n🔵 Property {idx+1}/{len(property_links)}: {clean_url} already scraped")
                
                if idx%10==0:
                    with open(name, "wb") as fp:
                        pickle.dump(all_properties, fp)
                        
                continue
            print(f"\n🔵 Opening {idx+1}/{len(property_links)}: {clean_url}")

            # Open in new tab
            driver.get(raw_url)
            time.sleep(1.5)

            try:
                time.sleep(5)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

                # Click calendar to open it
                calendar_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="searchbox-dates-container"]')))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", calendar_button)
                time.sleep(1)
                calendar_button.click()
                time.sleep(0.5)  # Optional short delay to smooth over animation

                # ✅ Wait for calendar to appear
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="searchbox-datepicker-calendar"]')))
                # Extract calendar
                calendar_data = extract_calendar_prices(driver, wait, max_rounds=3, max_clicks_back = index + 1)

                # Title
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, 'div[data-capla-component-boundary="b-property-web-property-page/PropertyHeaderName"] h2')
                    title = title_element.text.strip()                
                except Exception as e:
                    print(f"Failed to get title: {e}")
                    title = None
                # Score
                try:
                    review_score_component = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="review-score-right-component"]')
                    review_text = review_score_component.text.strip()
                    import re
                    match = re.search(r'(\d+,\d+)', review_text)
                    if match:
                        score = float(match.group(1).replace(',', '.'))
                    else:
                        score = None
                except Exception as e:
                    print(f"Failed to get score")
                    score = None
                # Position text
                try:
                    xpath = '/html/body/div[4]/div/div[6]/main/div[1]/div[1]/div[1]/div[2]/div[4]/div[3]/div/div/div/span[1]/button/div/text()'
                    position_text = extract_address_from_xpath(driver, xpath)

                except Exception as e:
                    print(f"Failed to get position text: {e}")
                    position_text = None
                # Lat/lon
                try:
                    map_link = driver.find_element(By.ID, 'map_trigger_header')
                    latlng = map_link.get_attribute('data-atlas-latlng')
                    lat, lon = latlng.split(',')
                except Exception as e:
                    print("Could not find position:", e)
                    lat, lon = None, None
                # Assemble result
                property_info = {
                    "title": title,
                    "url": clean_url,
                    "score": score,
                    "position_text": position_text,
                    "latitude": lat,
                    "longitude": lon,
                    "calendar": calendar_data
                }

                all_properties[clean_url] = property_info
                
            except Exception as e:
                print(f"Error scraping property: {e}")

            finally:
                if idx%10==0:
                    with open(name, "wb") as fp:
                        pickle.dump(all_properties, fp)

                # Close tab and go back
                time.sleep(1.5)

        driver.quit()

    with open(name, "wb") as fp:
        pickle.dump(all_properties, fp)