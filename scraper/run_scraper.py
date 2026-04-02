"""
Main script to scrape fighter images
Run this from the sciphr/scraper directory
"""

import sys
import os
import pandas as pd

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from fighter_image_scraper import FighterImageScraper

def get_fighter_data_from_csv():
    """Get fighter names and URLs from CSV"""
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'golden_full_converted.csv')
    
    print(f"📂 Loading fighters from CSV: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Get unique fighters with their URLs
    fighters = {}
    
    # From red corner
    for _, row in df[['r_name', 'r_url']].dropna().drop_duplicates().iterrows():
        if row['r_name'] not in fighters:
            fighters[row['r_name']] = row['r_url']
    
    # From blue corner
    for _, row in df[['b_name', 'b_url']].dropna().drop_duplicates().iterrows():
        if row['b_name'] not in fighters:
            fighters[row['b_name']] = row['b_url']
    
    return fighters

def main():
    print("🚀 SCIPHR Fighter Image Scraper\n")
    
    # Get fighter data from CSV
    fighters_data = get_fighter_data_from_csv()
    print(f"\n✓ Found {len(fighters_data)} fighters with URLs\n")
    
    # Initialize scraper
    scraper = FighterImageScraper(
        output_dir='../frontend-redesign/sciphr-redesign/frontend-redesign/public/fighters'
    )
    
    # Start scraping
    print("\n" + "="*70)
    print("⚠️  IMPORTANT NOTES:")
    print("="*70)
    print("• This will take 1-2 hours for all fighters")
    print("• Progress is saved automatically every 10 fighters")
    print("• Press Ctrl+C to stop anytime")
    print("• Re-run to continue from where you left off")
    print("="*70 + "\n")
    
    input("Press Enter to start scraping...")
    
    try:
        scraper.scrape_all_with_urls(fighters_data, delay=1.0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("✓ Progress saved. Run again to continue.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("✓ Progress saved. Check error and try again.")
    
    print("\n✅ Done!")
    print(f"📁 Images saved to: {scraper.output_dir}")
    print(f"📄 Mapping file: {scraper.mapping_file}")


if __name__ == "__main__":
    main()