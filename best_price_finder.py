#!/usr/bin/env python3
# best_price_finder.py

import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

SEARCH_QUERY = "43 inch smart tv"
WAIT = 12

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

# ---------------- UTILS ----------------
def clean_price(text):
    if not text:
        return None
    text = text.replace(",", "")
    m = re.search(r"₹\s?(\d+)", text)
    return int(m.group(1)) if m else None

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    return uc.Chrome(options=options)

# ---------------- AMAZON ----------------
def fetch_amazon_prices(driver):
    log.info("Searching Amazon...")
    results = []
    driver.get("https://www.amazon.in")
    wait = WebDriverWait(driver, WAIT)

    search = wait.until(EC.element_to_be_clickable((By.ID, "twotabsearchtextbox")))
    search.send_keys(SEARCH_QUERY, Keys.ENTER)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item")))

    for item in driver.find_elements(By.CSS_SELECTOR, "div.s-result-item")[:12]:
        try:
            title = item.find_element(By.CSS_SELECTOR, "h2 span").text
            price = item.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
            price_val = clean_price("₹" + price)
            if price_val:
                results.append({"platform": "Amazon", "title": title, "price": price_val})
        except:
            continue

    print("\n📦 AMAZON (HIGH → LOW)")
    for r in sorted(results, key=lambda x: x["price"], reverse=True):
        print(f"₹{r['price']:>7} | {r['title'][:85]}")

    return results

# ---------------- FLIPKART ----------------
def fetch_flipkart_prices(driver):
    log.info("Searching Flipkart...")
    results = []
    driver.get("https://www.flipkart.com")
    wait = WebDriverWait(driver, WAIT)

    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'✕')]"))).click()
    except:
        pass

    try:
        search = wait.until(EC.element_to_be_clickable((By.NAME, "q")))
        search.send_keys(SEARCH_QUERY, Keys.ENTER)
    except TimeoutException:
        log.warning("Flipkart blocked search")
        return results

    selectors = ["div._2kHMtA", "div._1AtVbE"]
    cards = []

    for sel in selectors:
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel)))
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break
        except:
            continue

    for c in cards[:10]:
        try:
            title = c.find_element(By.CSS_SELECTOR, "div._4rR01T").text
            price = c.find_element(By.CSS_SELECTOR, "div._30jeq3").text
            price_val = clean_price(price)
            if price_val:
                results.append({"platform": "Flipkart", "title": title, "price": price_val})
        except:
            continue

    return results

# ---------------- RELIANCE DIGITAL ----------------
def fetch_reliance_prices(driver):
    log.info("Searching Reliance Digital...")
    results = []
    driver.get("https://www.reliancedigital.in/search?q=43%20inch%20tv")
    wait = WebDriverWait(driver, WAIT)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.grid")))
    except TimeoutException:
        log.warning("Reliance results not loaded")
        return results

    for item in driver.find_elements(By.CSS_SELECTOR, "li.grid")[:10]:
        try:
            title = item.find_element(By.CSS_SELECTOR, "p.sp__name").text
            price = item.find_element(By.CSS_SELECTOR, "span.sc-bdnylx").text
            price_val = clean_price(price)
            if price_val:
                results.append({"platform": "Reliance", "title": title, "price": price_val})
        except:
            continue

    return results

# ---------------- CROMA ----------------
def fetch_croma_prices(driver):
    log.info("Searching Croma...")
    results = []
    driver.get("https://www.croma.com/search/?text=43%20inch%20tv")
    wait = WebDriverWait(driver, WAIT)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-item")))
    except TimeoutException:
        log.warning("Croma results not loaded")
        return results

    for item in driver.find_elements(By.CSS_SELECTOR, "div.product-item")[:10]:
        try:
            title = item.find_element(By.CSS_SELECTOR, "h3").text
            price = item.find_element(By.CSS_SELECTOR, "span.amount").text
            price_val = clean_price(price)
            if price_val:
                results.append({"platform": "Croma", "title": title, "price": price_val})
        except:
            continue

    return results

# ---------------- MAIN ----------------
def main():
    driver = setup_driver()
    try:
        all_results = []
        all_results += fetch_amazon_prices(driver)
        all_results += fetch_flipkart_prices(driver)
        all_results += fetch_reliance_prices(driver)
        all_results += fetch_croma_prices(driver)

        if not all_results:
            print("❌ No prices found")
            return

        print("\n🏆 BEST PRICE OVERALL\n")
        best = min(all_results, key=lambda x: x["price"])
        print(f"{best['platform']} – ₹{best['price']}")
        print(best["title"])

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
