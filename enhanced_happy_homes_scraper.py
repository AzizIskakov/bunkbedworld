#!/usr/bin/env python3
"""
Enhanced Happy Homes scraper for complete inventory management.
Features:
- Multiple image extraction with carousel support
- Rich product descriptions
- Sold out detection and inventory tracking
- New/removed/restored item management
"""

import json, re, sys, time, os
from urllib.request import urlopen, Request, urlretrieve
from urllib.error import HTTPError, URLError
from html import unescape
from urllib.parse import urljoin, urlparse
import hashlib

PRODUCTS_FILE = 'products.json'
INVENTORY_TRACKING_FILE = 'happy_homes_inventory.json'
IMAGES_DIR = 'images'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

class HappyHomesScrapingEngine:
    def __init__(self):
        self.base_url = 'https://www.happyhomesindustries.com'
        
        # Load existing products and inventory tracking
        self.products = self.load_products()
        self.inventory_tracking = self.load_inventory_tracking()
        
    def load_products(self):
        """Load existing products.json"""
        try:
            with open(PRODUCTS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def load_inventory_tracking(self):
        """Load inventory tracking data"""
        try:
            with open(INVENTORY_TRACKING_FILE, 'r') as f:
                data = json.load(f)
                # Convert lists back to sets
                data['current_urls'] = set(data.get('current_urls', []))
                data['previous_urls'] = set(data.get('previous_urls', []))
                return data
        except FileNotFoundError:
            return {
                'last_scan': None,
                'current_urls': set(),
                'previous_urls': set(),
                'sold_out_items': {},
                'scan_history': []
            }
    
    def save_inventory_tracking(self):
        """Save inventory tracking data"""
        # Convert sets to lists for JSON serialization
        tracking_copy = self.inventory_tracking.copy()
        tracking_copy['current_urls'] = list(tracking_copy['current_urls'])
        tracking_copy['previous_urls'] = list(tracking_copy['previous_urls'])
        
        with open(INVENTORY_TRACKING_FILE, 'w') as f:
            json.dump(tracking_copy, f, indent=2)
    
    def fetch_html(self, url, max_retries=3):
        """Fetch HTML with retries using urllib"""
        for attempt in range(max_retries):
            try:
                req = Request(url, headers={'User-Agent': USER_AGENT})
                response = urlopen(req, timeout=30)
                html = response.read().decode('utf-8', errors='replace')
                response.close()
                return html
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {url}: {e}")
                    return None
                time.sleep(2 ** attempt)
        return None
    
    def extract_product_images(self, html, product_url):
        """Extract all product images from HTML"""
        images = []
        
        # Look for main product images in various containers
        image_patterns = [
            # Main product gallery
            r'<div[^>]*class="[^"]*productGalleryImage[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"',
            # Alternative image containers
            r'<div[^>]*id="[^"]*gallery[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"',
            # Direct img tags with product-related classes
            r'<img[^>]*class="[^"]*(?:product|gallery|main)[^"]*"[^>]*src="([^"]+)"',
            # Wix-specific patterns
            r'<wix-image[^>]*>.*?<img[^>]*src="([^"]+)"',
            # General large images
            r'<img[^>]*src="([^"]+)"[^>]*(?:width="[456789]\d\d"|height="[456789]\d\d")',
        ]
        
        found_images = set()
        for pattern in image_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for img_url in matches:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(self.base_url, img_url)
                
                # Filter out obviously non-product images
                if self.is_product_image(img_url):
                    found_images.add(img_url)
        
        return list(found_images)
    
    def is_product_image(self, img_url):
        """Filter to only include actual product images"""
        # Skip icons, logos, buttons, etc.
        skip_patterns = [
            r'icon', r'logo', r'button', r'arrow', r'cart', r'search',
            r'social', r'nav', r'menu', r'banner', r'footer', r'header',
            r'thumb', r'_small', r'_mini', r'_tiny', r'facebook', r'twitter'
        ]
        
        url_lower = img_url.lower()
        for pattern in skip_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # Must be reasonable size (avoid thumbnails)
        # Look for size indicators in URL
        size_match = re.search(r'(\d+)x(\d+)', url_lower)
        if size_match:
            w, h = int(size_match.group(1)), int(size_match.group(2))
            if w < 200 or h < 200:
                return False
        
        return True
    
    def download_and_save_image(self, img_url, product_id, image_index):
        """Download image and save to images directory using urllib"""
        try:
            # Generate filename
            img_extension = '.jpg'  # Default
            if '.png' in img_url.lower():
                img_extension = '.png'
            elif '.webp' in img_url.lower():
                img_extension = '.webp'
            
            filename = f"happy-{product_id}-{image_index}{img_extension}"
            filepath = os.path.join(IMAGES_DIR, filename)
            
            # Save image
            os.makedirs(IMAGES_DIR, exist_ok=True)
            
            # Download using urllib
            req = Request(img_url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=30) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            
            return f"/images/{filename}"
            
        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")
            return None
    
    def extract_detailed_description(self, html):
        """Extract rich product details like the Future example"""
        result = {}
        
        # Find product description section
        desc_patterns = [
            r'<div[^>]*id="wsite-com-product-short-description"[^>]*>.*?<div class="paragraph">(.*?)</div>',
            r'<div[^>]*class="[^"]*product-description[^"]*"[^>]*>(.*?)</div>',
        ]
        
        content_html = ""
        for pattern in desc_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content_html = match.group(1)
                break
        
        if not content_html:
            return result
        
        # Clean HTML to text
        clean_text = re.sub(r'<br\s*/?>', '\n', content_html)
        clean_text = re.sub(r'</(?:p|li|div)>', '\n', clean_text)
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = unescape(clean_text)
        
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        
        # Extract structured fields
        extracted_data = {
            'item_name': '',
            'color': '',
            'material': '',
            'dimensions': '',
            'features': [],
            'description_lines': lines
        }
        
        # Parse labeled fields
        dimensions_section = []
        in_dimensions = False
        
        for line in lines:
            # Item Name: Value
            if re.match(r'^Item Name:\s*(.+)', line, re.IGNORECASE):
                extracted_data['item_name'] = re.match(r'^Item Name:\s*(.+)', line, re.IGNORECASE).group(1).strip()
            
            # Color: Value  
            elif re.match(r'^Color:\s*(.+)', line, re.IGNORECASE):
                extracted_data['color'] = re.match(r'^Color:\s*(.+)', line, re.IGNORECASE).group(1).strip()
            
            # Material: Value
            elif re.match(r'^Material:\s*(.+)', line, re.IGNORECASE):
                extracted_data['material'] = re.match(r'^Material:\s*(.+)', line, re.IGNORECASE).group(1).strip()
            
            # Dimensions: or lines that look like dimensions
            elif re.match(r'^Dimensions?:', line, re.IGNORECASE):
                in_dimensions = True
                # Check if value is on same line
                dim_match = re.match(r'^Dimensions?:\s*(.+)', line, re.IGNORECASE)
                if dim_match and dim_match.group(1).strip():
                    dimensions_section.append(dim_match.group(1).strip())
            
            elif in_dimensions:
                if self.looks_like_dimension(line) or re.match(r'(?:Queen|King|Twin|Full)', line, re.IGNORECASE):
                    dimensions_section.append(line)
                elif line.startswith('-') or line.startswith('•'):
                    # End of dimensions, start of features
                    in_dimensions = False
                    feature = line.lstrip('- •').strip()
                    if feature:
                        extracted_data['features'].append(feature)
                elif ':' in line and not self.looks_like_dimension(line):
                    # Probably a new section
                    in_dimensions = False
            
            # Feature bullets (lines starting with -)
            elif line.startswith('-') or line.startswith('•'):
                feature = line.lstrip('- •').strip()
                if feature:
                    extracted_data['features'].append(feature)
        
        # Set dimensions from collected lines
        if dimensions_section:
            extracted_data['dimensions'] = '\n'.join(dimensions_section)
        
        # Build comprehensive description
        description_parts = []
        
        if extracted_data['item_name']:
            description_parts.append(f"Item Name: {extracted_data['item_name']}")
        
        if extracted_data['color']:
            description_parts.append(f"Color: {extracted_data['color']}")
        
        if extracted_data['material']:
            description_parts.append(f"Material: {extracted_data['material']}")
        
        if extracted_data['dimensions']:
            description_parts.append(f"Dimensions:\n{extracted_data['dimensions']}")
        
        if extracted_data['features']:
            description_parts.append('\n' + '\n'.join(f"- {feature}" for feature in extracted_data['features']))
        
        result['description'] = '\n\n'.join(description_parts) if description_parts else ''
        result['color'] = extracted_data['color']
        result['material'] = extracted_data['material'] 
        result['dimensions'] = extracted_data['dimensions']
        
        return result
    
    def looks_like_dimension(self, line):
        """Check if line contains dimension information"""
        dim_patterns = [
            r'\d+(?:\.\d+)?"?\s*[LWHDxX×]',  # 72"L, 34W, etc.
            r'\d+(?:\.\d+)?\s*x\s*\d+',      # 72 x 34
            r'(?:Queen|King|Twin|Full).*\d+', # Queen 100"L x 70"W
            r'\d+(?:\.\d+)?"\s*[LWH]',       # 100"L
        ]
        
        for pattern in dim_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def extract_retail_code_and_pricing(self, html):
        """Extract retail codes for pricing"""
        retail_codes = {}
        
        # Look for retail code patterns
        patterns = [
            r'Retail Code:?\s*\n?([^<\n]+)',
            r'(?:Queen|King|Twin|Full|Chair|Sofa):\s*(\d{5,6})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Parse size and code
                size_code_match = re.search(r'(Queen|King|Twin|Full|Chair|Sofa):\s*(\d{5,6})', match, re.IGNORECASE)
                if size_code_match:
                    size = size_code_match.group(1).strip()
                    code = size_code_match.group(2).strip()
                    retail_codes[size] = code
        
        return retail_codes
    
    def calculate_price_from_retail_code(self, retail_code):
        """Calculate sell price from Happy Homes retail code (7****7 format)"""
        if not retail_code or len(retail_code) != 5:
            return None
        
        if retail_code.startswith('7') and retail_code.endswith('7'):
            # Extract middle 3 digits as vendor cost
            vendor_cost = int(retail_code[1:4])
            # Multiply by 1.7 and round
            sell_price = round(vendor_cost * 1.7)
            return sell_price
        
        return None
    
    def check_sold_out_status(self, html):
        """Check if product is sold out"""
        sold_out_patterns = [
            r'sold\s*out',
            r'out\s*of\s*stock',
            r'unavailable',
            r'discontinued',
        ]
        
        html_lower = html.lower()
        for pattern in sold_out_patterns:
            if re.search(pattern, html_lower):
                return True
        
        return False
    
    def discover_all_product_urls(self):
        """Discover all product URLs from Happy Homes categories"""
        print("🔍 Discovering all product URLs...")
        
        # Happy Homes category pages to scrape
        category_urls = [
            f"{self.base_url}/store/c24/Sleepers_%26_Futons",
            f"{self.base_url}/store/c23/Stationary_Sofa_%26_Loveseats",
            f"{self.base_url}/store/c21/Stationary_Sectionals",
            f"{self.base_url}/store/c19/Reclining_Sofa_%26_Loveseats", 
            f"{self.base_url}/store/c32/Reclining_Sectionals",
            f"{self.base_url}/store/c10/Recliners_%26_Lift_Chairs",
            f"{self.base_url}/store/c14/Occasional_Tables",
            f"{self.base_url}/store/c11/TV_Stands",
            f"{self.base_url}/store/c22/Accessories",
            f"{self.base_url}/store/c25/Office_%26_Bookcase",
            f"{self.base_url}/store/c30/Beds",
            f"{self.base_url}/store/c7/Bedrooms",
            f"{self.base_url}/store/c31/Daybeds",
            f"{self.base_url}/store/c17/Mattresses",
            f"{self.base_url}/store/c29/Vanities_%26_Mirrors",
            f"{self.base_url}/store/c8/Dining_Rooms",
            f"{self.base_url}/store/c28/Barstools",
        ]
        
        all_product_urls = set()
        
        for category_url in category_urls:
            print(f"  📂 Scanning category: {category_url.split('/')[-1]}")
            html = self.fetch_html(category_url)
            if not html:
                continue
            
            # Extract product links from category page
            product_links = re.findall(
                r'<a[^>]*href="(/store/p\d+/[^"]+)"[^>]*>',
                html, re.IGNORECASE
            )
            
            for link in product_links:
                full_url = urljoin(self.base_url, link)
                all_product_urls.add(full_url)
        
        print(f"✅ Found {len(all_product_urls)} product URLs")
        return all_product_urls
    
    def process_single_product(self, product_url):
        """Process a single product URL and return product data"""
        print(f"🔄 Processing: {product_url.split('/')[-1]}")
        
        html = self.fetch_html(product_url)
        if not html:
            return None
        
        # Check if sold out
        if self.check_sold_out_status(html):
            print(f"  ❌ SOLD OUT: {product_url.split('/')[-1]}")
            return None
        
        # Extract product ID from URL
        product_id_match = re.search(r'/p(\d+)/', product_url)
        if not product_id_match:
            print(f"  ⚠️ Could not extract product ID from {product_url}")
            return None
        
        product_id = f"p{product_id_match.group(1)}"
        
        # Extract images
        image_urls = self.extract_product_images(html, product_url)
        print(f"  📸 Found {len(image_urls)} images")
        
        # Download and save images
        saved_image_paths = []
        for i, img_url in enumerate(image_urls[:5]):  # Limit to 5 images max
            saved_path = self.download_and_save_image(img_url, product_id, i + 1)
            if saved_path:
                saved_image_paths.append(saved_path)
                print(f"    ✅ Saved image {i+1}")
        
        # Extract detailed description
        description_data = self.extract_detailed_description(html)
        
        # Extract pricing from retail codes
        retail_codes = self.extract_retail_code_and_pricing(html)
        
        # Calculate pricing
        sell_price = None
        size_prices = {}
        
        for size, code in retail_codes.items():
            price = self.calculate_price_from_retail_code(code)
            if price:
                size_prices[size] = {"sell": price}
        
        # If single price, use it as sell_price
        if len(size_prices) == 1:
            sell_price = list(size_prices.values())[0]["sell"]
            size_prices = {}
        elif not size_prices:
            # Try to extract a single retail code
            single_code_match = re.search(r'(\d{5})', html)
            if single_code_match:
                sell_price = self.calculate_price_from_retail_code(single_code_match.group(1))
        
        # Extract product name from title
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        product_name = ""
        if title_match:
            product_name = unescape(title_match.group(1).strip())
            # Clean up title
            product_name = re.sub(r'\s*-\s*Happy Homes.*$', '', product_name, re.IGNORECASE)
        
        # Determine category (you may need to enhance this logic)
        category = self.determine_category_from_url_or_content(product_url, html)
        
        # Build product data
        product_data = {
            "id": product_id,
            "name": product_name,
            "image": saved_image_paths[0] if saved_image_paths else "",
            "page": product_url,
            "category": category,
            "color": description_data.get('color', ''),
            "material": description_data.get('material', ''),
            "dimensions": description_data.get('dimensions', ''),
            "description": description_data.get('description', ''),
            "vendor": "Happy Homes"
        }
        
        # Add images array if multiple images
        if len(saved_image_paths) > 1:
            product_data["images"] = saved_image_paths
        
        if sell_price:
            product_data["sell_price"] = sell_price
        elif size_prices:
            product_data["size_prices"] = size_prices
        
        print(f"  ✅ SUCCESS: {product_name[:50]}... (${sell_price or 'multi-size'})")
        return product_data
    
    def determine_category_from_url_or_content(self, url, html):
        """Determine product category from URL or content"""
        # Map URL patterns to categories
        category_mapping = {
            '/c24/': 'Sleepers & Futons',
            '/c23/': 'Stationary Sofa & Loveseats', 
            '/c21/': 'Stationary Sectionals',
            '/c19/': 'Reclining Sofa & Loveseats',
            '/c32/': 'Reclining Sectionals',
            '/c10/': 'Recliners & Lift Chairs',
            '/c14/': 'Occasional Tables',
            '/c11/': 'TV Stands', 
            '/c22/': 'Accessories',
            '/c25/': 'Office & Bookcase',
            '/c30/': 'Beds',
            '/c7/': 'Bedrooms',
            '/c31/': 'Daybeds',
            '/c17/': 'Mattresses',
            '/c29/': 'Vanities & Mirrors',
            '/c8/': 'Dining Rooms',
            '/c28/': 'Barstools',
        }
        
        for pattern, category in category_mapping.items():
            if pattern in url:
                return category
        
        return 'Accessories'  # Default fallback
    
    def run_full_rescan(self):
        """Execute full rescan and update"""
        print("🚀 Starting Enhanced Happy Homes Full Rescan...")
        
        # Discover all current products
        current_urls = self.discover_all_product_urls()
        self.inventory_tracking['current_urls'] = current_urls
        
        # Track changes
        previous_urls = set(self.inventory_tracking.get('previous_urls', []))
        new_urls = current_urls - previous_urls
        removed_urls = previous_urls - current_urls
        
        print(f"\n📊 Inventory Changes:")
        print(f"  🆕 New products: {len(new_urls)}")
        print(f"  ❌ Removed products: {len(removed_urls)}")
        print(f"  📦 Total current: {len(current_urls)}")
        
        # Process all products
        updated_products = []
        processed_count = 0
        
        for product_url in current_urls:
            product_data = self.process_single_product(product_url)
            if product_data:
                updated_products.append(product_data)
            
            processed_count += 1
            if processed_count % 50 == 0:
                print(f"\n⏳ Progress: {processed_count}/{len(current_urls)} processed")
            
            time.sleep(0.3)  # Be nice to the server
        
        # Update products.json
        # Remove old Happy Homes products and add new ones
        non_happy_homes = [p for p in self.products if p.get('vendor') != 'Happy Homes']
        all_products = non_happy_homes + updated_products
        
        # Save updated products
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(all_products, f, indent=2)
        
        # Update inventory tracking
        self.inventory_tracking['previous_urls'] = list(current_urls)
        self.inventory_tracking['last_scan'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.inventory_tracking['scan_history'].append({
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_products': len(updated_products),
            'new_products': len(new_urls),
            'removed_products': len(removed_urls)
        })
        
        self.save_inventory_tracking()
        
        print(f"\n🎉 Rescan Complete!")
        print(f"  ✅ Products processed: {len(updated_products)}")
        print(f"  📸 Products with multiple images: {sum(1 for p in updated_products if p.get('images'))}")
        print(f"  💾 Updated products.json with {len(all_products)} total products")
        
        return {
            'success': True,
            'total_products': len(updated_products),
            'new_products': len(new_urls),
            'removed_products': len(removed_urls),
            'total_all_products': len(all_products),
            'multi_image_products': sum(1 for p in updated_products if p.get('images'))
        }


if __name__ == '__main__':
    scraper = HappyHomesScrapingEngine()
    result = scraper.run_full_rescan()
    print(f"\n🏆 Final Results: {result}")