import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import deque

class EmailScraper:
    def __init__(self, start_url, max_pages=50):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.urls_to_visit = deque()
        self.urls_to_visit.append(start_url)
        self.domain = urlparse(start_url).netloc
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        self.found_emails = set()

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.domain

    def get_all_links(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find emails in the current page
            self.find_emails(response.text, url)
            
            # Extract all links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                if self.is_valid_url(full_url) and full_url not in self.visited_urls:
                    self.urls_to_visit.append(full_url)
                    
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")

    def find_emails(self, text, source_url):
        emails = set(self.email_pattern.findall(text))
        for email in emails:
            if email not in self.found_emails:
                self.found_emails.add(email)
                print(f"Found email: {email} (on {source_url})")

    def scrape(self):
        while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_url = self.urls_to_visit.popleft()
            
            if current_url in self.visited_urls:
                continue
                
            print(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            
            self.get_all_links(current_url)
        
        print("\nScraping complete!")
        if self.found_emails:
            print(f"\n------------------ Found {len(self.found_emails)} emails ------------------")
            for email in sorted(self.found_emails):
                print(email)
        else:
            print("No emails found.")

if __name__ == "__main__":
    start_url = input("Enter the starting URL (e.g., https://example.com): ").strip()
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    
    max_pages = input("Enter maximum number of pages to scrape (default 50): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 50
    
    scraper = EmailScraper(start_url, max_pages)
    scraper.scrape()
