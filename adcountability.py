import requests
import pandas as pd
import os
import json
from urllib.parse import urlparse
# Cache for storing seller.json data by domain
sellers_cache = {}

# Mapping for domains with special cases for seller.json locations
special_sellers_json = {
    'advertising.com': 'https://www.yahoo.com/sellers.json',  # Example override
    'google.com': 'http://realtimebidding.google.com/sellers.json',
    'adtech.com':'https://www.yahoo.com/sellers.json',
    'districtm.io':'https://www.media.net/sellers.json',
    'indexexchange.com':'https://cdn.indexexchange.com/sellers.json',
    'sovrn.com':'https://lijit.com/sellers.json',
    'xad.com':'https://www.groundtruth.com/sellers.json',
    'yieldmo.com':'https://yieldmo.com/sellers.json'
    # Add more overrides as necessary
}
local_cache_domains = [
    'freewheel.tv',
    'rhythmone.com',
    'pubnative.net',
    'rhythmone.com',
    'sonobi.com',
    'sovrn.com'
                                          ]
skip_domains = [
    'spotx.tv'
]
def ensure_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def fetch_ads_txt(domain):
    url = f'http://{domain}/ads.txt'
    try:
        response = requests.get(url,
                                headers=
                                {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                                    'Accept-Language': 'en-US,en;q=0.5',
                                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                                    'Connection': 'keep-alive',
                                    'Priority': 'u=0, i',
                                    'Upgrade-Insecure-Requests': '1',
                                    'Sec-Fetch-Dest': 'document',
                                    'Sec-Fetch-Mode': 'navigate',
                                    'Sec-Fetch-Site': 'cross-site',
                                    'Sec-Fetch-User': '?1',
                                }
                                )
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching ads.txt for {domain}: {e}")
        return None

def parse_ads_txt(content, domain):
    lines = content.splitlines()
    entries = []
    for line in lines:
        if line.strip() and not line.startswith('#'):
            parts = line.split(',')
            if len(parts) >= 3:
                entries.append({
                    'domain': domain,
                    'ad_domain': parts[0].strip(),
                    'publisher_id': parts[1].strip(),
                    'relationship': parts[2].strip(),
                    'cert_authority_id': parts[3].strip() if len(parts) > 3 else None
                })
    return entries


def fetch_seller_json(domain):
    if domain in skip_domains:
        return None
    elif domain in sellers_cache:
        return sellers_cache[domain]   
    elif domain in local_cache_domains:
        # Handle local caching
        local_path = f'sellers/{domain.replace(".", "_")}_sellers.json'
        if os.path.exists(local_path):
            with open(local_path, 'r') as file:
                sellers_cache[domain] = json.load(file)
                return sellers_cache[domain]

    # Check if there is a special URL or use the default
    url = special_sellers_json.get(domain, f'http://{domain}/sellers.json')
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        sellers_data = response.json()
        sellers_cache[domain] = sellers_data
        
        # Save to local cache if applicable
        if domain in local_cache_domains:
            with open(local_path, 'w') as file:
                json.dump(sellers_data, file)
        
        return sellers_data
    except requests.RequestException as e:
        print(f"Error fetching sellers.json for {domain} from {url}: {e}")
        return None


def augment_entries(entries):
    for entry in entries:
        domain = entry['ad_domain']
        sellers_data = fetch_seller_json(domain)
        if sellers_data and 'sellers' in sellers_data:
            seller_info = next((s for s in sellers_data['sellers'] if str(s['seller_id']) == str(entry['publisher_id'])), None)
            if seller_info:
                entry.update({
                    'seller_name': seller_info.get('name'),
                    'seller_domain': seller_info.get('domain'),
                    'seller_type': seller_info.get('seller_type')
                })
    return entries

def main(domains):
    all_entries = []
    for domain in domains:
        print(f"Processing ads.txt for {domain}")        
        ads_txt_content = fetch_ads_txt(domain)
        if ads_txt_content:
            entries = parse_ads_txt(ads_txt_content, domain)
            augmented_entries = augment_entries(entries)
            all_entries.extend(augmented_entries)

    if all_entries:
        df = pd.DataFrame(all_entries)
        df.to_csv("ads_data_combined.csv", index=False)
        print("Data saved to ads_data_combined.csv")
    else:
        print("No ads.txt data to process across the domains.")

if __name__ == "__main__":
    # Load cache if available from sellers_cache.json
    if os.path.exists('sellers_cache.json'):
        with open('sellers_cache.json', 'r') as file:
            sellers_cache = json.load(file)
    domains_df = pd.read_csv("./domains.csv")  # Load domains from a CSV file
    domains = domains_df['domain'].tolist()  # Convert the domain column to a list
    main(domains)