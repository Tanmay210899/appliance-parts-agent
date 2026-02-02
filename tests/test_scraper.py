"""
Test scraper on just ONE brand to verify everything works.
This is much faster for testing before running the full scrape.
"""

import sys
sys.path.insert(0, '/Users/tanmaysharma/Documents/Git Repos/partselect-chatbot/scrapers')

from scraper import setup_driver, get_brand_links, get_parts_from_page, scrape_part_details, save_to_csv
import time

def test_single_brand():
    """Test scraping just the first brand to verify the scraper works."""
    
    print("="*70)
    print("TEST MODE: Scraping one brand only")
    print("="*70)
    
    driver = setup_driver()
    test_data = []
    
    try:
        # Get brand links
        category_url = "https://www.partselect.com/Dishwasher-Parts.htm"
        brand_links = get_brand_links(driver, category_url)
        
        if not brand_links:
            print("[ERROR] No brand links found")
            return
        
        # Test with just the first brand
        test_brand = brand_links[0]
        print(f"\n[TEST] Testing with first brand: {test_brand}")
        
        # Get parts from this brand (just first 5 to keep it quick)
        parts = get_parts_from_page(driver, test_brand)
        print(f"[TEST] Found {len(parts)} parts, will scrape first 5")
        
        # Scrape details for first 5 parts
        for i, part_info in enumerate(parts[:5], 1):
            print(f"\n[{i}/5] Scraping: {part_info['part_name']}")
            part_data = scrape_part_details(
                driver,
                part_info['part_name'],
                part_info['product_url']
            )
            if part_data:
                test_data.append(part_data)
            time.sleep(2)
        
        # Save results
        save_to_csv(test_data, "test_scrape.csv")
        
        print("\n" + "="*70)
        print("[SUCCESS] Test complete!")
        print(f"Scraped {len(test_data)} parts -> data/test_scrape.csv")
        print("If this looks good, run the full scraper with:")
        print('  "/Users/tanmaysharma/Documents/Git Repos/partselect-chatbot/.venv/bin/python" scrapers/scraper.py')
        print("="*70)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
    finally:
        driver.quit()
        print("\n[INFO] Browser closed")

if __name__ == "__main__":
    test_single_brand()
