"""
Fighter Image Scraper
Scrapes fighter headshots from Sherdog and saves them locally
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import json
from pathlib import Path
import re

class FighterImageScraper:
    def __init__(self, output_dir='../frontend-redesign/sciphr-redesign/frontend-redesign/public/fighters'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.mapping = {}
        self.mapping_file = self.output_dir / 'fighter_images.json'
        
        # Load existing mapping if it exists
        if self.mapping_file.exists():
            with open(self.mapping_file, 'r') as f:
                self.mapping = json.load(f)
    
    def clean_fighter_name(self, name):
        """Clean fighter name for filename"""
        # Remove special characters, replace spaces with hyphens
        clean = re.sub(r'[^\w\s-]', '', name.lower())
        clean = re.sub(r'[-\s]+', '-', clean)
        return clean.strip('-')
    
    def search_espn(self, fighter_name):
        """Search ESPN for fighter image using multiple methods"""
        try:
            print(f"  🔍 Searching ESPN...")
            
            # Method 1: Try direct URL format
            # ESPN URLs: https://www.espn.com/mma/fighter/_/id/[id]/[name]
            search_name = fighter_name.lower().replace(' ', '-').replace("'", "")
            
            # Method 2: Use ESPN's search/autocomplete API
            search_api = "https://site.api.espn.com/apis/search/v2"
            params = {
                'query': fighter_name,
                'region': 'us',
                'lang': 'en',
                'section': 'mma',
                'limit': 5
            }
            
            response = requests.get(search_api, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got results
                if data.get('results') and len(data['results']) > 0:
                    # Get first fighter result
                    for result in data['results']:
                        if result.get('type') == 'athlete' or 'fighter' in result.get('contentType', '').lower():
                            fighter_url = result.get('url')
                            
                            if fighter_url:
                                print(f"  ✓ Found ESPN page")
                                
                                # Fetch fighter page
                                time.sleep(0.5)
                                page_response = requests.get(fighter_url, headers=self.headers, timeout=15)
                                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                                
                                # Look for fighter image in multiple locations
                                # ESPN uses different classes for images
                                img = None
                                
                                # Try different selectors
                                selectors = [
                                    ('img', {'class': 'Image'}),
                                    ('img', {'class': 'PlayerHeader__Image'}),
                                    ('div', {'class': 'PlayerHeader__Photo'}),
                                    ('picture', {'class': 'Image'}),
                                ]
                                
                                for tag, attrs in selectors:
                                    element = page_soup.find(tag, attrs)
                                    if element:
                                        if tag == 'picture':
                                            img = element.find('img')
                                        elif tag == 'div':
                                            img = element.find('img')
                                        else:
                                            img = element
                                        
                                        if img:
                                            break
                                
                                if img:
                                    img_url = img.get('src') or img.get('data-default-src') or img.get('data-src')
                                    if img_url:
                                        # Handle ESPN's URL formats
                                        if img_url.startswith('//'):
                                            img_url = 'https:' + img_url
                                        elif not img_url.startswith('http'):
                                            img_url = 'https://www.espn.com' + img_url
                                        
                                        # ESPN images often have size parameters, get larger version
                                        if 'crop' in img_url:
                                            img_url = img_url.split('?')[0]  # Remove crop parameters
                                        
                                        print(f"  ✓ Found ESPN image")
                                        return img_url
                                
                                break  # Found the fighter but no image
            
            # Method 3: Try direct page construction
            # Some fighters might not show up in search but have pages
            direct_url = f"https://www.espn.com/mma/fighter/_/id/0/{search_name}"
            time.sleep(0.5)
            
            try:
                direct_response = requests.get(direct_url, headers=self.headers, timeout=10, allow_redirects=True)
                if direct_response.status_code == 200 and 'fighter' in direct_response.url:
                    soup = BeautifulSoup(direct_response.content, 'html.parser')
                    img = soup.find('img', class_='Image')
                    if img:
                        img_url = img.get('src')
                        if img_url:
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            print(f"  ✓ Found ESPN image (direct)")
                            return img_url
            except:
                pass
            
            return None
            
        except Exception as e:
            print(f"  ❌ ESPN error: {e}")
            return None
    
    def search_official_ufc(self, fighter_name):
        """Search official UFC website for fighter image"""
        try:
            # UFC.com athlete pages
            search_name = fighter_name.lower().replace(' ', '-')
            
            print(f"  🔍 Searching UFC.com...")
            
            # Try direct athlete page
            athlete_url = f"https://www.ufc.com/athlete/{search_name}"
            
            response = requests.get(athlete_url, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # UFC.com has hero images
                img = (
                    soup.find('img', class_='hero-profile__image') or
                    soup.find('div', class_='hero-profile__image-wrap').find('img') if soup.find('div', class_='hero-profile__image-wrap') else None or
                    soup.find('img', class_='athlete-profile__image')
                )
                
                if img:
                    img_url = img.get('src')
                    if img_url:
                        if not img_url.startswith('http'):
                            img_url = 'https://www.ufc.com' + img_url
                        print(f"  ✓ Found UFC.com image")
                        return img_url
            
            return None
            
        except Exception as e:
            print(f"  ❌ UFC.com error: {e}")
            return None
    
    def download_image(self, url, fighter_name):
        """Download image from URL and save it"""
        try:
            clean_name = self.clean_fighter_name(fighter_name)
            filename = f"{clean_name}.jpg"
            filepath = self.output_dir / filename
            
            # Skip if already exists
            if filepath.exists():
                print(f"  ✓ Already exists: {filename}")
                return filename
            
            print(f"  ⬇️  Downloading...")
            response = requests.get(url, headers=self.headers, timeout=15, stream=True)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"  ✅ Saved: {filename}")
                return filename
            else:
                print(f"  ❌ Download failed (status {response.status_code})")
                return None
                
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            return None
    
    def scrape_fighter(self, fighter_name):
        """Scrape image for a single fighter"""
        # Check if already processed successfully
        if fighter_name in self.mapping and self.mapping[fighter_name]:
            return self.mapping[fighter_name]
        
        # Try Sherdog
        image_url = self.search_sherdog(fighter_name)
        
        if image_url:
            filename = self.download_image(image_url, fighter_name)
            if filename:
                self.mapping[fighter_name] = {
                    'filename': filename,
                    'url': image_url,
                    'source': 'sherdog'
                }
                self.save_mapping()
                return self.mapping[fighter_name]
        
        print(f"  ⚠️  No image found")
        self.mapping[fighter_name] = None
        self.save_mapping()
        return None
    
    def save_mapping(self):
        """Save mapping to JSON file"""
        with open(self.mapping_file, 'w') as f:
            json.dump(self.mapping, f, indent=2)
    
    def scrape_all(self, fighter_list, delay=2.0):
        """Scrape images for all fighters in list"""
        print(f"\n{'='*70}")
        print(f"🥊 FIGHTER IMAGE SCRAPER")
        print(f"{'='*70}")
        print(f"Total fighters: {len(fighter_list)}")
        print(f"Output: {self.output_dir}")
        print(f"Delay: {delay}s between requests")
        print(f"{'='*70}\n")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, fighter in enumerate(fighter_list, 1):
            print(f"\n[{i}/{len(fighter_list)}] {fighter}")
            
            if fighter in self.mapping and self.mapping[fighter]:
                print(f"  ✓ Already processed")
                skipped_count += 1
                continue
            
            result = self.scrape_fighter(fighter)
            
            if result:
                success_count += 1
            else:
                failed_count += 1
            
            # Rate limiting
            if i < len(fighter_list):
                time.sleep(delay)
            
            # Save progress every 10 fighters
            if i % 10 == 0:
                print(f"\n💾 Progress saved ({success_count} successful, {failed_count} failed)")
        
    def scrape_all_with_urls(self, fighters_dict, delay=1.5):
        """Scrape images for all fighters trying multiple sources"""
        print(f"\n{'='*70}")
        print(f"🥊 FIGHTER IMAGE SCRAPER")
        print(f"{'='*70}")
        print(f"Total fighters: {len(fighters_dict)}")
        print(f"Output: {self.output_dir}")
        print(f"Sources: UFC.com → ESPN → Sherdog")
        print(f"Delay: {delay}s between requests")
        print(f"{'='*70}\n")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        fighter_list = list(fighters_dict.keys())
        
        for i, fighter_name in enumerate(fighter_list, 1):
            print(f"\n[{i}/{len(fighter_list)}] {fighter_name}")
            
            if fighter_name in self.mapping and self.mapping[fighter_name]:
                print(f"  ✓ Already processed")
                skipped_count += 1
                continue
            
            image_url = None
            source = None
            
            # Try UFC.com first (best quality)
            image_url = self.search_official_ufc(fighter_name)
            if image_url:
                source = 'ufc.com'
            
            # Try ESPN if UFC.com failed
            if not image_url:
                time.sleep(1)
                image_url = self.search_espn(fighter_name)
                if image_url:
                    source = 'espn'
            
            # If still no image found, skip
            if not image_url:
                print(f"  ⚠️  No image found from any source")
            
            if image_url:
                filename = self.download_image(image_url, fighter_name)
                if filename:
                    self.mapping[fighter_name] = {
                        'filename': filename,
                        'url': image_url,
                        'source': source
                    }
                    self.save_mapping()
                    success_count += 1
                    print(f"  ✅ Success from {source}")
                else:
                    failed_count += 1
            else:
                print(f"  ⚠️  No image found from any source")
                failed_count += 1
                self.mapping[fighter_name] = None
                self.save_mapping()
            
            # Rate limiting
            if i < len(fighter_list):
                time.sleep(delay)
            
            # Save progress every 10 fighters
            if i % 10 == 0:
                print(f"\n💾 Progress: {success_count} successful, {failed_count} failed, {skipped_count} skipped")
        
        print(f"\n{'='*70}")
        print(f"✅ SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"✓ Success: {success_count}")
        print(f"⚠️  Failed: {failed_count}")
        print(f"→ Skipped: {skipped_count}")
        print(f"{'='*70}\n")
        print(f"\n{'='*70}")
        print(f"✅ SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"✓ Success: {success_count}")
        print(f"⚠️  Failed: {failed_count}")
        print(f"→ Skipped: {skipped_count}")
        print(f"{'='*70}\n")



if __name__ == "__main__":
    pass