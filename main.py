import requests
from bs4 import BeautifulSoup
import csv
import tldextract
from urllib.parse import urljoin, urlparse
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from websites import websites

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrivacyPolicyScraper:
    def __init__(self, max_workers=5, delay_range=(1, 3)):
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def normalize_url(self, url):
        """Ensure URL has proper scheme"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def find_privacy_policy_url(self, base_url):
        """Find privacy policy URL with multiple strategies"""
        try:
            base_url = self.normalize_url(base_url)
            response = self.session.get(base_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Strategy 1: Look for common privacy policy patterns
            privacy_patterns = [
                r'privacy[_-]?policy',
                r'privacy[_-]?statement',
                r'privacy[_-]?notice',
                r'data[_-]?protection',
                r'privacy',
                r'legal/privacy',
                r'about/privacy',
                r'support/privacy'
            ]
            
            # Check all links
            for a in soup.find_all("a", href=True):
                href = a['href'].lower()
                text = a.get_text(strip=True).lower()
                
                # Check href and text for privacy patterns
                for pattern in privacy_patterns:
                    if re.search(pattern, href) or re.search(pattern, text):
                        full_url = urljoin(base_url, a['href'])
                        logger.info(f"Found privacy policy link: {full_url}")
                        return full_url
            
            # Strategy 2: Try common privacy policy URLs
            common_paths = [
                '/privacy-policy',
                '/privacy',
                '/privacy-statement',
                '/privacy-notice',
                '/legal/privacy',
                '/about/privacy',
                '/support/privacy',
                '/privacy.html',
                '/privacy.php',
                '/terms-and-privacy',
                '/legal/privacy-policy'
            ]
            
            for path in common_paths:
                test_url = urljoin(base_url, path)
                try:
                    test_response = self.session.head(test_url, timeout=10)
                    if test_response.status_code == 200:
                        logger.info(f"Found privacy policy at common path: {test_url}")
                        return test_url
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding privacy policy for {base_url}: {str(e)}")
            return None
        
        return None
    
    def get_policy_text(self, url):
        """Extract text from privacy policy page with improved content detection"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove unwanted elements
            for elem in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
                elem.decompose()
            
            # Strategy 1: Look for main content containers
            content_selectors = [
                'main',
                '[role="main"]',
                '.main-content',
                '.content',
                '.policy-content',
                '.privacy-policy',
                '.legal-content',
                'article',
                '.container'
            ]
            
            content_text = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(separator='\n', strip=True)
                        if len(text) > len(content_text):
                            content_text = text
                    break
            
            # Strategy 2: If no main content found, get all relevant text elements
            if not content_text:
                text_elements = soup.find_all([
                    "p", "div", "span", "article", "section", 
                    "h1", "h2", "h3", "h4", "h5", "h6", "li"
                ])
                content_text = "\n".join(elem.get_text(strip=True) for elem in text_elements if elem.get_text(strip=True))
            
            # Clean up the text
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)  # Remove excessive newlines
            content_text = re.sub(r'\s+', ' ', content_text)  # Normalize spaces
            
            # Limit to reasonable size but increase from 10k to 50k chars for better coverage
            if len(content_text) > 50000:
                content_text = content_text[:50000] + "... [Content truncated]"
            
            logger.info(f"Extracted {len(content_text)} characters from {url}")
            return content_text
            
        except Exception as e:
            logger.error(f"Error extracting text from {url}: {str(e)}")
            return None
    
    def scrape_single_site(self, site):
        """Scrape privacy policy for a single site"""
        try:
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(*self.delay_range))
            
            company = tldextract.extract(site).domain.capitalize()
            logger.info(f"🔍 Checking {company} ({site})")
            
            policy_url = self.find_privacy_policy_url(site)
            if policy_url:
                logger.info(f" ✅ Found policy link: {policy_url}")
                text = self.get_policy_text(policy_url)
                if text and len(text.strip()) > 100:  # Ensure we have meaningful content
                    return {
                        'company': company,
                        'site': site,
                        'policy_url': policy_url,
                        'text': text,
                        'status': 'success'
                    }
                else:
                    logger.warning(f" ⚠️ Could not extract meaningful text from {policy_url}")
                    return {
                        'company': company,
                        'site': site,
                        'policy_url': policy_url,
                        'text': '',
                        'status': 'text_extraction_failed'
                    }
            else:
                logger.warning(f" ❌ Privacy policy not found on {site}")
                return {
                    'company': company,
                    'site': site,
                    'policy_url': '',
                    'text': '',
                    'status': 'policy_not_found'
                }
                
        except Exception as e:
            logger.error(f"Error processing {site}: {str(e)}")
            return {
                'company': tldextract.extract(site).domain.capitalize(),
                'site': site,
                'policy_url': '',
                'text': '',
                'status': f'error: {str(e)}'
            }
    
    def scrape_privacy_policies(self):
        """Main scraping function with concurrent processing"""
        results = []
        successful_scrapes = 0
        
        logger.info(f"Starting to scrape {len(websites)} websites...")
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_site = {executor.submit(self.scrape_single_site, site): site for site in websites}
            
            # Process completed tasks
            for future in as_completed(future_to_site):
                site = future_to_site[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result['status'] == 'success':
                        successful_scrapes += 1
                        logger.info(f"✅ Successfully scraped {result['company']}")
                    else:
                        logger.warning(f"⚠️ Failed to scrape {result['company']}: {result['status']}")
                except Exception as e:
                    logger.error(f"Error processing {site}: {str(e)}")
                    results.append({
                        'company': tldextract.extract(site).domain.capitalize(),
                        'site': site,
                        'policy_url': '',
                        'text': '',
                        'status': f'exception: {str(e)}'
                    })
        
        # Save results to CSV
        self.save_results(results)
        
        # Print summary
        logger.info(f"\n📊 SCRAPING SUMMARY:")
        logger.info(f"Total websites: {len(websites)}")
        logger.info(f"Successful scrapes: {successful_scrapes}")
        logger.info(f"Failed scrapes: {len(websites) - successful_scrapes}")
        logger.info(f"Success rate: {(successful_scrapes/len(websites)*100):.1f}%")
        
        return results
    
    def save_results(self, results):
        """Save results to CSV with additional metadata"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"privacy_policies_{timestamp}.csv"
        
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Company", 
                "Website", 
                "Privacy Policy URL", 
                "Text", 
                "Status",
                "Text Length",
                "Scrape Timestamp"
            ])
            
            for result in results:
                writer.writerow([
                    result['company'],
                    result['site'],
                    result['policy_url'],
                    result['text'],
                    result['status'],
                    len(result['text']),
                    time.strftime("%Y-%m-%d %H:%M:%S")
                ])
        
        logger.info(f"✅ Results saved to {filename}")
        
        # Also save a summary CSV
        summary_filename = f"privacy_policies_summary_{timestamp}.csv"
        with open(summary_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Website", "Privacy Policy URL", "Status", "Text Length"])
            
            for result in results:
                writer.writerow([
                    result['company'],
                    result['site'],
                    result['policy_url'],
                    result['status'],
                    len(result['text'])
                ])
        
        logger.info(f"✅ Summary saved to {summary_filename}")

def main():
    """Main function to run the scraper"""
    scraper = PrivacyPolicyScraper(max_workers=3, delay_range=(1, 2))
    results = scraper.scrape_privacy_policies()
    
    # Optional: Save failed sites for retry
    failed_sites = [r for r in results if r['status'] != 'success']
    if failed_sites:
        logger.info(f"\n📝 {len(failed_sites)} sites failed. Consider retrying these manually.")
        for site in failed_sites:
            logger.info(f"  - {site['company']} ({site['site']}): {site['status']}")

if __name__ == "__main__":
    main()