import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

USER_DATA_DIR = os.path.join(os.getcwd(), "selenium_linkedin_session")

# Common default installation paths for Brave on Windows
BRAVE_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
]

def find_brave_binary():
    for path in BRAVE_PATHS:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Could not find brave.exe automatically. Please verify your Brave install path.")

def get_driver(headless: bool = False):
    options = Options()
    
    # Point Selenium directly to Brave's executable
    brave_path = find_brave_binary()
    options.binary_location = brave_path
    
    if headless:
        options.add_argument("--headless=new")
        
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def setup_linkedin_session():
    """Launches Brave browser so you can log into LinkedIn once."""
    print("Launching Brave for LinkedIn session setup...")
    driver = get_driver(headless=False)
    driver.get("https://www.linkedin.com/login")
    
    print("\nPlease log into your LinkedIn account in the opened Brave window.")
    print("Once you see your feed, return to this terminal and press Enter...")
    input("Press Enter here when logged in: ")
    
    driver.quit()
    print("Session profile successfully saved in ./selenium_linkedin_session")

def apply_to_linkedin_job(job_url: str, cv_pdf_path: str, phone_number: str = "") -> dict:
    """Attempts to apply to a single LinkedIn Easy-Apply role using Brave."""
    result = {"url": job_url, "status": "Failed", "reason": ""}
    driver = None
    
    try:
        driver = get_driver(headless=False)
        driver.get(job_url)
        time.sleep(3)

        # Look for the Easy Apply button
        buttons = driver.find_elements(By.TAG_NAME, "button")
        easy_apply_btn = None
        for b in buttons:
            if "Easy Apply" in b.text:
                easy_apply_btn = b
                break

        if not easy_apply_btn:
            result["reason"] = "Not an Easy Apply posting (external ATS redirect)"
            return result

        easy_apply_btn.click()
        time.sleep(2)

        # Step through modal steps
        for _ in range(5):
            # Fill phone number if available
            try:
                phone_inputs = driver.find_elements(By.XPATH, "//input[contains(@id, 'phoneNumber')]")
                if phone_inputs and phone_number:
                    phone_inputs[0].clear()
                    phone_inputs[0].send_keys(phone_number)
            except Exception:
                pass

            # Upload CV if file input is present
            try:
                file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                if file_inputs and os.path.exists(cv_pdf_path):
                    abs_cv_path = os.path.abspath(cv_pdf_path)
                    file_inputs[0].send_keys(abs_cv_path)
                    time.sleep(1)
            except Exception:
                pass

            # Check for Submit application
            submits = driver.find_elements(By.XPATH, "//button[contains(., 'Submit application')]")
            if submits and submits[0].is_displayed():
                submits[0].click()
                time.sleep(3)
                result["status"] = "Submitted"
                break

            # Advance to next page
            next_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Next') or contains(., 'Review')]")
            if next_buttons and next_buttons[0].is_displayed():
                next_buttons[0].click()
                time.sleep(2)
            else:
                result["reason"] = "Encountered custom screening questionnaire or complex form"
                break

    except Exception as e:
        result["reason"] = str(e)
    finally:
        if driver:
            driver.quit()

    return result