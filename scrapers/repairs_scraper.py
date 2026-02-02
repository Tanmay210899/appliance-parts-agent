"""
PartSelect Repairs Scraper
Scrapes repair/symptom information for dishwashers and refrigerators
"""

import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


def setup_driver():
    """Creates and configures Chrome browser for scraping"""
    print("Setting up browser...")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    
    print("[OK] Browser ready")
    return driver


def safe_navigate(driver, url, max_retries=3):
    """Navigates to URL and waits for it to fully load"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            
            wait = WebDriverWait(driver, 30)
            wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            
            # Check for access denied
            if "Access Denied" in driver.title:
                print("  [WARNING] Access denied detected")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return False
            
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"  Error loading {url} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    print(f"  [FAILED] Could not load {url}")
    return False


def safe_get_text(element):
    """Safely extract text from an element"""
    try:
        return element.text.strip() if element else "N/A"
    except:
        return "N/A"


def extract_percentage(text):
    """Extract percentage number from text like '29% reported this'"""
    try:
        return text.split("%")[0].strip()
    except:
        return "0"


def get_symptoms_from_page(driver, appliance_url, appliance_type):
    """Extracts all symptoms from the main repair page"""
    print(f"\nCollecting symptoms from: {appliance_url}")
    
    if not safe_navigate(driver, appliance_url):
        return []
    
    symptoms = []
    
    try:
        # Wait for symptom list to load
        wait = WebDriverWait(driver, 30)
        symptom_list = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "symptom-list"))
        )
        print("  [OK] Found symptom list")
        
        # Get all symptom links
        symptom_links = symptom_list.find_elements(By.TAG_NAME, "a")
        print(f"  Found {len(symptom_links)} symptoms")
        
        # Extract data from each symptom
        for idx, link in enumerate(symptom_links, 1):
            try:
                # Get symptom name
                title_elem = link.find_elements(By.CLASS_NAME, "title-md")
                symptom_name = safe_get_text(title_elem[0]) if title_elem else "N/A"
                
                # Get description
                desc_elem = link.find_elements(By.TAG_NAME, "p")
                description = safe_get_text(desc_elem[0]) if desc_elem else "N/A"
                
                # Get percentage
                percent_elem = link.find_elements(By.CLASS_NAME, "symptom-list__reported-by")
                percentage = extract_percentage(safe_get_text(percent_elem[0])) if percent_elem else "0"
                
                # Get URL
                symptom_url = link.get_attribute("href")
                
                if symptom_name != "N/A" and symptom_url:
                    symptoms.append({
                        'Product': appliance_type,
                        'symptom': symptom_name,
                        'description': description,
                        'percentage': percentage,
                        'symptom_detail_url': symptom_url
                    })
                    print(f"    [{idx}/{len(symptom_links)}] Collected: {symptom_name}")
                
            except Exception as e:
                print(f"    [ERROR] Error extracting symptom {idx}: {e}")
                continue
        
    except Exception as e:
        print(f"  [ERROR] Error finding symptoms: {e}")
    
    return symptoms


def scrape_symptom_details(driver, symptom_data):
    """Visits symptom detail page and extracts repair information"""
    symptom_url = symptom_data['symptom_detail_url']
    symptom_name = symptom_data['symptom']
    
    if not safe_navigate(driver, symptom_url):
        print(f"  [FAILED] Failed to load: {symptom_name}")
        symptom_data.update({
            'parts': 'N/A',
            'difficulty': 'N/A',
            'repair_video_url': 'N/A'
        })
        return symptom_data
    
    try:
        # Wait for repair intro section
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "repair__intro")))
        
        # Get difficulty
        difficulty = "N/A"
        try:
            difficulty_elem = driver.find_elements(By.CSS_SELECTOR, "ul.list-disc li")
            if difficulty_elem:
                diff_text = safe_get_text(difficulty_elem[0])
                difficulty = diff_text.replace("Rated as", "").strip().upper()
        except:
            pass
        
        # Get parts list
        parts = []
        try:
            part_links = driver.find_elements(By.CSS_SELECTOR, "div.repair__intro a.js-scrollTrigger")
            for link in part_links:
                part_name = safe_get_text(link)
                if part_name and part_name != "N/A":
                    parts.append(part_name)
        except:
            pass
        
        parts_str = ", ".join(parts) if parts else "N/A"
        
        # Get video URL
        video_url = "N/A"
        try:
            video_elem = driver.find_elements(By.CSS_SELECTOR, "div[data-yt-init]")
            if video_elem:
                video_id = video_elem[0].get_attribute("data-yt-init")
                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
        except:
            pass
        
        symptom_data.update({
            'parts': parts_str,
            'difficulty': difficulty,
            'repair_video_url': video_url
        })
        
        print(f"  [OK] Scraped details for: {symptom_name}")
        return symptom_data
        
    except Exception as e:
        print(f"  [ERROR] Error scraping details for {symptom_name}: {e}")
        symptom_data.update({
            'parts': 'N/A',
            'difficulty': 'N/A',
            'repair_video_url': 'N/A'
        })
        return symptom_data


def scrape_appliance_repairs(appliance_url, appliance_type):
    """Main function to scrape all repairs for one appliance type"""
    print(f"\n{'='*70}")
    print(f"Starting to scrape: {appliance_type} Repairs")
    print(f"{'='*70}")
    
    driver = setup_driver()
    all_repairs_data = []
    
    try:
        # Get all symptoms from main page
        symptoms = get_symptoms_from_page(driver, appliance_url, appliance_type)
        print(f"\n[INFO] Found {len(symptoms)} symptoms to process")
        
        # Process each symptom
        for idx, symptom in enumerate(symptoms, 1):
            print(f"\n[{idx}/{len(symptoms)}] Processing: {symptom['symptom']}")
            
            repair_data = scrape_symptom_details(driver, symptom)
            all_repairs_data.append(repair_data)
            
            # Small delay between symptoms
            time.sleep(1)
        
        print(f"\n{'='*70}")
        print(f"[COMPLETE] Scraping complete for {appliance_type}")
        print(f"Total repairs collected: {len(all_repairs_data)}")
        print(f"{'='*70}")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error during scraping: {e}")
    finally:
        driver.quit()
        print("\n[INFO] Browser closed")
    
    return all_repairs_data


def save_to_csv(repairs_data, filename):
    """Saves scraped repair data to CSV file"""
    if not repairs_data:
        print("No data to save")
        return
    
    try:
        data_dir = os.path.dirname(filename)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
        
        fieldnames = [
            'Product', 'symptom', 'description', 'percentage', 
            'parts', 'symptom_detail_url', 'difficulty', 'repair_video_url'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(repairs_data)
        
        print(f"\n[SAVED] Saved {len(repairs_data)} repairs to {filename}")
    except Exception as e:
        print(f"[ERROR] Error saving to CSV: {e}")


if __name__ == "__main__":
    print("="*70)
    print("PartSelect Repairs Scraper")
    print("="*70)
    print("Scraping repair/symptom information")
   
    
    # Dishwasher repairs
    print("\n\nSTARTING: DISHWASHER REPAIRS")
    dishwasher_url = "https://www.partselect.com/Repair/Dishwasher/"
    dishwasher_repairs = scrape_appliance_repairs(dishwasher_url, "Dishwasher")
    save_to_csv(dishwasher_repairs, "data/dishwasher_repairs.csv")
    
    # Refrigerator repairs
    print("\n\nSTARTING: REFRIGERATOR REPAIRS")
    refrigerator_url = "https://www.partselect.com/Repair/Refrigerator/"
    refrigerator_repairs = scrape_appliance_repairs(refrigerator_url, "Refrigerator")
    save_to_csv(refrigerator_repairs, "data/refrigerator_repairs.csv")
    
    print(f"\n")
  
    print("ALL DONE!")

    print(f"Dishwasher repairs: {len(dishwasher_repairs):>5} -> data/dishwasher_repairs.csv")
    print(f"Refrigerator repairs: {len(refrigerator_repairs):>5} -> data/refrigerator_repairs.csv")
    print(f"Total repairs scraped: {len(dishwasher_repairs) + len(refrigerator_repairs):>5}")