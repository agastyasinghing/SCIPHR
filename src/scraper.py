"""
UFC Fight Data Scraper
Scrapes historical UFC fight data from ufcstats.com
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re

class UFCStatsScraper:
    """
    Scraper for UFC fight statistics
    """
    
    def __init__(self):
        self.base_url = "http://ufcstats.com/statistics/events/completed"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def get_completed_events(self, max_events=50):
        """
        Get list of completed UFC events
        
        Args:
            max_events: Maximum number of events to scrape (default 50 for testing)
            
        Returns:
            List of event URLs
        """
        print("Fetching completed events...")
        response = requests.get(self.base_url, headers=self.headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all event links
        event_links = []
        event_rows = soup.find_all('tr', class_='b-statistics__table-row')
        
        for row in event_rows[:max_events]:
            link = row.find('a', class_='b-link')
            if link and link.get('href'):
                event_links.append(link['href'])
                
        print(f"Found {len(event_links)} events to scrape")
        return event_links
    
    def scrape_event_fights(self, event_url):
        """
        Scrape all fights from a single event
        
        Args:
            event_url: URL of the event page
            
        Returns:
            List of fight data dictionaries
        """
        try:
            response = requests.get(event_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get event name and date
            event_name = soup.find('h2', class_='b-content__title').text.strip()
            event_date = soup.find('li', class_='b-list__box-list-item').text.strip()
            event_date = event_date.replace('Date:', '').strip()
            
            fights = []
            fight_rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            for row in fight_rows[1:]:  # Skip header row
                try:
                    fight_link = row.get('data-link')
                    if fight_link:
                        fight_data = self.scrape_fight_details(fight_link, event_name, event_date)
                        if fight_data:
                            fights.append(fight_data)
                            print(f"  ✓ Scraped: {fight_data['fighter1_name']} vs {fight_data['fighter2_name']}")
                except Exception as e:
                    print(f"  ✗ Error scraping fight: {e}")
                    continue
                    
            return fights
            
        except Exception as e:
            print(f"Error scraping event {event_url}: {e}")
            return []
    
    def scrape_fight_details(self, fight_url, event_name, event_date):
        """
        Scrape detailed statistics for a single fight
        
        Args:
            fight_url: URL of the fight details page
            event_name: Name of the event
            event_date: Date of the event
            
        Returns:
            Dictionary with fight statistics
        """
        try:
            time.sleep(0.5)  # Be polite to the server
            response = requests.get(fight_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get fighter names
            fighters = soup.find_all('a', class_='b-link_style_black')
            fighter1_name = fighters[0].text.strip()
            fighter2_name = fighters[1].text.strip()
            
            # Get fight result
            result_divs = soup.find_all('i', class_='b-fight-details__person-status')
            fighter1_result = result_divs[0].text.strip() if len(result_divs) > 0 else ''
            fighter2_result = result_divs[1].text.strip() if len(result_divs) > 1 else ''
            
            # Winner (1 = fighter1 wins, 0 = fighter2 wins, 0.5 = draw)
            if 'W' in fighter1_result:
                winner = 1
            elif 'W' in fighter2_result:
                winner = 0
            else:
                winner = 0.5  # Draw or NC
            
            # Get fight details (method, round, time)
            details = soup.find_all('p', class_='b-fight-details__text')
            method = ''
            round_num = ''
            fight_time = ''
            
            for detail in details:
                text = detail.text.strip()
                if 'Method:' in text:
                    method = text.replace('Method:', '').strip()
                elif 'Round:' in text:
                    round_num = text.replace('Round:', '').strip()
                elif 'Time:' in text:
                    fight_time = text.replace('Time:', '').strip()
            
            # Get total stats table
            stats_table = soup.find('table', class_='b-fight-details__table')
            if not stats_table:
                return None
                
            stats_rows = stats_table.find_all('tr')[1:]  # Skip header
            
            # Parse stats (fighter1 vs fighter2)
            stats = {}
            stat_names = ['knockdowns', 'sig_strikes', 'sig_strike_pct', 'total_strikes',
                         'takedowns', 'takedown_pct', 'submissions', 'reversals', 'ctrl_time']
            
            for i, row in enumerate(stats_rows):
                cols = row.find_all('td')
                if len(cols) >= 3:
                    fighter1_stat = cols[0].text.strip()
                    fighter2_stat = cols[2].text.strip()
                    
                    if i < len(stat_names):
                        stats[f'fighter1_{stat_names[i]}'] = fighter1_stat
                        stats[f'fighter2_{stat_names[i]}'] = fighter2_stat
            
            # Combine all data
            fight_data = {
                'event_name': event_name,
                'event_date': event_date,
                'fighter1_name': fighter1_name,
                'fighter2_name': fighter2_name,
                'winner': winner,
                'method': method,
                'round': round_num,
                'time': fight_time,
                **stats
            }
            
            return fight_data
            
        except Exception as e:
            print(f"Error scraping fight details: {e}")
            return None
    
    def scrape_all_fights(self, max_events=50, save_path='data/ufc_fights.csv'):
        """
        Scrape fights from multiple events and save to CSV
        
        Args:
            max_events: Number of events to scrape
            save_path: Where to save the CSV file
        """
        print(f"\n🥊 Starting UFC Stats Scraper")
        print(f"Target: {max_events} events\n")
        
        # Get event URLs
        event_urls = self.get_completed_events(max_events)
        
        all_fights = []
        
        # Scrape each event
        for i, event_url in enumerate(event_urls, 1):
            print(f"\n[{i}/{len(event_urls)}] Scraping event: {event_url}")
            fights = self.scrape_event_fights(event_url)
            all_fights.extend(fights)
            time.sleep(1)  # Be nice to the server
        
        # Convert to DataFrame and save
        df = pd.DataFrame(all_fights)
        df.to_csv(save_path, index=False)
        
        print(f"\n✅ Done! Scraped {len(all_fights)} fights")
        print(f"📁 Saved to: {save_path}")
        print(f"\nPreview:")
        print(df.head())
        
        return df


if __name__ == "__main__":
    # Run the scraper
    scraper = UFCStatsScraper()
    df = scraper.scrape_all_fights(max_events=150)  # Start with 10 events for testing