#!/usr/bin/env python3
"""
Golem.de Article Scraper
Downloads articles from Golem.de RSS feeds for offline reading on e-readers.
Requires a valid Golem Plus subscription.
"""

import os
import time
import re
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
from locale import setlocale, LC_TIME

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import requests
from ebooklib import epub
import feedparser

# Set German locale for date formatting
try:
    setlocale(LC_TIME, 'de_DE.UTF-8')
except:
    try:
        setlocale(LC_TIME, 'de_DE')
    except:
        pass  # Keep default if German locale not available


class GolemScraper:
    def __init__(self, download_dir="downloads", profile_dir=None, debug=False):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session = None
        self.cookies = None
        self.profile_dir = Path(profile_dir) if profile_dir else Path(download_dir) / "browser_profile"
        self.profile_dir.mkdir(exist_ok=True)
        self.debug = debug
    
    def format_german_date(self, date_string):
        """
        Convert ISO date string to human-friendly German format.
        Example: "2025-10-29T10:36:01.000Z" -> "29. Oktober 2025, 10:36 Uhr"
        """
        if not date_string:
            return ""
        
        try:
            # Parse ISO format
            if 'T' in date_string:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                # Try parsing as simple date
                dt = datetime.strptime(date_string.split()[0], '%Y-%m-%d')
            
            # Format in German
            # Try to use German month names
            months_de = {
                1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April',
                5: 'Mai', 6: 'Juni', 7: 'Juli', 8: 'August',
                9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
            }
            
            if dt.hour == 0 and dt.minute == 0:
                # Date only
                return f"{dt.day}. {months_de[dt.month]} {dt.year}"
            else:
                # Date and time
                return f"{dt.day}. {months_de[dt.month]} {dt.year}, {dt.hour:02d}:{dt.minute:02d} Uhr"
        except Exception as e:
            if self.debug:
                print(f"  [DEBUG] Could not parse date '{date_string}': {e}")
            return date_string
        
    def login_with_google(self, headless=False):
        """
        Login to Golem.de using Google OAuth.
        Opens a browser window for manual Google authentication.
        Uses a persistent browser profile to avoid Google's automation detection.
        """
        print("Opening browser for Google login...")
        print("Please log in manually when the browser opens.")
        print()
        
        with sync_playwright() as p:
            # Use persistent context to maintain cookies across sessions
            # This also helps avoid Google's automation detection
            context = p.chromium.launch_persistent_context(
                str(self.profile_dir),
                headless=headless,
                channel="chrome",  # Use system Chrome if available
                args=[
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ],
                ignore_default_args=['--enable-automation'],
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.pages[0] if context.pages else context.new_page()
            
            # Check if already logged in
            print("Checking if already logged in...")
            page.goto("https://account.golem.de/user")
            time.sleep(3)
            
            # Check URL and content to determine if logged in
            current_url = page.url
            content = page.content()
            
            # Multiple checks for login status
            is_logged_in = False
            
            # Check 1: If we're on the account page (not redirected to login)
            if "account.golem.de/user" in current_url and "login" not in current_url:
                is_logged_in = True
                print("  ✓ Account page accessible")
            
            # Check 2: Check for logout/account-related elements
            if "logout" in content.lower() or "abmelden" in content.lower():
                is_logged_in = True
                print("  ✓ Found logout link")
            
            # Check 3: Check cookies for session indicators
            cookies = context.cookies()
            cookie_names = [c['name'] for c in cookies]
            
            if self.debug:
                print(f"\n  [DEBUG] Found {len(cookies)} cookies:")
                for cookie in cookies[:10]:  # Show first 10
                    print(f"    - {cookie['name']}: {cookie['value'][:20]}...")
            
            if any('session' in name.lower() or 'auth' in name.lower() for name in cookie_names):
                is_logged_in = True
                print("  ✓ Found session cookies")
            
            # Check 4: Try accessing a Plus article (only if page is still open)
            try:
                test_article = "https://www.golem.de/news/softwareentwicklung-mit-sycl-parallel-programmieren-fuer-fast-jede-plattform-2510-201445.html"
                page.goto(test_article)
                time.sleep(2)
                article_content = page.content()
                
                # Look for paywall indicators
                if "golem pur" in article_content.lower() or "cookies zustimmen" in article_content.lower():
                    # Cookie consent might be needed, but could still be logged in
                    print("  ℹ Cookie consent detected (might need manual acceptance)")
                    if self.debug:
                        print(f"  [DEBUG] Current URL: {page.url}")
                elif "abo" in article_content.lower() and "anmelden" in article_content.lower():
                    # Looks like we need to subscribe/login
                    is_logged_in = False
                    print("  ✗ Paywall detected - not logged in")
                else:
                    # Article seems accessible
                    is_logged_in = True
                    print("  ✓ Article content accessible")
                
                if self.debug:
                    print(f"\n  [DEBUG] Current URL: {current_url}")
                    print(f"  [DEBUG] Page title: {page.title()[:80]}")
                    print(f"  [DEBUG] Content length: {len(article_content)} chars")
            except Exception as e:
                # Page might be closed due to cookie consent, but we have cookies
                if self.debug:
                    print(f"  [DEBUG] Could not check article access: {e}")
                # If we got this far with session cookies, assume logged in
                pass
            
            print(f"\nLogin status: {'✓ LOGGED IN' if is_logged_in else '✗ NOT LOGGED IN'}")
            
            if is_logged_in:
                print("\n✓ Already logged in from previous session!")
                print("Browser will stay open for 5 seconds so you can verify...")
                time.sleep(5)
            else:
                # Navigate to login page
                print("Not logged in yet. Opening login page...")
                page.goto("https://account.golem.de/user/login")
                time.sleep(2)
                
                # Click on "Mit Google anmelden" button
                try:
                    page.click('text="Mit Google anmelden"', timeout=10000)
                    print("Clicked Google login button.")
                    print("\n" + "="*60)
                    print("IMPORTANT: Please complete the Google authentication in the browser.")
                    print("="*60)
                    print("\nTips:")
                    print("- Make sure to allow popups if prompted")
                    print("- If Google blocks login, try clicking 'Try again' or use a different method")
                    print("- After successful login, you'll be redirected back to Golem.de")
                    print("- The browser will close automatically\n")
                except PlaywrightTimeout:
                    print("Google login button not found. Please click it manually in the browser.")
                
                # Wait for user to complete Google OAuth login
                print("Waiting for login to complete (timeout: 3 minutes)...")
                
                try:
                    # Wait for successful redirect back to golem.de domain
                    page.wait_for_url("**/golem.de/**", timeout=180000)
                    time.sleep(3)  # Give extra time for cookies to be set
                    
                    # Verify we're on golem.de
                    page.goto("https://www.golem.de")
                    time.sleep(2)
                    
                    print("✓ Login successful!")
                    
                except PlaywrightTimeout:
                    print("\n✗ Login timeout. The browser will stay open for manual completion.")
                    print("Press Enter after you've logged in successfully...")
                    input()
            
            # Extract cookies for use with requests
            self.cookies = {}
            for cookie in context.cookies():
                self.cookies[cookie['name']] = cookie['value']
            
            # Close browser
            context.close()
            
        # Create a requests session with the cookies
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        return True
    
    def login_with_manual_cookies(self, cookies_file):
        """
        Alternative login method using manually exported cookies from your regular browser.
        
        To export cookies:
        1. Install browser extension like "EditThisCookie" or "Cookie-Editor"
        2. Log in to Golem.de in your regular browser
        3. Export all cookies for golem.de to a JSON file
        4. Pass the file path to this method
        """
        print(f"Loading cookies from: {cookies_file}")
        
        import json
        with open(cookies_file, 'r') as f:
            cookies_data = json.load(f)
        
        self.cookies = {}
        if isinstance(cookies_data, list):
            # Format: [{name: "...", value: "...", domain: "..."}, ...]
            for cookie in cookies_data:
                self.cookies[cookie['name']] = cookie['value']
        elif isinstance(cookies_data, dict):
            # Format: {name: value, name2: value2, ...}
            self.cookies = cookies_data
        
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        print("✓ Cookies loaded successfully")
        return True
    
    def fetch_rss_feed(self, feed_url):
        """
        Fetch and parse RSS/OPML feed to get article URLs.
        """
        print(f"\nFetching RSS feed: {feed_url}")
        
        response = self.session.get(feed_url) if self.session else requests.get(feed_url)
        
        # Check if it's OPML
        if 'opml' in feed_url.lower() or '<opml' in response.text[:200].lower():
            return self.parse_opml(response.text)
        else:
            # Parse as RSS
            feed = feedparser.parse(response.text)
            articles = []
            for entry in feed.entries:
                articles.append({
                    'title': entry.get('title', 'Untitled'),
                    'url': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', '')
                })
            return articles
    
    def parse_opml(self, opml_content):
        """
        Parse OPML to extract article entries.
        Golem's OPML format has articles directly in outline elements, not RSS feeds.
        """
        soup = BeautifulSoup(opml_content, 'xml')
        articles = []
        
        # Find all outline elements - these are individual articles in Golem's OPML
        outlines = soup.find_all('outline')
        
        print(f"Found {len(outlines)} articles in OPML")
        
        for outline in outlines:
            # In Golem's OPML, articles have htmlUrl (article URL) and title
            article_url = outline.get('htmlUrl') or outline.get('url')
            title = outline.get('title') or outline.get('text', 'Untitled')
            
            if article_url:
                articles.append({
                    'title': title,
                    'url': article_url,
                    'published': '',
                    'summary': outline.get('description', '')
                })
        
        print(f"\nTotal articles found: {len(articles)}")
        return articles
    
    def download_article(self, url):
        """
        Download a single article with full content.
        Handles pagination by following 'next' links.
        """
        try:
            all_content_parts = []
            all_images = []
            current_url = url
            page_num = 1
            
            # Extract metadata from first page
            response = self.session.get(current_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else "Untitled"
            
            author = None
            date = None
            
            author_elem = soup.find(class_=re.compile('author|byline'))
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            date_elem = soup.find('time') or soup.find(class_=re.compile('date|published'))
            if date_elem:
                date = date_elem.get('datetime', date_elem.get_text(strip=True))
            
            # Loop through all pages
            visited_urls = set()
            
            while current_url and current_url not in visited_urls:
                visited_urls.add(current_url)
                
                if page_num > 1:
                    print(f"    Downloading page {page_num}...")
                    response = self.session.get(current_url, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article content
                content = soup.find('article') or soup.find('div', class_=re.compile('content|article'))
                
                if not content:
                    # Fallback: try to find main content area
                    content = soup.find('main') or soup.find('div', class_='main')
                
                if not content:
                    print(f"  Warning: Could not find article content for {current_url}")
                    if page_num == 1:
                        return None
                    else:
                        break
                
                # IMPORTANT: Find next page link BEFORE removing nav elements
                next_link = None
                next_button = (
                    soup.find(class_='go-pagination__item--next') or 
                    soup.find(class_='gsnw-link__article-pagination')
                )
                
                if next_button:
                    # Find the link within or as the next button
                    link_elem = next_button.find('a') if next_button.name != 'a' else next_button
                    if link_elem and link_elem.get('href'):
                        next_link = urljoin(current_url, link_elem.get('href'))
                        if self.debug:
                            print(f"    Found next page: {next_link}")
                
                # Now remove unwanted elements (teaser blocks, ads, navigation, buttons, link lists, etc.)
                for unwanted in content.find_all(class_=re.compile('go-teaser-block|advertisement|ad-container|go-button-bar|go-alink-list')):
                    unwanted.decompose()
                
                # Remove nav elements
                for nav in content.find_all('nav'):
                    nav.decompose()
                
                # Cut off content AFTER go-article-end (e.g., comments, related articles)
                article_end = content.find(class_='go-article-end')
                if article_end:
                    # Remove everything after article-end marker (but keep the marker itself)
                    for sibling in list(article_end.find_next_siblings()):
                        sibling.decompose()
                
                # Remove "(öffnet im neuen Fenster)" text from links
                for link in content.find_all('a'):
                    link_text = link.get_text()
                    if '(öffnet im neuen Fenster)' in link_text:
                        # Replace the text without the phrase
                        new_text = link_text.replace('(öffnet im neuen Fenster)', '').strip()
                        link.string = new_text
                
                # Store content from this page
                all_content_parts.append(content)
                
                # Download images from this page
                for img in content.find_all('img'):
                    img_url = img.get('src') or img.get('data-src')
                    if img_url:
                        img_url = urljoin(current_url, img_url)
                        # Avoid downloading duplicate images
                        if not any(i['url'] == img_url for i in all_images):
                            img_data = self.download_image(img_url)
                            if img_data:
                                all_images.append({
                                    'url': img_url,
                                    'data': img_data,
                                    'alt': img.get('alt', ''),
                                    'element': img
                                })
                
                if next_link and next_link not in visited_urls:
                    current_url = next_link
                    page_num += 1
                    time.sleep(1)  # Be polite between page requests
                else:
                    break
            
            if page_num > 1:
                print(f"    ✓ Downloaded {page_num} pages")
            
            # Combine all content parts
            combined_html = ""
            for idx, content_part in enumerate(all_content_parts):
                if idx > 0:
                    combined_html += f"<hr/><p><em>Page {idx + 1}</em></p>"
                combined_html += str(content_part)
            
            return {
                'title': title_text,
                'url': url,
                'author': author,
                'date': date,
                'content': all_content_parts[0],  # Keep first content for processing
                'images': all_images,
                'html': combined_html,
                'pages': page_num
            }
            
        except Exception as e:
            print(f"  Error downloading {url}: {e}")
            return None
    
    def download_image(self, img_url):
        """
        Download an image and return its binary data.
        """
        try:
            response = self.session.get(img_url, timeout=15)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"    Error downloading image {img_url}: {e}")
            return None
    
    def create_epub(self, articles, output_filename, topic=None):
        """
        Create an EPUB file from downloaded articles.
        """
        print(f"\nCreating EPUB: {output_filename}")
        
        book = epub.EpubBook()
        
        # Set metadata
        book.set_identifier(f'golem-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
        topic_title = f' - {topic.title()}' if topic else ''
        book.set_title(f'Golem.de{topic_title} Articles')
        book.set_language('de')
        book.add_author('Golem.de')
        
        chapters = []
        
        for idx, article in enumerate(articles, 1):
            if not article:
                continue
            
            print(f"  Adding article {idx}/{len(articles)}: {article['title'][:50]}...")
            
            # Create chapter
            chapter = epub.EpubHtml(
                title=article['title'],
                file_name=f'chapter_{idx}.xhtml',
                lang='de'
            )
            
            # Build chapter content - start directly with article (no metadata header)
            # Add page break before each article (except the first one)
            content_html = ""
            
            # Add article content directly (which includes its own header)
            soup = BeautifulSoup(article['html'], 'html.parser')
            
            # Process images - find all img tags and update their sources
            img_tags = soup.find_all('img')
            img_map = {img_info['url']: img_info for img_info in article.get('images', [])}
            
            for img_tag in img_tags:
                # Get original URL
                original_url = img_tag.get('src') or img_tag.get('data-src')
                if original_url:
                    # Make it absolute if relative
                    absolute_url = urljoin(article['url'], original_url)
                    
                    # Find corresponding downloaded image
                    if absolute_url in img_map:
                        img_info = img_map[absolute_url]
                        
                        # Create an EpubImage for each image
                        img_ext = os.path.splitext(urlparse(img_info['url']).path)[1] or '.jpg'
                        img_filename = f"image_{idx}_{len([i for i in book.items if hasattr(i, 'file_name') and 'images/' in i.file_name])}{img_ext}"
                        
                        epub_image = epub.EpubImage()
                        epub_image.file_name = f"images/{img_filename}"
                        epub_image.content = img_info['data']
                        book.add_item(epub_image)
                        
                        # Update img src in content
                        img_tag['src'] = f"images/{img_filename}"
                        # Remove data-src if present
                        if img_tag.get('data-src'):
                            del img_tag['data-src']
            
            content_html += str(soup)
            
            # Add source link at the end of the article
            content_html += f'''
            <div style="margin-top: 3em; padding-top: 1em; border-top: 1px solid #ddd; font-size: 0.85em; color: #666;">
                <p><strong>Quelle:</strong> <a href="{article['url']}">{article['url']}</a></p>
            </div>
            '''
            
            chapter.content = content_html
            book.add_item(chapter)
            chapters.append(chapter)
                    
        # Add navigation
        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
                
        # Create spine
        book.spine = ['nav'] + chapters
        
        # Write EPUB file
        output_path = self.download_dir / output_filename
        epub.write_epub(output_path, book)
        
        print(f"✓ EPUB created: {output_path}")
        return output_path
    
    def scrape_feed(self, feed_url, output_filename=None, max_articles=None, topic=None):
        """
        Main method to scrape all articles from a feed.
        """
        # Fetch article list from feed
        articles_meta = self.fetch_rss_feed(feed_url)
        
        if max_articles:
            articles_meta = articles_meta[:max_articles]
        
        print(f"\nDownloading {len(articles_meta)} articles...")
        
        # Download each article
        articles_data = []
        for idx, article_meta in enumerate(articles_meta, 1):
            print(f"\n[{idx}/{len(articles_meta)}] {article_meta['title']}")
            print(f"  URL: {article_meta['url']}")
            
            article_data = self.download_article(article_meta['url'])
            if article_data:
                articles_data.append(article_data)
                print("  ✓ Downloaded")
            
            # Be polite - add delay between requests
            time.sleep(2)
        
        # Create EPUB
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_part = f"_{topic}" if topic else ""
            output_filename = f"golem{topic_part}_{timestamp}.epub"
        
        if articles_data:
            self.create_epub(articles_data, output_filename, topic=topic)
            print(f"\n✓ Successfully downloaded {len(articles_data)} articles")
        else:
            print("\n✗ No articles were downloaded")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape articles from Golem.de for offline reading',
        epilog='Examples:\n'
               '  %(prog)s security -n 10              # Download 10 security articles\n'
               '  %(prog)s                              # Download softwareentwicklung (default)\n'
               '  %(prog)s -o custom.epub               # Custom output filename\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'topic',
        nargs='?',
        default='softwareentwicklung',
        help='Topic to download (e.g., security, softwareentwicklung, ki). Default: softwareentwicklung'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output EPUB filename (default: golem_{topic}_{timestamp}.epub)',
        default=None
    )
    parser.add_argument(
        '-d', '--download-dir',
        help='Download directory',
        default='downloads'
    )
    parser.add_argument(
        '-n', '--max-articles',
        type=int,
        help='Maximum number of articles to download (default: 10)',
        default=1
    )
    parser.add_argument(
        '--no-login',
        action='store_true',
        help='Skip login (for public articles only)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (invisible, for automation)'
    )
    parser.add_argument(
        '--cookies',
        help='Path to JSON file with cookies from your browser (alternative to automated login)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output (shows cookies, page content snippets, etc.)'
    )
    
    args = parser.parse_args()
    
    # Construct feed URL from topic
    feed_url = f'https://rss.golem.de/rss.php?ms={args.topic}'
    
    scraper = GolemScraper(download_dir=args.download_dir, debug=args.debug)
    
    if not args.no_login:
        print("Golem.de Article Scraper")
        print("=" * 50)
        
        if args.cookies:
            # Use manual cookies file
            print("\nLoading cookies from file...")
            if not scraper.login_with_manual_cookies(args.cookies):
                print("Failed to load cookies. Exiting.")
                return 1
        else:
            # Use automated browser login
            print("\nThis tool will open a browser for Google login.")
            print("Please log in with your Golem Plus account.")
            print()
            
            if not scraper.login_with_google(headless=args.headless):
              print("Login failed. Exiting.")
              return 1
    
    # Scrape articles
    scraper.scrape_feed(
        feed_url,
        output_filename=args.output,
        max_articles=args.max_articles,
        topic=args.topic
    )
    
    print("\n✓ Done!")
    return 0


if __name__ == '__main__':
    exit(main())

