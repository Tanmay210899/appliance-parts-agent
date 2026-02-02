"""
PartSelect Web Scraper
Scrapes dishwasher and refrigerator parts from PartSelect.com
"""

import time
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

csv_lock = Lock()
MAX_WORKERS = 10


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
            
            is_product_page = "/PS" in url
            
            try:
                if is_product_page:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.pd__wrap")))
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.price.pd__price")))
                else:
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "nf__links")))
                
                time.sleep(0.5)
                
                if is_product_page:
                    driver.execute_script("window.scrollTo(0, 1000);")
                    time.sleep(0.3)
                    driver.execute_script("window.scrollTo(0, 2000);")
                    time.sleep(0.5)
                
                return True
                
            except TimeoutException:
                if is_product_page:
                    if driver.find_elements(By.CSS_SELECTOR, "div.pd__wrap"):
                        return True
                else:
                    if driver.find_elements(By.CSS_SELECTOR, "div.nf__part"):
                        return True
                
                if attempt < max_retries - 1:
                    print(f"  Timeout on {url}, retrying...")
                    time.sleep(2)
                    
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


def get_brand_links(driver, category_url):
    """Extracts all brand links from main category page"""
    print(f"\nCollecting brand links from: {category_url}")
    
    if not safe_navigate(driver, category_url):
        return []
    
    brand_links = []
    
    ul_tags = driver.find_elements(By.CLASS_NAME, "nf__links")
    if ul_tags:
        li_tags = ul_tags[0].find_elements(By.TAG_NAME, "li")
        print(f"  Found {len(li_tags)} brands")
        
        for li in li_tags:
            try:
                a_tag = li.find_element(By.TAG_NAME, "a")
                link = a_tag.get_attribute("href")
                if link:
                    brand_links.append(link)
            except:
                continue
    
    return brand_links


def get_related_links(driver, category_name):
    """Extracts related category links from current page"""
    related_links = []
    
    section_titles = driver.find_elements(By.CLASS_NAME, "section-title")
    
    for title in section_titles:
        try:
            title_text = safe_get_text(title)
            
            if "Related" in title_text and f"{category_name} Parts" in title_text:
                related_ul = title.find_element(By.XPATH, "./following::ul[@class='nf__links'][1]")
                li_tags = related_ul.find_elements(By.TAG_NAME, "li")
                
                for li in li_tags:
                    try:
                        a_tag = li.find_element(By.TAG_NAME, "a")
                        link = a_tag.get_attribute("href")
                        if link:
                            related_links.append(link)
                    except:
                        continue
        except:
            continue
    
    return related_links


def get_parts_from_page(driver, page_url):
    """Extracts all part information from category/brand page"""
    if not safe_navigate(driver, page_url):
        return []
    
    parts = []
    
    part_divs = driver.find_elements(By.CSS_SELECTOR, "div.nf__part.mb-3")
    
    for part_div in part_divs:
        try:
            a_tag = part_div.find_element(By.CLASS_NAME, "nf__part__detail__title")
            span_tag = a_tag.find_element(By.TAG_NAME, "span")
            
            part_name = safe_get_text(span_tag)
            part_url = a_tag.get_attribute("href")
            
            if part_name and part_url:
                parts.append({
                    'part_name': part_name,
                    'product_url': part_url
                })
        except:
            continue
    
    return parts


def scrape_part_details(driver, part_name, product_url):
    """Visits part detail page and extracts all information"""
    if not safe_navigate(driver, product_url):
        print(f"  [FAILED] Failed to load: {part_name}")
        return None
    
    data = {
        'part_name': part_name,
        'part_id': 'N/A',
        'mpn_id': 'N/A',
        'part_price': 'N/A',
        'install_difficulty': 'N/A',
        'install_time': 'N/A',
        'product_description': 'N/A',
        'symptoms': 'N/A',
        'product_types': 'N/A',
        'replace_parts': 'N/A',
        'installation_story': 'N/A',
        'brand': 'N/A',
        'availability': 'N/A',
        'install_video_url': 'N/A',
        'product_url': product_url
    }
    
    try:
        h1_elem = driver.find_elements(By.CSS_SELECTOR, "h1[itemprop='name']")
        if h1_elem:
            h1_text = driver.execute_script("return arguments[0].innerText;", h1_elem[0]).strip()
            if h1_text:
                data['part_name'] = h1_text
        

        elem = driver.find_elements(By.CSS_SELECTOR, "span[itemprop='productID']")
        if elem:
            data['part_id'] = driver.execute_script("return arguments[0].innerText;", elem[0]).strip()
        
        elem = driver.find_elements(By.CSS_SELECTOR, "span[itemprop='mpn']")
        if elem:
            data['mpn_id'] = driver.execute_script("return arguments[0].innerText;", elem[0]).strip()
        
        elem = driver.find_elements(By.CSS_SELECTOR, "span[itemprop='brand'] span[itemprop='name']")
        if elem:
            brand_text = driver.execute_script("return arguments[0].innerText;", elem[0]).strip()
            if brand_text:
                data['brand'] = brand_text
            else:
                brand_elem = driver.find_elements(By.CSS_SELECTOR, "span[itemprop='brand']")
                if brand_elem:
                    brand_text = driver.execute_script("return arguments[0].innerText;", brand_elem[0]).strip()
                    if brand_text:
                        data['brand'] = brand_text
        
        desc_elem = driver.find_elements(By.CSS_SELECTOR, "div[itemprop='description']")
        if desc_elem:
            desc_text = driver.execute_script("return arguments[0].innerText;", desc_elem[0]).strip()
            if desc_text:
                data['product_description'] = desc_text
        else:
            meta_desc = driver.find_elements(By.CSS_SELECTOR, "meta[name='description']")
            if meta_desc:
                content = meta_desc[0].get_attribute("content")
                if content:
                    data['product_description'] = content.strip()
        
        elem = driver.find_elements(By.CSS_SELECTOR, "span[itemprop='availability']")
        if elem:
            data['availability'] = driver.execute_script("return arguments[0].innerText;", elem[0]).strip()
        
        video_div = driver.find_elements(By.CSS_SELECTOR, "div.yt-video")
        if video_div:
            video_id = video_div[0].get_attribute("data-yt-init")
            if video_id:
                data['install_video_url'] = f"https://www.youtube.com/watch?v={video_id}"
        
        elem = driver.find_elements(By.CSS_SELECTOR, "div[data-collapse-container*='targetClassToggle']")
        if elem:
            for e in elem:
                text = driver.execute_script("return arguments[0].innerText;", e).strip()
                if text and any(char.isalnum() for char in text):
                    data['replace_parts'] = text
                    break
        
        try:
            price_container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.price.pd__price"))
            )
            time.sleep(0.3)
            
            price_span = price_container.find_elements(By.CSS_SELECTOR, "span.js-partPrice")
            if price_span:
                price_text = driver.execute_script("return arguments[0].innerText;", price_span[0]).strip()
                if price_text:
                    data['part_price'] = price_text
            
            if data['part_price'] == "N/A":
                content = price_container.get_attribute("content")
                if content:
                    data['part_price'] = f"${content}"
        except:
            pass
        
        try:
            symptom_headers = driver.find_elements(By.XPATH, "//div[contains(text(), 'This part fixes the following symptoms')]")
            if symptom_headers:
                parent = symptom_headers[0].find_element(By.XPATH, "./..")
                full_text = driver.execute_script("return arguments[0].innerText;", parent)
                header_text = driver.execute_script("return arguments[0].innerText;", symptom_headers[0])
                data['symptoms'] = full_text.replace(header_text, "").strip()
        except:
            pass
        
        try:
            product_headers = driver.find_elements(By.XPATH, "//div[contains(text(), 'This part works with the following products')]")
            if product_headers:
                parent = product_headers[0].find_element(By.XPATH, "./..")
                full_text = driver.execute_script("return arguments[0].innerText;", parent)
                header_text = driver.execute_script("return arguments[0].innerText;", product_headers[0])
                data['product_types'] = full_text.replace(header_text, "").strip()
        except:
            pass
        
        try:
            difficulty_elems = driver.find_elements(By.XPATH, "//p[contains(text(), 'Easy') or contains(text(), 'Difficult') or contains(text(), 'Moderate')]")
            if difficulty_elems:
                for elem in difficulty_elems:
                    text = driver.execute_script("return arguments[0].innerText;", elem)
                    if text and len(text) < 50:
                        data['install_difficulty'] = text.strip()
                        break
        except:
            pass
        
        try:
            time_elems = driver.find_elements(By.XPATH, "//p[contains(text(), 'min') or contains(text(), 'hour')]")
            if time_elems:
                for elem in time_elems:
                    text = driver.execute_script("return arguments[0].innerText;", elem)
                    if text and len(text) < 50:
                        data['install_time'] = text.strip()
                        break
        except:
            pass
        
        try:
            repair_stories = driver.find_elements(By.CSS_SELECTOR, "div.repair-story")
            if repair_stories:
                stories = []
                for story in repair_stories[:3]:
                    story_text = driver.execute_script("return arguments[0].innerText;", story)
                    if story_text and len(story_text) > 20:
                        stories.append(story_text)
                
                if stories:
                    data['installation_story'] = " | ".join(stories)
        except:
            pass
        
        print(f"  [OK] Scraped: {part_name} ({data['part_id']})")
        return data
        
    except Exception as e:
        print(f"  [ERROR] Error scraping {part_name}: {e}")
        return data


def scrape_single_part_with_driver(part_info):
    """Scrape a single part with its own driver instance"""
    driver = setup_driver()
    try:
        part_data = scrape_part_details(
            driver,
            part_info['part_name'],
            part_info['product_url']
        )
        return part_data
    finally:
        driver.quit()


def scrape_parts_parallel(parts_list, brand_idx, total_brands):
    """Scrape multiple parts in parallel using thread pool"""
    results = []
    total_parts = len(parts_list)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_part = {executor.submit(scrape_single_part_with_driver, part): idx 
                         for idx, part in enumerate(parts_list, 1)}
        
        completed = 0
        for future in as_completed(future_to_part):
            completed += 1
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"  [{brand_idx}/{total_brands}] Progress: {completed}/{total_parts} ✓")
            except Exception as e:
                print(f"  [{brand_idx}/{total_brands}] Progress: {completed}/{total_parts} ✗ Error: {str(e)[:50]}")
    
    return results


def scrape_category(category_url, category_name):
    """Main function that orchestrates scraping process for one category"""
    print(f"\n{'='*70}")
    print(f"Starting to scrape: {category_name}")
    print(f"{'='*70}")
    
    driver = setup_driver()
    all_parts_data = []
    
    try:
        brand_links = get_brand_links(driver, category_url)
        print(f"\n[INFO] Found {len(brand_links)} brands to process")
        print(f"[INFO] Using {MAX_WORKERS} parallel workers (5x faster!)")
        
        for brand_idx, brand_url in enumerate(brand_links, 1):
            print(f"\n[{brand_idx}/{len(brand_links)}] Processing brand: {brand_url}")
            
            print("  Collecting parts from brand page...")
            brand_parts = get_parts_from_page(driver, brand_url)
            print(f"    Found {len(brand_parts)} parts on brand page")
            
            if safe_navigate(driver, brand_url):
                related_links = get_related_links(driver, category_name)
                print(f"    Found {len(related_links)} related category pages")
                
                for rel_url in related_links:
                    rel_parts = get_parts_from_page(driver, rel_url)
                    brand_parts.extend(rel_parts)
                    print(f"    Added {len(rel_parts)} parts from related category")
            
            print(f"\n  Scraping {len(brand_parts)} parts in parallel...")
            brand_results = scrape_parts_parallel(brand_parts, brand_idx, len(brand_links))
            all_parts_data.extend(brand_results)
            
            print(f"\n  [COMPLETE] Brand complete: {len(brand_results)} parts scraped")
        
        print(f"\n{'='*70}")
        print(f"[COMPLETE] Scraping complete for {category_name}")
        print(f"Total parts collected: {len(all_parts_data)}")
        print(f"{'='*70}")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Scraping interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error during scraping: {e}")
    finally:
        driver.quit()
        print("\n[INFO] Browser closed")
    
    return all_parts_data


def save_to_csv(parts_data, filename):
    """Saves scraped data to CSV file"""
    if not parts_data:
        print("No data to save")
        return
    
    try:
        data_dir = os.path.dirname(filename)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
        
        fieldnames = parts_data[0].keys()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(parts_data)
        
        print(f"\n[SAVED] Saved {len(parts_data)} parts to {filename}")
    except Exception as e:
        print(f"[ERROR] Error saving to CSV: {e}")


if __name__ == "__main__":
    print("="*70)
    print("PartSelect Web Scraper")
    print("="*70)
    print("Scraping REFRIGERATOR parts only (10 parallel browsers)")
    print("Estimated time: 1-2 hours (41 brands)")
    print("="*70)
    

    print("\n\nSTARTING: DISHWASHER PARTS")
    dishwasher_url = "https://www.partselect.com/Dishwasher-Parts.htm"
    dishwasher_data = scrape_category(dishwasher_url, "Dishwasher")
    save_to_csv(dishwasher_data, "data/dishwasher_parts.csv")
    
    print("\n\nSTARTING: REFRIGERATOR PARTS")
    refrigerator_url = "https://www.partselect.com/Refrigerator-Parts.htm"
    refrigerator_data = scrape_category(refrigerator_url, "Refrigerator")
    save_to_csv(refrigerator_data, "data/refrigerator_parts.csv")
    

    print("ALL DONE!")

