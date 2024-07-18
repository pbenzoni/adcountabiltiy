from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import requests
from urllib.parse import urlparse
import os

# URL of the ads and tracking list
ads_tracking_list_url = "https://www.github.developerdan.com/hosts/lists/ads-and-tracking-extended.txt"

# Load the ads and tracking list
response = requests.get(ads_tracking_list_url)
ads_tracking_list = response.text.splitlines()
ads_domains = [line.split()[1] for line in ads_tracking_list if line and (not line == '') and (not line.startswith("#")) and line.split()]

# Set up Selenium WebDriver (using Chrome in this example)

service = Service('C:\\Users\\benzo\\repo\\adcountability\\chromedriver-win64\\chromedriver.exe')  # Adjust path to your chromedriver
#set selecnium to run in headless mode
options = Options()
options.headless = True

driver = webdriver.Chrome(service=service
                          , options=options)

# Function to extract and compare links
def check_ads_on_site(url):
    driver.get(url)
    time.sleep(13)


    all_links = []
    
    # Function to extract links from a given driver context from href and src tags
    def extract_links(driver):
        links = []
        link_attr_tags = []
        non_link_iframes = []
        # Extract links from the main page's body tag and its children
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # limit to body tag and its children
        soup = soup.find("body")
        # Extract links from a, link, and iframe tags, save the tag-attr-link tuple

        for tag in soup.find_all(["a", "link", "iframe"]):
            if tag.has_attr("href"):
                links.append(tag["href"])
                link_attr_tags.append((tag["href"], tag.name, "href"))
            if tag.has_attr("src"):
                links.append(tag["src"])
                link_attr_tags.append((tag["src"], tag.name, "src"))
            elif tag.name == "iframe" and tag.has_attr("id"):
                non_link_iframes.append(tag["id"])
        return links, link_attr_tags, non_link_iframes


    # Extract links from the main page
    all_links, link_attr_tags, non_link_iframes  = extract_links(driver)
    
    # Remove local links and reduce to FQDN
    external_links = []
    for link in all_links:
        # Remove local links 
        if link.startswith("/"):
            continue
        parsed_url = urlparse(link)
        if parsed_url.netloc:  # This checks if the link is external
            fqdn = parsed_url.netloc
            if len(fqdn.split(".")) > 2:
                fqdn = ".".join(fqdn.split(".")[-2:])
            external_links.append( fqdn)

    # Remove duplicates
    external_links = list(set(external_links))

    # # Check for any matches with the ads and tracking list
    matched_ads = []
    for fqdn_link in external_links:
        if fqdn_link in ads_domains:
            matched_ads.append(fqdn_link)

    # # Capture screenshots of matched elements
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    #filter down link_attr_tags to non-local links
    link_attr_tags = [(link, tag, attr) for link, tag, attr in link_attr_tags if link.startswith("http")]

    #filter down to matched links only in link_attr_tags

    matched_ltas = [(link, tag, attr) for link, tag, attr in link_attr_tags for fqdn in matched_ads if fqdn in link]
    
    #set base element to the body tag
    #TODO: customize paths to fit link and url
    base_element = driver.find_element(By.TAG_NAME, "body")
    for i, (link, tag, attr) in enumerate(matched_ltas):
        try:
            element = base_element
            element = driver.find_element(By.XPATH, f"//*[@*='{link}']")
            if element.rect.get("width") == 0 or element.rect.get("height") == 0:
                continue
            #scroll to the element
            driver.execute_script("arguments[0].scrollIntoView();", element)
            screenshot_path = os.path.join(screenshot_dir, f"matched_ad_{i + 1}.png")
            element.screenshot(screenshot_path)
            print(f"Screenshot saved for matched link: {link}")
        except Exception as e:
            print(f"Error capturing screenshot for matched link: {link} - {e.msg}")
    for i,iframe_id in enumerate(non_link_iframes):
        try:
            element = base_element
            element = driver.find_element(By.XPATH, f"//iframe[@id='{iframe_id}']")
            #get parent element
            element = element.find_element(By.XPATH, "..")
            if element.rect.get("width") == 0 or element.rect.get("height") == 0:
                continue
            #scroll to the element
            driver.execute_script("arguments[0].scrollIntoView();", element)
            screenshot_path = os.path.join(screenshot_dir, f"matched_iframe_ad_{i+1}.png")
            element.screenshot(screenshot_path)
            print(f"Screenshot saved for matched link: {iframe_id}")
        except Exception as e:
            print(f"Error capturing screenshot for matched link: {link} - {e.msg}")
    #grab the page screenshot after scrolling to the top
    driver.execute_script("window.scrollTo(0, 0);")
    driver.save_screenshot(os.path.join(screenshot_dir, "full_page.png"))

    return matched_ads

# Example usage
# TODO: take in list of URLs to check, and output to a CSV
url_to_check = "https://www.geeksforgeeks.org/regular-expression-to-validate-a-bitcoin-address/"  # Replace with the URL you want to check
matched_ads = check_ads_on_site(url_to_check)

print("Matched ad/tracking links:")
for ad in matched_ads:
    print(ad)

# Clean up
driver.quit()