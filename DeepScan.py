import requests
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import re
from collections import deque
from xml.etree import ElementTree as ET
import time

class EmailScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.visited = set()
        self.queue = deque()
        self.broken_links = set()
        self.emails = set()
        self.sitemaps = []
        self.headers = {
            'User-Agent': 'EmailScraperBot/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.robot_parser = None
    
    def init_robots_parser(self):
        robots_url = urljoin(self.base_url, '/robots.txt')
        try:
            # Fetch robots.txt manually
            response = requests.get(robots_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                # Create parser and parse content
                self.robot_parser = RobotFileParser()
                self.robot_parser.parse(response.text.splitlines())
                print(f"Parsed robots.txt for {self.base_domain}")
                
                # Extract sitemaps from robots.txt content
                for line in response.text.splitlines():
                    if line.strip().lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        self.sitemaps.append(sitemap_url)
        except Exception as e:
            print(f"Robots.txt error: {str(e)}")

    def is_allowed(self, url):
        if self.robot_parser:
            try:
                return self.robot_parser.can_fetch('*', url)
            except:
                return True
        return True

    def normalize_url(self, url):
        parsed = urlparse(url)
        # Remove fragments and normalize
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', parsed.query, ''))
        return normalized.rstrip('/')

    def extract_emails(self, text):
        # Robust email regex pattern
        pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        return set(re.findall(pattern, text))

    def get_links(self, url, html):
        # Try different parsers if lxml is not available
        try:
            soup = BeautifulSoup(html, 'lxml')
        except:
            try:
                soup = BeautifulSoup(html, 'html.parser')
            except Exception as e:
                print(f"HTML parsing failed: {str(e)}")
                return set()
        
        links = set()
        
        for tag in soup.find_all(['a', 'link'], href=True):
            href = tag['href'].strip()
            if any(href.startswith(prefix) for prefix in 
                  ('mailto:', 'tel:', 'javascript:', '#')):
                continue
            
            # Handle relative URLs
            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            
            # Normalize and filter
            normalized = self.normalize_url(absolute_url)
            if parsed.netloc == self.base_domain:
                links.add(normalized)
                
        return links

    def parse_sitemap(self, content):
        urls = set()
        try:
            root = ET.fromstring(content)
            # Handle different sitemap formats
            namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Sitemap index
            for elem in root.findall('sm:sitemap/sm:loc', namespace) or \
                        root.findall('sitemap/loc'):
                if elem.text:
                    urls.add(elem.text.strip())
            
            # URL set
            for elem in root.findall('sm:url/sm:loc', namespace) or \
                        root.findall('url/loc'):
                if elem.text:
                    urls.add(elem.text.strip())
                    
        except ET.ParseError:
            # Handle plain text sitemap
            for line in content.splitlines():
                clean_line = line.strip()
                if clean_line and not clean_line.startswith('#'):
                    urls.add(clean_line)
                    
        return urls

    def crawl(self, max_depth=5, delay=1.0):
        self.init_robots_parser()
        
        # Start with base URL and sitemaps
        self.queue.append((self.base_url, 0))
        for sitemap in self.sitemaps:
            if urlparse(sitemap).netloc == self.base_domain:
                self.queue.append((sitemap, 0))
        
        while self.queue:
            url, depth = self.queue.popleft()
            
            if depth > max_depth:
                continue
            if url in self.visited:
                continue
                
            self.visited.add(url)
            
            if not self.is_allowed(url):
                print(f"Skipping disallowed URL: {url}")
                continue
                
            try:
                print(f"Crawling ({depth}): {url}")
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                # Handle different content types
                content_type = response.headers.get('Content-Type', '').lower()
                
                # Process sitemaps
                if 'sitemap' in url or 'xml' in content_type:
                    sitemap_urls = self.parse_sitemap(response.text)
                    if sitemap_urls:
                        for new_url in sitemap_urls:
                            normalized = self.normalize_url(new_url)
                            if urlparse(normalized).netloc == self.base_domain:
                                if normalized not in self.visited:
                                    self.queue.append((normalized, depth))
                
                # Process HTML content
                elif 'html' in content_type:
                    # Extract emails
                    new_emails = self.extract_emails(response.text)
                    if new_emails:
                        self.emails.update(new_emails)
                        print(f"Found {len(new_emails)} emails at {url}")
                    
                    # Extract links
                    for link in self.get_links(url, response.text):
                        if link not in self.visited:
                            self.queue.append((link, depth + 1))
            
            except requests.RequestException as e:
                if hasattr(e, 'response') and e.response:
                    if e.response.status_code == 404:
                        self.broken_links.add(url)
                print(f"Error ({url}): {str(e)}")
            
            time.sleep(delay)  # Respect crawl delay

    def report(self):
        print("\n" + "="*60)
        print(f"Crawling Report for {self.base_url}")
        print(f"Pages crawled: {len(self.visited)}")
        print(f"Broken links: {len(self.broken_links)}")
        print(f"Unique emails found: {len(self.emails)}")
        
        print("\nEmails:")
        for email in sorted(self.emails):
            print(f" - {email}")
            
        if self.broken_links:
            print("\nBroken Links:")
            for link in sorted(self.broken_links):
                print(f" - {link}")


if __name__ == "__main__":
    target_url = input("Enter the starting URL (e.g., https://example.com): ").strip()
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    max_pages = input("Enter maximum number of pages to scrape (default 5): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 5

    delay = input("Enter maximum number of delay (default 0.5 sec): ").strip()
    delay = float(delay) if delay.isdigit() else 0.5
    
    scraper = EmailScraper(target_url)
    scraper.crawl(max_depth=max_pages, delay=delay)
    scraper.report()
