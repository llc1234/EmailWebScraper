import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import deque

class PDFScraper:
    def __init__(self, start_url, max_pages=50):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.urls_to_visit = deque()
        self.urls_to_visit.append(start_url)
        self.domain = urlparse(start_url).netloc
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        self.found_pdfs = {}  # Dictionary: PDF URL -> set of source URLs

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.domain

    def is_pdf_link(self, url):
        """Check if URL points to a PDF resource"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check common PDF indicators
        if path.endswith('.pdf'):
            return True
        if 'pdf' in path.split('/')[-1].split('.')[0].lower():
            return True
        return False

    def get_all_links(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                
                # Handle PDF links separately
                if self.is_pdf_link(full_url):
                    if full_url not in self.found_pdfs:
                        self.found_pdfs[full_url] = set()
                    self.found_pdfs[full_url].add(url)
                    print(f"Found PDF: {full_url} (on {url})")
                # Process regular links
                elif self.is_valid_url(full_url) and full_url not in self.visited_urls:
                    self.urls_to_visit.append(full_url)
                    
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")

    def scrape(self):
        while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_url = self.urls_to_visit.popleft()
            
            if current_url in self.visited_urls:
                continue
                
            print(f"Scraping: {current_url}")
            self.visited_urls.add(current_url)
            self.get_all_links(current_url)
        
        print("\nScraping complete!")
        if self.found_pdfs:
            print(f"\n------------------------------------- Found {len(self.found_pdfs)} PDF documents -------------------------------------")
            for pdf_url, source_urls in self.found_pdfs.items():
                print(f"\nPDF: {pdf_url}")
                print(f"Found on {len(source_urls)} pages:")
                for idx, source in enumerate(source_urls, 1):
                    print(f"  {idx}. {source}")
        else:
            print("No PDFs found.")

if __name__ == "__main__":
    start_url = input("Enter the starting URL (e.g., https://example.com): ").strip()
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    
    max_pages = input("Enter maximum number of pages to scrape (default 50): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 50
    
    scraper = PDFScraper(start_url, max_pages)
    scraper.scrape()
