import time
import json
import pathlib
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.indeed.com"
DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)


def get_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrape_job_details(driver) -> Dict[str, Any]:
    details = {}

    # Wait for the REAL job component (title must load)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "div.jobsearch-JobComponent h2.jobsearch-JobInfoHeader-title"
        ))
    )

    container = driver.find_element(By.CSS_SELECTOR, "div.jobsearch-JobComponent")

    def safe(css):
        try:
            return container.find_element(By.CSS_SELECTOR, css).text.strip()
        except:
            return None

    details["title"] = safe("h2.jobsearch-JobInfoHeader-title")
    details["company"] = safe("[data-testid='inlineHeader-companyName']")
    details["location"] = safe("[data-testid='inlineHeader-companyLocation']")
    details["salary"] = safe("#salaryInfoAndJobType span")
    details["description"] = safe("#jobDescriptionText")

    return details


def scrape_indeed(
    driver: webdriver.Chrome, query: str, location: str, pages: int = 1
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for page in range(pages):
        start = page * 10
        search_url = f"{BASE_URL}/jobs?q={query.replace(' ', '+')}&l={location}&start={start}"

        print(f"\n[INFO] Fetching page {page + 1}: {search_url}")
        driver.get(search_url)

        # Wait until job cards exist in the LEFT pane
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.cardOutline")
            )
        )
        time.sleep(1)

        # Snapshot of how many cards we have on this page
        cards = driver.find_elements(By.CSS_SELECTOR, "div.cardOutline")
        print(f"[INFO] Found {len(cards)} job cards on this page")

        # IMPORTANT: always index by integer; the DOM can re-render after clicks
        for idx in range(len(cards)):
            print(f"[INFO] Scraping job {idx + 1}/{len(cards)}")
            try:
                # Re-fetch the cards each time to avoid stale element errors
                current_cards = driver.find_elements(By.CSS_SELECTOR, "div.cardOutline")

                # Safety check
                if idx >= len(current_cards):
                    print(f"[WARN] Card index {idx} out of range, skipping…")
                    continue

                card = current_cards[idx]

                # Scroll card into view & click it to populate right pane
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", card
                )
                time.sleep(0.3)
                card.click()

                # Wait for right pane to update
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.jobsearch-RightPane")
                    )
                )

                time.sleep(0.5)

                # Extract details from the right pane
                job = scrape_job_details(driver)

                # --- Build job URL ---
                job_url = None
                try:
                    # Find the inner <a> with data-jk inside this card
                    link_el = card.find_element(By.CSS_SELECTOR, "a[data-jk]")
                    jk = link_el.get_attribute("data-jk")
                    href = link_el.get_attribute("href")
                    if href:
                        job_url = href
                    elif jk:
                        # fallback: construct viewjob URL
                        job_url = f"{BASE_URL}/viewjob?jk={jk}"
                except Exception:
                    job_url = None

                job["url"] = job_url
                results.append(job)

            except Exception as e:
                print(f"[ERROR] Failed on job {idx + 1}: {e}")
                # keep going with the rest
                continue

    return results


def save_jsonl(records: List[Dict[str, Any]], out_path: pathlib.Path):
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    print("[INFO] Launching browser...")
    driver = get_driver()

    query = "software engineer"
    location = "United States"

    try:
        first_url = f"{BASE_URL}/jobs?q={query.replace(' ', '+')}&l={location}&start=0"
        print(f"[INFO] Opening initial page: {first_url}")
        driver.get(first_url)

        print("\n=== MANUAL ACTION REQUIRED ===")
        print("1. Solve CAPTCHA if needed.")
        print("2. Log in to Indeed.")
        print("3. Navigate to the search results page with job cards on the left.")
        input("Press ENTER once job cards are visible → ")

        print("[INFO] Starting scraping...")
        jobs = scrape_indeed(driver, query, location, pages=10)

        out_file = DATA_DIR / "indeed_sde_1127.jsonl"
        save_jsonl(jobs, out_file)
        print(f"[SUCCESS] Saved {len(jobs)} jobs to {out_file}")

    finally:
        print("[INFO] Browser left open for inspection.")
        # keep browser open so you can inspect the DOM if needed
        time.sleep(9999999)
