import time
import os
import sys
import logging
import atexit
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json
import re
import platform
from urllib.parse import urlparse
import dateutil.parser
from selenium.common.exceptions import NoSuchElementException

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
    def __init__(self, scrape_reviews=True, max_reviews=None):
        self.logger = setup_logging()
        self.driver = None
        self.scrape_reviews = scrape_reviews
        self.max_reviews = max_reviews
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
            self.driver.set_page_load_timeout(300)
            
            # Set user agent after driver initialization
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            self.logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
            raise

    def get_creator_videos(self, username, limit=10):
        """Get videos from a creator's profile and extract products from each video page."""
        try:
            # Visit creator's profile
            profile_url = f'https://www.tiktok.com/@{username}'
            self.logger.info(f"Accessing creator profile: {profile_url}")
            
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.driver.get(profile_url)
                    
                    # After loading the profile page
                    try:
                        # Wait a moment for the error to appear if it will
                        time.sleep(2)
                        refresh_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button.css-tlik2g-Button-StyledButton')
                        if refresh_buttons:
                            self.logger.info("Detected 'Something went wrong' page. Clicking Refresh button.")
                            refresh_buttons[0].click()
                            # Wait for the page to reload
                            time.sleep(5)
                    except Exception as e:
                        self.logger.error(f"Error trying to click Refresh button: {str(e)}")
                    
                    # Wait for initial page load
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Wait for video elements to be present
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e="user-post-item"]'))
                    )
                    
                    time.sleep(5)  # Additional wait for dynamic content
                    break
                    
                except Exception as e:
                    retry_count += 1
                    self.logger.error(f"Error loading profile page (attempt {retry_count}/{max_retries}): {str(e)}")
                    
                    if retry_count < max_retries:
                        # Try to recover by reinitializing the driver
                        self.logger.info("Attempting to recover by reinitializing WebDriver...")
                        try:
                            if self.driver:
                                self.driver.quit()
                        except:
                            pass
                        self.driver = None
                        self.setup_driver()
                        time.sleep(5)  # Wait before retrying
                    else:
                        raise Exception(f"Failed to load profile page after {max_retries} attempts")
            
            # Scroll to load more videos with improved error handling
            self.logger.info("Starting to scroll profile page to load more videos...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scroll_attempts = 20  # Limit maximum scroll attempts
            
            while scroll_count < max_scroll_attempts:
                try:
                    # Scroll down
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # Increased wait time for content to load
                    scroll_count += 1
                    
                    # Calculate new scroll height
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        self.logger.info(f"Finished scrolling after {scroll_count} attempts")
                        break
                    last_height = new_height
                    self.logger.info(f"Scrolled {scroll_count} times, new height: {new_height}")
                    
                except Exception as e:
                    self.logger.error(f"Error during scrolling (attempt {scroll_count + 1}): {str(e)}")
                    time.sleep(2)  # Wait before retrying scroll
                    continue
            
            # Get all video URLs
            self.logger.info("Collecting video URLs from profile page...")
            video_urls = []
            try:
                # Find all video elements
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-e2e="user-post-item"] a')
                self.logger.info(f"Found {len(video_elements)} video elements on profile page")
                
                for element in video_elements:
                    try:
                        url = element.get_attribute('href')
                        if url and '/video/' in url:
                            # Extract view count from child element
                            try:
                                views_element = element.find_element(By.CSS_SELECTOR, '[data-e2e="video-views"]')
                                views = views_element.text
                            except Exception:
                                views = None
                            video_urls.append({'url': url, 'views': views})
                            self.logger.info(f"Added video URL: {url} with views: {views}")
                    except Exception as e:
                        self.logger.error(f"Error getting URL from element: {str(e)}")
                        continue
                
                self.logger.info(f"Successfully collected {len(video_urls)} video URLs")
            except Exception as e:
                self.logger.error(f"Error getting video URLs: {str(e)}")
            
            
            # Process each video URL
            self.logger.info(f"Starting to process {min(len(video_urls), limit)} videos...")
            videos = []
            for index, video_info in enumerate(video_urls[:limit], 1):
                video_url = video_info['url']
                video_views = video_info['views']
                self.logger.info(f"Processing video {index}/{min(len(video_urls), limit)}: {video_url}")
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        # Navigate to video page
                        self.logger.info(f"Navigating to video page (attempt {retry_count + 1}/{max_retries})")
                        self.driver.get(video_url)
                        
                        # Wait for the page to be fully loaded with multiple conditions
                        self.logger.info("Waiting for page to load...")
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Additional wait for dynamic content
                        self.logger.info("Waiting for dynamic content...")
                        time.sleep(8)  # Increased wait time for dynamic content
                        
                        # Get page HTML
                        html_content = self.driver.page_source
                        
                        # Extract video metadata
                        video_id = video_url.split('/')[-1]
                        video_title = None
                        duration = None
                        like_count = None
                        comment_count = None
                        
                        try:
                            # Extract video title
                            desc_container = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="browse-video-desc"]')
                            spans = desc_container.find_elements(By.CSS_SELECTOR, 'span[data-e2e="new-desc-span"]')
                            desc_text = ' '.join([span.text for span in spans if span.text.strip()])
                            hashtags = [a.text for a in desc_container.find_elements(By.CSS_SELECTOR, 'a[data-e2e="search-common-link"]')]
                            video_title = desc_text + ' ' + ' '.join(hashtags)
                            
                            # Extract like count
                            try:
                                like_element = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="like-count"]')
                                like_count = like_element.text
                            except Exception:
                                like_count = None
                            # Extract comment count
                            try:
                                comment_element = self.driver.find_element(By.CSS_SELECTOR, '[data-e2e="comment-count"]')
                                comment_count = comment_element.text
                            except Exception:
                                comment_count = None
                            # Extract duration
                            try:
                                duration_container = self.driver.find_element(By.CSS_SELECTOR, '.css-1cuqcrm-DivSeekBarTimeContainer')
                                if duration_container:
                                    duration_text = duration_container.text
                                    if '/' in duration_text:
                                        duration = duration_text.split('/')[-1].strip()
                                    else:
                                        duration = duration_text.strip()
                            except Exception:
                                duration = None
                        except Exception as e:
                            self.logger.error(f"Error extracting video metadata: {str(e)}")
                        
                        # Try to get posting time from script data
                        posted_time = None
                        try:
                            # Look for createTime in script tag
                            script_pattern = r'<script[^>]*>.*?"createTime":\s*"?(\d+)"?.*?</script>'
                            script_match = re.search(script_pattern, html_content, re.DOTALL)
                            if script_match:
                                timestamp = int(script_match.group(1))
                                posted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                self.logger.info(f"Found posting time from timestamp: {posted_time}")
                            else:
                                # Try alternative pattern for createTime
                                alt_pattern = r'"createTime":\s*"?(\d+)"?'
                                alt_match = re.search(alt_pattern, html_content)
                                if alt_match:
                                    timestamp = int(alt_match.group(1))
                                    posted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                    self.logger.info(f"Found posting time from alternative pattern: {posted_time}")
                                else:
                                    self.logger.warning("Could not find createTime in script data")
                                    posted_time = "Unknown"
                        except Exception as e:
                            self.logger.error(f"Error getting posting time from script data: {str(e)}")
                            posted_time = "Unknown"
                        
                        # Extract products
                        self.logger.info("Extracting product information...")
                        products = self.extract_product_info(html_content)
                        
                        if products:  # Only add videos that have products
                            videos.append({
                                'id': video_id,
                                'title': video_title,
                                'web_url': video_url,
                                'duration': duration,
                                'like_count': like_count,
                                'views': video_views,
                                'comment_count': comment_count,
                                'posted_date': posted_time,
                                'products': products
                            })
                            self.logger.info(f"Found {len(products)} products in video: {video_url}")
                        else:
                            self.logger.info(f"No products found in video: {video_url}")
                        
                        # If we got here, break the retry loop
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        self.logger.error(f"Error processing video {video_url} (attempt {retry_count}/{max_retries}): {str(e)}")
                        
                        if retry_count < max_retries:
                            # Try to recover by reinitializing the driver
                            self.logger.info("Attempting to recover by reinitializing WebDriver...")
                            try:
                                if self.driver:
                                    self.driver.quit()
                            except:
                                pass
                            self.driver = None
                            self.setup_driver()
                            time.sleep(5)  # Wait before retrying
                        else:
                            self.logger.error(f"Max retries reached for video {video_url}")
                            break
                
                # Add a delay between processing videos
                time.sleep(5)
            
            self.logger.info(f"Finished processing all videos. Found {len(videos)} videos with products")
            return videos
            
        except Exception as e:
            self.logger.error(f"Error getting creator videos: {str(e)}")
            return []

    def parse_tiktok_date(self, date_text):
        """Parse TikTok date format to datetime object."""
        try:
            now = datetime.now()
            
            if 'ago' in date_text.lower():
                # Handle relative dates
                number = int(re.search(r'\d+', date_text).group())
                
                if 'min' in date_text.lower():
                    return now - timedelta(minutes=number)
                elif 'hour' in date_text.lower():
                    return now - timedelta(hours=number)
                elif 'day' in date_text.lower():
                    return now - timedelta(days=number)
                elif 'week' in date_text.lower():
                    return now - timedelta(weeks=number)
                elif 'month' in date_text.lower():
                    return now - timedelta(days=number*30)
                elif 'year' in date_text.lower():
                    return now - timedelta(days=number*365)
            else:
                # Handle absolute dates
                return dateutil.parser.parse(date_text)
                
        except Exception as e:
            self.logger.error(f"Error parsing date '{date_text}': {str(e)}")
            return datetime.now()

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
                                        
                                        # Add formatted price if available
                                        if 'price' in product_info and 'currency_format' in product_info:
                                            currency_format = product_info['currency_format']
                                            price = product_info['price']
                                            formatted_price = f"{currency_format.get('currency_symbol', '$')}{price:,.2f}"
                                            product_info['formatted_price'] = formatted_price

                                        # Scrape additional product details if seo_url is available
                                        if product_info.get('seo_url'):
                                            try:
                                                self.logger.info(f"Scraping additional details for product: {product_info['product_id']}")
                                                product_details = self.scrape_product_details(product_info['seo_url'])
                                                if product_details:
                                                    product_info.update(product_details)
                                            except Exception as e:
                                                self.logger.error(f"Error scraping additional product details: {str(e)}")
                                        
                                        products.append(product_info)
                                        
                                except Exception as e:
                                    self.logger.error(f"Error processing product {j+1} in anchor {i+1}: {str(e)}")
                                    continue
                                    
                        except Exception as e:
                            self.logger.error(f"Error processing anchor {i+1}: {str(e)}")
                            continue
                
                return products
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON data: {str(e)}")
                return []
            
        except Exception as e:
            self.logger.error(f"Error extracting product info: {str(e)}")
            return []

    def scrape_product_details(self, seo_url):
        """Scrape additional product details from the product page."""
        try:
            self.logger.info(f"Scraping product details from: {seo_url}")
            self.driver.get(seo_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Extract product details
            product_data = {
                'additional_images': [],
                'current_price': None,
                'amount_sold': None,
                'reviews': [],
                'rating': None,
                'total_reviews': None
            }
            
            # Get all product images
            try:
                image_elements = self.driver.find_elements(By.CSS_SELECTOR, '.slider-container img')
                for img in image_elements:
                    src = img.get_attribute('src')
                    if src:
                        product_data['additional_images'].append(src)
            except Exception as e:
                self.logger.error(f"Error getting product images: {str(e)}")
            
            # Get current price
            try:
                # Find the price container
                price_container = self.driver.find_element(By.CSS_SELECTOR, '.flex.flex-row.items-baseline')
                if price_container:
                    # Get all price elements
                    price_parts = []
                    
                    # Get currency symbol
                    currency_symbol = price_container.find_element(By.CSS_SELECTOR, '.font-sans.font-medium').text.strip()
                    price_parts.append(currency_symbol)
                    
                    # Get whole number
                    whole_number = price_container.find_element(By.CSS_SELECTOR, '.text-color-UIText1.Headline-Semibold').text.strip()
                    price_parts.append(whole_number)
                    
                    # Get decimal part
                    decimal_part = price_container.find_element(By.CSS_SELECTOR, '.font-sans.font-medium:last-child').text.strip()
                    price_parts.append(decimal_part)
                    
                    # Combine all parts
                    product_data['current_price'] = ''.join(price_parts)
            except NoSuchElementException:
                self.logger.warning("Price element not found")
            except Exception as e:
                self.logger.error(f"Error getting price: {str(e)}")
            
            # Get amount sold
            try:
                # Find all elements with the class
                sold_elements = self.driver.find_elements(By.CSS_SELECTOR, '.flex.flex-row.items-center span.H3-Regular.text-color-UIText2')
                for element in sold_elements:
                    text = element.text.strip()
                    # Check if the text contains any digit
                    if any(char.isdigit() for char in text):
                        product_data['amount_sold'] = text
                        break
            except NoSuchElementException:
                self.logger.warning("Amount sold element not found")
            except Exception as e:
                self.logger.error(f"Error getting amount sold: {str(e)}")
            
            # Get overall rating and total reviews
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, '.flex.flex-col.mt-40 .H1-Bold.mr-3')
                if rating_element:
                    product_data['rating'] = rating_element.text.strip()
                
                total_reviews_element = self.driver.find_element(By.CSS_SELECTOR, '.flex.flex-col.mt-40 .H2-Semibold.text-color-UIText1Display')
                if total_reviews_element:
                    product_data['total_reviews'] = total_reviews_element.text.strip()
            except NoSuchElementException:
                self.logger.warning("Rating or total reviews element not found")
            except Exception as e:
                self.logger.error(f"Error getting rating or total reviews: {str(e)}")
            
            # Get reviews if enabled
            if self.scrape_reviews:
                try:
                    # Click "View more" button if it exists and we want more reviews
                    if self.max_reviews:
                        try:
                            view_more_button = self.driver.find_element(By.CSS_SELECTOR, '.rounded-8.flex.justify-center.items-center.background-color-UIShapeNeutral4.Headline-Semibold.text-color-UIText1.px-24.py-13')
                            if view_more_button and view_more_button.text.strip() == "View more":
                                view_more_button.click()
                                time.sleep(2)  # Wait for reviews to load
                        except NoSuchElementException:
                            self.logger.info("No 'View more' button found")
                        except Exception as e:
                            self.logger.error(f"Error clicking 'View more' button: {str(e)}")
                    
                    review_containers = self.driver.find_elements(By.CSS_SELECTOR, '.flex.flex-col.mb-20')
                    reviews_processed = 0
                    
                    for review in review_containers:
                        if self.max_reviews and reviews_processed >= self.max_reviews:
                            break
                            
                        try:
                            # Get reviewer name
                            reviewer_name = review.find_element(By.CSS_SELECTOR, '.ml-12 .H3-Semibold').text.strip()
                            
                            # Get review text
                            review_text = review.find_element(By.CSS_SELECTOR, '.H4-Regular.text-color-UIText1.mt-12').text.strip()
                            
                            # Get item details
                            item_details = review.find_element(By.CSS_SELECTOR, '.mt-12.Headline-Regular.text-color-UIText3').text.strip()
                            
                            # Get review date
                            review_date = review.find_element(By.CSS_SELECTOR, '.mt-8.Headline-Regular.text-color-UIText3').text.strip()
                            
                            # Count filled stars for rating
                            filled_stars = len(review.find_elements(By.CSS_SELECTOR, '.zero-sized-font.flex.gap-4.text-color-UIText1 svg'))
                            
                            review_data = {
                                'reviewer': reviewer_name,
                                'rating': filled_stars,
                                'text': review_text,
                                'item_details': item_details,
                                'date': review_date
                            }
                            product_data['reviews'].append(review_data)
                            reviews_processed += 1
                        except Exception as e:
                            self.logger.error(f"Error processing individual review: {str(e)}")
                            continue
                except Exception as e:
                    self.logger.error(f"Error getting reviews: {str(e)}")
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error scraping product details: {str(e)}")
            return None

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

def main():
    # Get input from user
    print("\nTikTok Creator Product Scraper")
    print("==============================")
    
    # Get creator usernames
    usernames = []
    while True:
        username = input("\nEnter TikTok creator username (or press Enter to finish): ").strip()
        if not username:
            break
        usernames.append(username)
    
    if not usernames:
        print("No usernames provided. Exiting...")
        return
    
    # Get video limit
    while True:
        try:
            limit_input = input("\nEnter maximum number of videos to process (default: 10): ").strip()
            limit = int(limit_input) if limit_input else 10
            if limit > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Invalid number. Using default value of 10.")
            limit = 10
            break
    
    # Get review scraping options
    print("\nReview Scraping Options")
    print("----------------------")
    print("1. Do you want to scrape product reviews?")
    print("   This will collect reviewer names, ratings, comments, and dates.")
    print("   Note: This will make the scraping process slower.")
    
    while True:
        scrape_reviews_input = input("\nEnter your choice (y/n): ").strip().lower()
        if scrape_reviews_input in ['y', 'n']:
            scrape_reviews = scrape_reviews_input == 'y'
            break
        print("Please enter 'y' for yes or 'n' for no.")
    
    max_reviews = None
    if scrape_reviews:
        print("\n2. How many reviews do you want to scrape per product?")
        print("   - Enter a number to limit reviews")
        print("   - Press Enter to scrape all available reviews")
        print("   Note: More reviews = longer scraping time")
        
        while True:
            try:
                max_reviews_input = input("\nEnter maximum number of reviews (or press Enter for all): ").strip()
                if not max_reviews_input:
                    print("Will scrape all available reviews.")
                    break
                max_reviews = int(max_reviews_input)
                if max_reviews > 0:
                    break
                print("Please enter a positive number.")
            except ValueError:
                print("Invalid number. Please enter a valid number or press Enter for all reviews.")
    
    print("\nStarting scraper with the following settings:")
    print(f"- Number of creators: {len(usernames)}")
    print(f"- Maximum videos per creator: {limit}")
    print(f"- Review scraping: {'Enabled' if scrape_reviews else 'Disabled'}")
    if scrape_reviews:
        print(f"- Maximum reviews per product: {'All' if max_reviews is None else max_reviews}")
    
    proceed = input("\nProceed with these settings? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Scraping cancelled.")
        return
    
    scraper = TikTokScraper(scrape_reviews=scrape_reviews, max_reviews=max_reviews)
    
    try:
        all_results = []
        
        for username in usernames:
            print(f"\nProcessing creator: @{username}")
            
            # Get products from creator's profile
            products = scraper.get_creator_videos(username, limit=limit)
            print(f"Found {len(products)} products for creator: @{username}")
            
            # Process each product
            for product in products:
                print(f"\nProcessing product: {product['web_url']}")
                
                # Get page HTML
                html_content = scraper.get_page_html(product['web_url'])
                if html_content:
                    # Extract product information
                    products = scraper.extract_product_info(html_content)
                    
                    if products:
                        # Add results for this product
                        product_results = {
                            'product_url': product['web_url'],
                            'product_date': product['posted_date'],
                            'products': products
                        }
                        all_results.append(product_results)
                        
                        print(f"Found {len(products)} products for product:")
                        for product in products:
                            print(f"\nProduct ID: {product['product_id']}")
                            print(f"Title: {product['title']}")
                            print(f"Price: {product.get('formatted_price', 'N/A')}")
                            print(f"Number of images: {len(product['images'])}")
                            if scrape_reviews:
                                print(f"Number of reviews scraped: {len(product.get('reviews', []))}")
                
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