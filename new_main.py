import requests
from bs4 import BeautifulSoup
import csv
import tldextract
from urllib.parse import urljoin
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from websites import websites  # List of domains

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrivacyPolicyScraper:
    def __init__(self, max_workers=5, delay_range=(1, 3), output_prefix="privacy_policies"):
        self.session = self._init_session()
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.output_prefix = output_prefix

    def _init_session(self):
        """Initialize session with headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        return session

    @staticmethod
    def normalize_url(url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url

    def find_policy_url(self, base_url):
        base_url = self.normalize_url(base_url)
        try:
            res = self.session.get(base_url, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # First strategy: anchor text
            patterns = [r'privacy', r'data[_-]?protection', r'legal/privacy']
            for a in soup.find_all("a", href=True):
                href = a['href'].lower()
                text = a.get_text(strip=True).lower()
                if any(re.search(pat, href) or re.search(pat, text) for pat in patterns):
                    return urljoin(base_url, a['href'])

            # Fallback strategy: guess common paths
            fallback_paths = [
                "/privacy", "/privacy-policy", "/legal/privacy",
                "/privacy.html", "/privacy.php"
            ]
            for path in fallback_paths:
                full_url = urljoin(base_url, path)
                try:
                    head = self.session.head(full_url, timeout=5)
                    if head.status_code == 200:
                        return full_url
                except: continue

        except Exception as e:
            logger.warning(f"Failed to resolve {base_url}: {e}")
        return None

    def extract_policy_text(self, url):
        try:
            res = self.session.get(url, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            selectors = ['main', '[role="main"]', '.content', '.policy-content', 'article']
            content = ""
            for sel in selectors:
                elements = soup.select(sel)
                for el in elements:
                    text = el.get_text(separator="\n", strip=True)
                    if len(text) > len(content):
                        content = text
                if content:
                    break

            if not content:
                text_elements = soup.find_all(["p", "div", "span", "section"])
                content = "\n".join(e.get_text(strip=True) for e in text_elements if e.get_text(strip=True))

            cleaned = re.sub(r'\n{2,}', '\n\n', content).strip()
            return cleaned[:50000] + ("... [Truncated]" if len(cleaned) > 50000 else "")
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None

    def scrape_site(self, site):
        time.sleep(random.uniform(*self.delay_range))
        domain = tldextract.extract(site).domain.capitalize()

        try:
            logger.info(f"🔍 Processing {domain}")
            policy_url = self.find_policy_url(site)
            if not policy_url:
                return self._result(domain, site, '', '', 'not_found')

            text = self.extract_policy_text(policy_url)
            if not text or len(text.strip()) < 100:
                return self._result(domain, site, policy_url, '', 'text_too_short')

            return self._result(domain, site, policy_url, text, 'success')

        except Exception as e:
            logger.error(f"Exception while scraping {site}: {e}")
            return self._result(domain, site, '', '', f'error: {str(e)}')

    @staticmethod
    def _result(company, site, url, text, status):
        return {
            "company": company,
            "site": site,
            "policy_url": url,
            "text": text,
            "status": status
        }

    def scrape_all(self, sites):
        logger.info(f"🚀 Scraping {len(sites)} sites...")
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.scrape_site, site): site for site in sites}
            for future in as_completed(futures):
                results.append(future.result())

        self.save_csv(results)
        return results

    def save_csv(self, results):
        full_path = f"{self.output_prefix}.csv"
        summary_path = f"{self.output_prefix}_summary.csv"

        with open(full_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Website", "Privacy Policy URL", "Text", "Status", "Text Length"])
            for r in results:
                writer.writerow([r['company'], r['site'], r['policy_url'], r['text'], r['status'], len(r['text'])])

        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Website", "URL", "Status"])
            for r in results:
                writer.writerow([r['company'], r['site'], r['policy_url'], r['status']])

        logger.info(f"✅ Full CSV: {full_path}")
        logger.info(f"📋 Summary CSV: {summary_path}")


# Entrypoint
if __name__ == "__main__":
    scraper = PrivacyPolicyScraper(max_workers=4, delay_range=(1, 2))
    scraper.scrape_all(websites)
