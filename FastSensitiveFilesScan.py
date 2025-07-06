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
        self.found_files = {}
        
        # Common file extensions
        self.file_extensions = {
            # Documents
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.rtf', '.txt', 
            '.odt', '.ods', '.odp', '.tex', '.log', '.csv', '.accd', '.accdb',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.psd', '.ai', '.svg', '.raw', '.cr2', '.nef',
            # Audio
            '.mp3', '.wav', '.flac', '.midi', '.ogg',
            # Video
            '.avi', '.mov', '.mp4', '.mpeg', '.mpeg2', '.mpeg3', '.mpg', '.mkv', '.flv', '.3gp', '.m4v', '.wmv',
            # Archives & Backups
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bak', '.backup', '.wbcat',
            # Code & Developer Files
            '.py', '.html', '.htm', '.php', '.js', '.css', '.cpp', '.c', '.java', 
            '.cs', '.vb', '.asp', '.aspx', '.cgi', '.pl', '.sh', '.ps1',
            # Databases
            '.sql', '.db', '.dbf', '.mdb', '.accdb', '.accd', '.kdbx'
        }
        
        # Sensitive file patterns (both extensions and filenames)
        self.sensitive_patterns = {
            # Configuration files
            '.env', '.htaccess', '.htpasswd', '.conf', '.config', '.yml', '.yaml', 
            '.ini', '.cfg', '.properties', '.gitignore', '.gitconfig',
            # Security files
            'id_rsa', 'id_dsa', '.pem', '.key', '.kdbx', 'oauth', 'token',
            # Backup files
            '.bak', '.backup', '.swp', '.swo', '~',
            # Log files
            '.log', 'error.log',
            # Database files
            '.sql', '.dump', '.db', '.mdb',
            # History files
            '.bash_history', '.zsh_history', '_history',
            # Server files
            'php.ini', 'web.config', 'robots.txt',
            # Dependency files
            'package-lock.json', 'yarn.lock', 'pipfile.lock', 'requirements.txt'
        }

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.domain

    def is_sensitive_file(self, url):
        """Check if URL points to a sensitive file"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        basename = path.split('/')[-1]  # Get filename only
        
        # Check by file extension
        if '.' in basename:
            ext = '.' + basename.split('.')[-1]
            if ext in self.file_extensions:
                return True
        
        # Check by sensitive filename patterns
        for pattern in self.sensitive_patterns:
            if pattern in basename:
                return True
        
        # Check common sensitive filenames without extensions
        sensitive_names = {
            'env', 'htaccess', 'htpasswd', 'id_rsa', 'id_dsa', 'oauth', 'token',
            'robots', 'phpinfo', 'web', 'gitignore', 'bash_history'
        }
        if basename in sensitive_names:
            return True
            
        return False

    def get_all_links(self, url):
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                
                if self.is_sensitive_file(full_url):
                    if full_url not in self.found_files:
                        self.found_files[full_url] = set()
                    self.found_files[full_url].add(url)
                    print(f"Found sensitive file: {full_url} (on {url})")
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
            print(f"\nFound {len(self.found_files)} sensitive files:")
            for file_url, source_urls in self.found_files.items():
                print(f"\nFile: {file_url}")
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
