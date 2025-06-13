import time
import os
import sys
import logging
import atexit
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import platform
from urllib.parse import urlparse

# Configure logging
def setup_logging():
    """Set up logging configuration."""
    # Configure logging to only use console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class TikTokScraper:
    def __init__(self):
        self.logger = setup_logging()
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """Set up the Chrome WebDriver."""
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

            self.logger.info("Setting up Chrome WebDriver...")
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            options.add_argument('--lang=en-US')
            options.add_argument('--mute-audio')  # Disable audio
            
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            
            # Set user agent after driver initialization
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            self.logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
            raise

    def get_page_html(self, url):
        """Get the full HTML content of the page."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"Accessing URL: {url}")
                
                # Ensure driver is initialized
                if not self.driver:
                    self.setup_driver()
                
                # Navigate to the page
                self.driver.get(url)
                
                # Wait for the page to load
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait for any script tags to be present
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "script"))
                )
                
                # Additional wait for dynamic content
                time.sleep(15)  # Increased wait time for dynamic content
                
                # Get the full HTML content
                html_content = self.driver.page_source
                self.logger.info("Successfully retrieved page HTML")
                
                # Save HTML to file for inspection
                with open('page_content.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.logger.info("Saved HTML content to page_content.html")
                
                # Debug: Check if the script tag exists
                if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in html_content:
                    self.logger.info("Found __UNIVERSAL_DATA_FOR_REHYDRATION__ in HTML")
                else:
                    self.logger.warning("__UNIVERSAL_DATA_FOR_REHYDRATION__ not found in HTML")
                    # Save a debug file with all script tags
                    script_tags = self.driver.find_elements(By.TAG_NAME, "script")
                    with open('script_tags.txt', 'w', encoding='utf-8') as f:
                        for script in script_tags:
                            f.write(f"Script ID: {script.get_attribute('id')}\n")
                            f.write(f"Script Type: {script.get_attribute('type')}\n")
                            f.write("---\n")
                    self.logger.info("Saved script tags to script_tags.txt")
                
                return html_content
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Error getting page HTML (attempt {retry_count}/{max_retries}): {str(e)}")
                
                # Try to recover by reinitializing the driver
                try:
                    if self.driver:
                        self.driver.quit()
                except:
                    pass
                self.driver = None
                
                if retry_count < max_retries:
                    self.logger.info("Retrying with new WebDriver instance...")
                    time.sleep(5)  # Wait before retrying
                    self.setup_driver()
                else:
                    self.logger.error("Max retries reached. Giving up.")
                    return None

    def extract_product_info(self, html_content):
        """Extract product information from HTML content."""
        try:
            # First find the script tag containing __DEFAULT_SCOPE__
            script_pattern = r'<script[^>]*>.*?__DEFAULT_SCOPE__\s*=\s*({.*?});.*?</script>'
            script_match = re.search(script_pattern, html_content, re.DOTALL)
            
            if not script_match:
                # Try alternative pattern
                script_pattern = r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>({.*?})</script>'
                script_match = re.search(script_pattern, html_content, re.DOTALL)
                
                if not script_match:
                    self.logger.error("Could not find script tag with __UNIVERSAL_DATA_FOR_REHYDRATION__")
                    return []
            
            # Extract the JSON object
            scope_json = script_match.group(1)
            self.logger.info("Found __UNIVERSAL_DATA_FOR_REHYDRATION__ in script tag")
            
            # Parse the JSON data
            try:
                data = json.loads(scope_json)
                products = []
                
                # Debug the structure
                self.logger.info(f"Default scope keys: {list(data.keys())}")
                
                # Handle case where __DEFAULT_SCOPE__ might be a list
                default_scope = data.get('__DEFAULT_SCOPE__', {})
                if isinstance(default_scope, list):
                    default_scope = default_scope[0] if default_scope else {}
                
                if not default_scope:
                    self.logger.error("No __DEFAULT_SCOPE__ found in data")
                    return []
                
                # Handle webapp.video-detail which might be a list
                webapp_video_detail = default_scope.get('webapp.video-detail', {})
                if isinstance(webapp_video_detail, list):
                    webapp_video_detail = webapp_video_detail[0] if webapp_video_detail else {}
                
                # Handle itemInfo which might be a list
                item_info = webapp_video_detail.get('itemInfo', {})
                if isinstance(item_info, list):
                    item_info = item_info[0] if item_info else {}
                
                # Handle itemStruct which might be a list
                item_struct = item_info.get('itemStruct', {})
                if isinstance(item_struct, list):
                    item_struct = item_struct[0] if item_struct else {}
                
                # Get anchors and ensure it's a list
                anchors = item_struct.get('anchors', [])
                if not isinstance(anchors, list):
                    anchors = [anchors] if anchors else []
                
                self.logger.info(f"Number of anchors found: {len(anchors)}")
                
                # Process each anchor
                for i, anchor in enumerate(anchors):
                    if isinstance(anchor, dict) and "extra" in anchor:
                        try:
                            # Parse the extra field which contains a list of product information
                            extra_list = json.loads(anchor["extra"])
                            if not isinstance(extra_list, list):
                                extra_list = [extra_list]
                            
                            self.logger.info(f"Found {len(extra_list)} products in anchor {i+1}")
                            
                            # Process each product in the extra list
                            for j, product_data in enumerate(extra_list):
                                try:
                                    # Parse the product's extra field which contains the detailed product info
                                    if isinstance(product_data, dict) and "extra" in product_data:
                                        extra_data = json.loads(product_data["extra"])
                                        
                                        # Handle categories which might be a list
                                        categories = extra_data.get('categories', [])
                                        if not isinstance(categories, list):
                                            categories = [categories] if categories else []
                                        
                                        # Handle skus which might be a list
                                        skus = extra_data.get('skus', [])
                                        if not isinstance(skus, list):
                                            skus = [skus] if skus else []
                                        
                                        # Handle images which might be a list
                                        images = extra_data.get('img_url', [])
                                        if not isinstance(images, list):
                                            images = [images] if images else []
                                        
                                        # Extract product information with all available fields
                                        product_info = {
                                            'product_id': str(extra_data.get('product_id')),  # Convert to string to preserve precision
                                            'title': extra_data.get('title', '').replace('\\u0026', '&'),
                                            'elastic_title': extra_data.get('elastic_title', ''),
                                            'price': extra_data.get('price', 0),
                                            'market_price': extra_data.get('market_price', 0),
                                            'currency': extra_data.get('currency', 'USD'),
                                            'currency_format': extra_data.get('currency_format', {}),
                                            'seller_id': str(extra_data.get('seller_id')),  # Convert to string to preserve precision
                                            'source': extra_data.get('source', 'TikTok Shop'),
                                            'categories': categories,
                                            'images': images,
                                            'cover_url': extra_data.get('cover_url'),
                                            'detail_url': extra_data.get('detail_url'),
                                            'seo_url': extra_data.get('seo_url'),
                                            'skus': skus,
                                            'product_status': extra_data.get('product_status'),
                                            'platform': extra_data.get('platform'),
                                            'is_platform_product': extra_data.get('is_platform_product', False),
                                            'ad_label': extra_data.get('extra', {}).get('ad_label_name'),
                                            'ad_position': extra_data.get('extra', {}).get('ad_label_position')
                                        }
                                        
                                        # Clean up any remaining escape sequences in the title
                                        if product_info['title']:
                                            product_info['title'] = product_info['title'].encode().decode('unicode_escape')
                                        if product_info['elastic_title']:
                                            product_info['elastic_title'] = product_info['elastic_title'].encode().decode('unicode_escape')
                                        
                                        # Format the price with currency
                                        if product_info['currency_format']:
                                            currency_format = product_info['currency_format']
                                            price = product_info['price']
                                            formatted_price = f"{currency_format.get('currency_symbol', '$')}{price:,.{currency_format.get('decimal_place', 2)}f}"
                                            product_info['formatted_price'] = formatted_price
                                        
                                        products.append(product_info)
                                        self.logger.info(f"Found product: {product_info['product_id']}")
                                    
                                except json.JSONDecodeError as e:
                                    self.logger.error(f"Error parsing product extra data: {str(e)}")
                                except Exception as e:
                                    self.logger.error(f"Error processing product data: {str(e)}")
                                    self.logger.error(f"Product data: {product_data}")
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Error parsing anchor extra data: {str(e)}")
                        except Exception as e:
                            self.logger.error(f"Error processing anchor data: {str(e)}")
                            self.logger.error(f"Anchor data: {anchor}")
                
                self.logger.info(f"Found {len(products)} products")
                return products
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing scope JSON: {str(e)}")
                return []
            
        except Exception as e:
            self.logger.error(f"Error extracting product info: {str(e)}")
            return []

    def close(self):
        """Close the WebDriver."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.logger.info("Chrome WebDriver closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing Chrome WebDriver: {str(e)}")
            self.driver = None

def main():
    # List of video URLs to scrape
    video_urls = []
    
    scraper = TikTokScraper()
    
    try:
        all_results = []
        
        for video_url in video_urls:
            print(f"\nProcessing video: {video_url}")
            
            # Get page HTML
            html_content = scraper.get_page_html(video_url)
            if html_content:
                # Extract product information
                products = scraper.extract_product_info(html_content)
                
                # Add results for this video
                video_results = {
                    'video_url': video_url,
                    'products': products
                }
                all_results.append(video_results)
                
                print(f"\nFound {len(products)} products for video:")
                for product in products:
                    print(f"\nProduct ID: {product['product_id']}")
                    print(f"Title: {product['title']}")
                    print(f"Price: {product.get('formatted_price', 'N/A')}")
                    print(f"Number of images: {len(product['images'])}")
            
            # Add a small delay between requests
            time.sleep(5)
        
        # Save all results to a single JSON file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'product_info_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=4)
        
        print(f"\nAll results have been saved to {output_file}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 