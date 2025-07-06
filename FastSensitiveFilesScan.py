import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import deque

class SensitiveFileScraper:
    def __init__(self, start_url, max_pages=50):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.urls_to_visit = deque()
        self.urls_to_visit.append(start_url)
        self.domain = urlparse(start_url).netloc
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        self.found_files = {}  # Dictionary: file URL -> set of source URLs
        # Common sensitive file patterns
        self.sensitive_patterns = [
            r'\.(bak|backup|old|orig|save|copy|bkp)$',  # Backup files
            r'\.(swp|swo|tmp|temp)$',  # Temporary files
            r'\.(log|error|err)$',  # Log files
            r'\.(env|config|conf|cfg|ini|properties)$',  # Configuration files
            r'\.(sql|db|sqlite|mdb)$',  # Database files
            r'\.(pem|key|crt|cer|pfx|p12)$',  # Certificate files
            r'(password|passwd|pwd|secret|credential|key)\.(txt|md|csv|json)$',  # Credential files
            r'(wp-config|htaccess|htpasswd|gitconfig|bashrc|bash_history|ssh/id_rsa)$',  # Common sensitive files
            r'\.(git|svn|hg|bzr)$',  # Version control files
            r'\.(ds_store|idea|vscode)$',  # IDE/OS metadata
            r'~$',  # Tilde backup files
            r'\.(yaml|yml|xml)$'  # Additional config files
        ]

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.domain

    def is_sensitive_file(self, url):
        """Check if URL points to a potentially sensitive file"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check against sensitive patterns
        for pattern in self.sensitive_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        # Check for common sensitive filenames
        sensitive_names = [
            '.htaccess', '.htpasswd', '.env', '.gitignore', 
            'wp-config.php', 'config.php', 'secrets.txt', 
            'credentials.json', 'dockerfile', 'compose.yml',
            'id_rsa', 'id_dsa', 'known_hosts', 'authorized_keys'
        ]
        filename = path.split('/')[-1]
        if filename in sensitive_names:
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
                
                # Handle sensitive files separately
                if self.is_sensitive_file(full_url):
                    if full_url not in self.found_files:
                        self.found_files[full_url] = set()
                    self.found_files[full_url].add(url)
                    print(f"Found sensitive file: {full_url} (on {url})")
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
        if self.found_files:
            print(f"\n------------------ Found {len(self.found_files)} potentially sensitive files ------------------")
            for file_url, source_urls in self.found_files.items():
                print(f"\nSensitive file: {file_url}")
                print(f"Found on {len(source_urls)} pages:")
                for idx, source in enumerate(source_urls, 1):
                    print(f"  {idx}. {source}")
        else:
            print("No sensitive files found.")

if __name__ == "__main__":
    start_url = input("Enter the starting URL (e.g., https://example.com): ").strip()
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    
    max_pages = input("Enter maximum number of pages to scrape (default 50): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else 50
    
    scraper = SensitiveFileScraper(start_url, max_pages)
    scraper.scrape()
