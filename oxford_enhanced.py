import fitz  # PyMuPDF
import requests
from tqdm import tqdm
from Crypto.Cipher import AES
from dataclasses import dataclass
from bs4 import BeautifulSoup
from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import unpad
import base64
import os, re
import urllib3
import time
import json
import asyncio

# Playwright imports for modern web automation
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
    print("[+] Playwright available for modern web automation")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[!] Playwright not available, install with: pip install playwright && playwright install chromium")

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def sanitize_filename(filename):
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', filename)

@dataclass
class Book:
    title: str
    pages: int
    description: str
    author: str
    isbn: str

class Oxford:
    def __init__(self, ebook_id=None):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        self.encryption_key = ""
        self.ebook_id = ebook_id
        self.logged_in = False
        self.playwright = None
        self.browser = None
        self.page = None
        
    async def check_login_status(self):
        """Check if already logged in by looking for dashboard elements"""
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Navigate to bookshelf URL
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf: {await self.page.title()}")
            
            # Wait for page to load
            await self.page.wait_for_timeout(3000)
            
            # Check if we're already logged in by looking for dashboard/bookshelf elements
            login_indicators = [
                'input[name="username"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="username" i]'
            ]
            
            dashboard_indicators = [
                '.bookshelf',
                '.dashboard',
                '.collection',
                '[class*="book"]',
                '[class*="shelf"]',
                '.bookThumbnailImages',
                '.collectionTitle'
            ]
            
            # Check for login form
            is_login_page = False
            for selector in login_indicators:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    is_login_page = True
                    print(f"[+] Found login form - need to login")
                    break
                except:
                    continue
            
            # Check for dashboard
            is_dashboard = False
            if not is_login_page:
                for selector in dashboard_indicators:
                    try:
                        await self.page.wait_for_selector(selector, timeout=2000)
                        is_dashboard = True
                        print(f"[+] Found dashboard - already logged in!")
                        break
                    except:
                        continue
            
            if is_dashboard:
                # Extract cookies from already logged in session
                cookies = await self.page.context.cookies()
                cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                
                # Save cookies to file
                with open('cookies.txt', 'w') as f:
                    f.write(cookie_string)
                print(f"[+] Session cookies saved to cookies.txt")
                
                # Update requests session
                self.session.headers.update({'Cookie': cookie_string})
                self.logged_in = True
                
                # Take screenshot for verification
                await self.page.screenshot(path="dashboard.png")
                print("[+] Dashboard screenshot saved as dashboard.png")
                
                return True
            else:
                print("[!] Need to login - login form detected")
                return False
                
        except Exception as e:
            print(f"[!] Error checking login status: {e}")
            return False
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

    async def login_with_playwright(self, username="gopalprasadpatel@gmail.com", password="London@12"):
        """Use Playwright for modern web automation login"""
        if not PLAYWRIGHT_AVAILABLE:
            print("[!] Playwright not available, falling back to requests-only login")
            return False
        
        # First check if already logged in
        if await self.check_login_status():
            return True
        
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)  # Set to False for debugging
            self.page = await self.browser.new_page()
            
            print("[+] Playwright browser initialized")
            
            # Navigate to bookshelf URL
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf: {await self.page.title()}")
            
            # Wait a bit for any redirects
            await self.page.wait_for_timeout(3000)
            
            # Take screenshot for debugging
            await self.page.screenshot(path="login_page.png")
            print("[+] Screenshot saved as login_page.png")
            
            # Try multiple login form selectors
            login_selectors = [
                'input[name="username"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="username" i]',
                'input[id*="email" i]',
                'input[id*="username" i]',
                'input.form-control[type="email"]',
                'input.form-control[type="text"]'
            ]
            
            username_field = None
            for selector in login_selectors:
                try:
                    username_field = await self.page.wait_for_selector(selector, timeout=2000)
                    if username_field:
                        print(f"[+] Found username field with selector: {selector}")
                        break
                except:
                    continue
            
            if not username_field:
                print("[!] Could not find username/email field")
                # Print page content for debugging
                page_content = await self.page.content()
                print(f"[+] Page content length: {len(page_content)}")
                return False
            
            # Fill username field
            await username_field.fill(username)
            print("[+] Username field filled")
            
            # Find password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password" i]',
                'input[id*="password" i]',
                'input.form-control[type="password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = await self.page.wait_for_selector(selector, timeout=2000)
                    if password_field:
                        print(f"[+] Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                print("[!] Could not find password field")
                return False
            
            # Fill password field
            await password_field.fill(password)
            print("[+] Password field filled")
            
            # Find and click login button
            login_button_selectors = [
                'button[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
                'input[type="submit"]',
                'button.login-btn',
                'button.btn-primary',
                '.login-button',
                '[onclick*="login" i]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if login_button:
                        print(f"[+] Found login button with selector: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                print("[!] Could not find login button")
                return False
            
            await login_button.click()
            print("[+] Login button clicked")
            
            # Wait for login to complete
            await self.page.wait_for_timeout(5000)
            
            # Check if login was successful by looking for bookshelf elements
            success_indicators = [
                '.bookshelf',
                '.dashboard',
                '.collection',
                '[class*="book"]',
                '[class*="shelf"]'
            ]
            
            login_success = False
            for indicator in success_indicators:
                try:
                    await self.page.wait_for_selector(indicator, timeout=3000)
                    login_success = True
                    print(f"[+] Login successful - found {indicator}")
                    break
                except:
                    continue
            
            if not login_success:
                print("[!] Login may have failed - no success indicators found")
                # Take screenshot for debugging
                await self.page.screenshot(path="after_login.png")
                return False
            
            # Extract cookies from Playwright
            cookies = await self.page.context.cookies()
            cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            
            # Save cookies to file
            with open('cookies.txt', 'w') as f:
                f.write(cookie_string)
            print(f"[+] Playwright cookies saved to cookies.txt")
            
            # Update requests session with Playwright cookies
            self.session.headers.update({'Cookie': cookie_string})
            self.logged_in = True
            
            return True
            
        except Exception as e:
            print(f"[!] Playwright login failed: {e}")
            return False
        finally:
            # Keep browser open for debugging if login failed
            if self.logged_in and self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def find_class5_books(self):
        """Find all Class 5 ebooks from the bookshelf"""
        if not self.logged_in:
            print("[!] Please login first")
            return []
        
        try:
            # Reinitialize Playwright for book discovery
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Load cookies from file
            with open('cookies.txt', 'r') as f:
                cookie_string = f.read().strip()
            
            cookies = []
            for cookie in cookie_string.split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies.append({
                        'name': name.strip(), 
                        'value': value.strip(), 
                        'domain': '.oxfordeducate.in',
                        'path': '/'
                    })
            
            await self.page.context.add_cookies(cookies)
            
            # Navigate to bookshelf
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            
            # Wait for page to load
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot for debugging
            await self.page.screenshot(path="bookshelf.png")
            print("[+] Bookshelf screenshot saved as bookshelf.png")
            
            # Find all books with "5" in title using multiple approaches
            class5_books = []
            
            # Try different selectors for book titles
            title_selectors = [
                '[class*="title"]',
                '[class*="Title"]',
                '.bookTitle',
                '.book-title',
                'h1', 'h2', 'h3', 'h4',
                '[ng-bind*="title"]',
                '[data-title]',
                '.shelf-title',
                '.collection-title'
            ]
            
            all_elements = []
            for selector in title_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    all_elements.extend(elements)
                except:
                    continue
            
            # Also try to find any text containing "5"
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Find all elements containing "5"
            for element in soup.find_all(text=lambda text: text and '5' in str(text)):
                parent = element.parent
                if parent and parent.get_text().strip():
                    text = parent.get_text().strip()
                    if '5' in text and len(text) < 200:  # Reasonable length
                        print(f"[+] Found potential book title: {text}")
                        
                        # Try to find clickable parent
                        clickable_parent = parent
                        while clickable_parent and clickable_parent.name not in ['a', 'button', 'div', 'section']:
                            clickable_parent = clickable_parent.parent
                        
                        if clickable_parent:
                            # Get CSS selector or XPath
                            element_text = await self.page.evaluate('''
                                (text) => {
                                    const elements = document.querySelectorAll('*');
                                    for (let el of elements) {
                                        if (el.textContent && el.textContent.includes(text)) {
                                            return el.tagName + (el.className ? '.' + el.className.split(' ').join('.') : '');
                                        }
                                    }
                                    return null;
                                }
                            ''', text)
                            
                            book_info = {
                                'title': text,
                                'element_text': element_text,
                                'parent_tag': clickable_parent.name if clickable_parent else 'unknown'
                            }
                            class5_books.append(book_info)
            
            # Alternative: Use Playwright to find elements with text containing "5"
            try:
                elements_with_5 = await self.page.query_selector_all('text=/5/')
                for element in elements_with_5:
                    text = await element.text_content()
                    if text and '5' in text and len(text.strip()) < 200:
                        parent = await element.evaluate('el => el.parentElement')
                        if parent:
                            class5_books.append({
                                'title': text.strip(),
                                'element': parent,
                                'type': 'text_node'
                            })
            except:
                pass
            
            # Remove duplicates
            unique_books = []
            seen_titles = set()
            for book in class5_books:
                title = book['title'].strip()
                if title not in seen_titles:
                    unique_books.append(book)
                    seen_titles.add(title)
            
            class5_books = unique_books
            
            print(f"[+] Found {len(class5_books)} Class 5 books:")
            for i, book in enumerate(class5_books, 1):
                print(f"    {i}. {book['title']}")
            
            return class5_books
            
        except Exception as e:
            print(f"[!] Error finding Class 5 books: {e}")
            return []
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def get_book_collection(self, book_element):
        """Click on a book and get its collection (24 items)"""
        try:
            # Reinitialize Playwright for collection access
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            
            # Load cookies
            with open('cookies.txt', 'r') as f:
                cookie_string = f.read().strip()
            
            cookies = []
            for cookie in cookie_string.split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies.append({'name': name.strip(), 'value': value.strip(), 'domain': '.oxfordeducate.in'})
            
            await self.page.context.add_cookies(cookies)
            
            # Navigate to bookshelf
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            
            # Click on the book to open collection
            await book_element.click()
            print("[+] Book clicked, waiting for collection to load...")
            
            # Wait for collection view to appear
            await self.page.wait_for_selector('.allCategoeryCollectionView, .collection, .bookThumbnailImages', timeout=10000)
            
            # Extract collection information
            collection_info = await self.page.evaluate('''
                () => {
                    const collectionDiv = document.querySelector('.allCategoeryCollectionView');
                    if (!collectionDiv) return null;
                    
                    const titleElement = collectionDiv.querySelector('.collectionTitle');
                    const itemsElement = collectionDiv.querySelector('.totalItems');
                    const bookElements = collectionDiv.querySelectorAll('.collectionBookContainer');
                    
                    const books = [];
                    bookElements.forEach((bookEl, index) => {
                        const titleEl = bookEl.querySelector('.bookTitleText');
                        const imgEl = bookEl.querySelector('.bookThumbnailImages');
                        const typeEl = bookEl.querySelector('.bookType');
                        
                        if (titleEl && imgEl) {
                            books.push({
                                index: index,
                                title: titleEl.textContent.trim(),
                                ariaLabel: imgEl.getAttribute('aria-label'),
                                type: typeEl ? typeEl.textContent.trim() : 'CHAPTER',
                                onclick: imgEl.getAttribute('onclick'),
                                ngClick: imgEl.getAttribute('ng-click')
                            });
                        }
                    });
                    
                    return {
                        title: titleElement ? titleElement.textContent.trim() : 'Unknown',
                        totalItems: itemsElement ? itemsElement.textContent.trim() : '0',
                        books: books
                    };
                }
            ''')
            
            if collection_info:
                print(f"[+] Collection found: {collection_info['title']}")
                print(f"[+] Total items: {collection_info['totalItems']}")
                print(f"[+] Found {len(collection_info['books'])} books in collection")
                
                return collection_info
            else:
                print("[!] No collection found")
                return None
                
        except Exception as e:
            print(f"[!] Error getting book collection: {e}")
            return None
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def get_book_id_from_toc(self, book_info):
        """Click on a book item and get its ID from toc.xml response"""
        try:
            # Reinitialize Playwright for individual book access
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            
            # Set up response interceptor to capture toc.xml request
            toc_data = {}
            
            async def handle_response(response):
                if 'toc.xml' in response.url:
                    print(f"[+] Intercepted toc.xml: {response.url}")
                    
                    # Extract book ID from URL
                    book_id_match = re.search(r'/s3view/(\d+)/html5/', response.url)
                    if book_id_match:
                        book_id = book_id_match.group(1)
                        toc_data['book_id'] = book_id
                        
                        # Get cookies from response headers
                        cookies = response.headers.get('set-cookie', '')
                        toc_data['cookies'] = cookies
                        
                        print(f"[+] Found book ID: {book_id}")
                    toc_data['status'] = response.status
            
            self.page.on('response', handle_response)
            
            # Load cookies
            with open('cookies.txt', 'r') as f:
                cookie_string = f.read().strip()
            
            cookies = []
            for cookie in cookie_string.split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookies.append({'name': name.strip(), 'value': value.strip(), 'domain': '.oxfordeducate.in'})
            
            await self.page.context.add_cookies(cookies)
            
            # Navigate to bookshelf
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            
            # Find and click on the specific book
            book_selector = f'[aria-label="{book_info["ariaLabel"]}"]'
            await self.page.wait_for_selector(book_selector, timeout=10000)
            await self.page.click(book_selector)
            print(f"[+] Clicked on book: {book_info['title']}")
            
            # Wait for toc.xml request to be intercepted
            await self.page.wait_for_timeout(5000)  # Wait 5 seconds for request
            
            if 'book_id' in toc_data:
                # Update cookies with new session data
                if 'cookies' in toc_data and toc_data['cookies']:
                    # Parse and update cookies
                    new_cookies = toc_data['cookies']
                    with open('cookies.txt', 'w') as f:
                        f.write(cookie_string + '; ' + new_cookies)
                    
                    self.session.headers.update({'Cookie': cookie_string + '; ' + new_cookies})
                
                return toc_data['book_id']
            else:
                print(f"[!] Could not get book ID for: {book_info['title']}")
                return None
                
        except Exception as e:
            print(f"[!] Error getting book ID: {e}")
            return None
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    def get_encryption_key(self, book_id):
        """Get encryption key from the book preview page"""
        preview_url = f"https://www.oxfordeducate.in/reader/oupindia/#/book/{book_id}"
        response = self.session.get(preview_url)
        
        if response.status_code == 200:
            # Look for encryption key in JavaScript
            key_match = re.search(r'window\.angularComponentRef\.render\.settings\.encResource\s*=\s*["\']([^"\']+)["\']', 
                                response.text)
            if key_match:
                self.encryption_key = key_match.group(1)
                print(f"[+] Found encryption key: {self.encryption_key[:10]}...")
                return True
        
        print(f"[!] Could not find encryption key for book {book_id}")
        return False

    def download_book_item(self, book_id, item_title):
        """Download a single book item"""
        try:
            self.ebook_id = book_id
            
            # Get encryption key
            if not self.get_encryption_key(book_id):
                print(f"[!] Could not get encryption key for {item_title}")
                return None
            
            # Get book metadata
            response = self.session.get(f'https://www.oxfordeducate.in/ContentServer/mvc/s3view/{book_id}/html5/{book_id}/OPS/content.opf')
            soup = BeautifulSoup(response.text, 'lxml')
            
            book = Book(
                title=soup.find('dc:title').text if soup.find('dc:title') else item_title,
                pages=int(soup.select('itemref')[-1]['idref'].removeprefix('page')) if soup.select('itemref') else 0,
                description=soup.find('dc:description').text if soup.find('dc:description') else '',
                author=soup.find('dc:author').text if soup.find('dc:author') else '',
                isbn=soup.find('dc:identifier').text.split(':')[2] if soup.find('dc:identifier') else ''
            )
            
            print(f"[+] Downloading: {book.title} ({book.pages} pages)")
            
            # Get image items
            items = {}
            for item in soup.find_all('item'):
                media_type = item.get('media-type')
                if media_type in ['image/svg+xml', 'image/png', 'image/jpeg']:
                    items[item.get('id')] = item.get('href')
            
            # Create PDF for this item
            pdf_file = fitz.Document()
            itemrefs = soup.find_all('itemref')
            
            for idx, itemref in enumerate(tqdm(itemrefs, desc=f"Downloading {item_title}", ncols=100, leave=False)):
                idref = itemref.get('idref')
                if not idref.startswith('page'):
                    continue
                    
                img_url = f'https://www.oxfordeducate.in/ContentServer/mvc/s3view/{book_id}/html5/{book_id}/OPS/{items.get(f"images{idref}svgz", items.get(f"images{idref}png", items.get(f"images{idref}jpg")))}'
                
                try:
                    if 'svgz' in img_url:
                        svg = fitz.open(stream=self.get_page(img_url), filetype="svg")
                        pdf_file.insert_pdf(fitz.open(stream=svg.convert_to_pdf()))
                    else:
                        img_data = self.get_page(img_url)
                        pix = fitz.Pixmap(img_data)
                        page = pdf_file.new_page(width=pix.width, height=pix.height)
                        page.insert_image((0, 0, page.rect.width, page.rect.height), pixmap=pix)
                        pix = None
                except Exception as e:
                    print(f"[!] Error downloading page {idx + 1}: {str(e)}")
                    continue
            
            print(f"[+] Downloaded {pdf_file.page_count} pages for {item_title}")
            return pdf_file, book
            
        except Exception as e:
            print(f"[!] Error downloading book item {item_title}: {e}")
            return None
    
    def get_page(self, url):
        """Get and decrypt page content"""
        response = self.session.get(url)
        if response.headers.get('X-Amz-Server-Side-Encryption') == 'AES256':
            cipher = AES.new(self.encryption_key.encode('utf-8'), AES.MODE_CBC, iv=self.encryption_key.encode('utf-8'))
            decrypted_bytes = cipher.decrypt(base64.b64decode(response.text))
            decrypted_text = decrypted_bytes.rstrip(b"\x01...\x0F").decode('utf-8')
            return decrypted_text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()
        return response.text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()
    
    def merge_books(self, book_files, collection_title):
        """Merge multiple book PDFs into one complete book"""
        if not book_files:
            print("[!] No books to merge")
            return
        
        print(f"[+] Merging {len(book_files)} books into complete collection...")
        
        # Create final PDF
        final_pdf = fitz.Document()
        
        for pdf_file, book_info in tqdm(book_files, desc="Merging books", ncols=100):
            if pdf_file and pdf_file.page_count > 0:
                final_pdf.insert_pdf(pdf_file)
                print(f"[+] Added {book_info.title} ({pdf_file.page_count} pages)")
        
        # Save merged PDF
        output_file = f"{sanitize_filename(collection_title)}_Complete.pdf"
        try:
            final_pdf.save(output_file, garbage=4, deflate=True, clean=True)
            print(f"\n[+] Complete book saved as: {output_file}")
            print(f"[+] Total pages in complete book: {final_pdf.page_count}")
        except Exception as e:
            print(f"\n[!] Error saving complete book: {str(e)}")
            try:
                final_pdf.save(output_file, garbage=3)
                print(f"\n[+] Complete book saved with alternative method as: {output_file}")
            except Exception as e2:
                print(f"\n[!] Alternative save also failed: {str(e2)}")
    
    async def run_complete_workflow(self):
        """Run the complete automated workflow with single browser session"""
        print("[+] Starting complete automated workflow...")
        
        # Initialize browser once and keep it open
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Step 1: Login (check if already logged in first)
            if not await self.login_with_single_browser():
                print("[!] Login failed, cannot proceed")
                return
            
            # Step 2: Find Class 5 books
            self.class5_books = await self.find_class5_books_single_browser()
            if not self.class5_books:
                print("[!] No Class 5 books found")
                return
            
            # Step 3: Select first book
            selected_book = self.class5_books[0]
            print(f"[+] Selected book: {selected_book['title']}")
            
            # Step 4: Get book collection
            collection_info = await self.get_book_collection_single_browser()
            if not collection_info:
                print("[!] Could not get book collection")
                return
            
            # Step 5: Download all books in collection
            book_files = []
            for book_info in tqdm(collection_info['books'], desc="Processing collection", ncols=100):
                print(f"\n[+] Processing: {book_info['title']}")
                
                # Get book ID from toc.xml
                book_id = await self.get_book_id_from_toc_single_browser(book_info)
                if book_id:
                    # Download book item
                    result = self.download_book_item(book_id, book_info['title'])
                    if result:
                        pdf_file, book_metadata = result
                        book_files.append((pdf_file, book_metadata))
                else:
                    print(f"[!] Could not get book ID for: {book_info['title']}")
            
            # Step 6: Merge all books
            if book_files:
                self.merge_books(book_files, collection_info['title'])
            else:
                print("[!] No books were downloaded to merge")
                
        except Exception as e:
            print(f"[!] Error in workflow: {e}")
        finally:
            # Close browser only at the end
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

    async def login_with_single_browser(self, username="gopalprasadpatel@gmail.com", password="London@12"):
        """Login using existing browser session"""
        if not PLAYWRIGHT_AVAILABLE:
            print("[!] Playwright not available")
            return False
        
        try:
            # Navigate to bookshelf URL
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf: {await self.page.title()}")
            
            # Wait for page to load
            await self.page.wait_for_timeout(3000)
            
            # Check if we're already logged in by looking for dashboard/bookshelf elements
            login_indicators = [
                'input[name="username"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="username" i]'
            ]
            
            dashboard_indicators = [
                '.bookshelf',
                '.dashboard',
                '.collection',
                '[class*="book"]',
                '[class*="shelf"]',
                '.bookThumbnailImages',
                '.collectionTitle'
            ]
            
            # Check for login form
            is_login_page = False
            for selector in login_indicators:
                try:
                    await self.page.wait_for_selector(selector, timeout=2000)
                    is_login_page = True
                    print(f"[+] Found login form - need to login")
                    break
                except:
                    continue
            
            # Check for dashboard
            is_dashboard = False
            if not is_login_page:
                for selector in dashboard_indicators:
                    try:
                        await self.page.wait_for_selector(selector, timeout=2000)
                        is_dashboard = True
                        print(f"[+] Found dashboard - already logged in!")
                        break
                    except:
                        continue
            
            if is_dashboard:
                # Extract cookies from already logged in session
                cookies = await self.page.context.cookies()
                cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                
                # Save cookies to file
                with open('cookies.txt', 'w') as f:
                    f.write(cookie_string)
                print(f"[+] Session cookies saved to cookies.txt")
                
                # Update requests session
                self.session.headers.update({'Cookie': cookie_string})
                self.logged_in = True
                
                return True
            elif is_login_page:
                # Need to login
                print("[+] Need to login - performing login...")
                
                # Find username field
                username_selectors = [
                    'input[name="username"]',
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="username" i]',
                    'input[id*="email" i]',
                    'input[id*="username" i]'
                ]
                
                username_field = None
                for selector in username_selectors:
                    try:
                        username_field = await self.page.wait_for_selector(selector, timeout=2000)
                        if username_field:
                            print(f"[+] Found username field with selector: {selector}")
                            break
                    except:
                        continue
                
                if not username_field:
                    print("[!] Could not find username/email field")
                    return False
                
                await username_field.fill(username)
                print("[+] Username field filled")
                
                # Find password field
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[placeholder*="password" i]',
                    'input[id*="password" i]'
                ]
                
                password_field = None
                for selector in password_selectors:
                    try:
                        password_field = await self.page.wait_for_selector(selector, timeout=2000)
                        if password_field:
                            print(f"[+] Found password field with selector: {selector}")
                            break
                    except:
                        continue
                
                if not password_field:
                    print("[!] Could not find password field")
                    return False
                
                await password_field.fill(password)
                print("[+] Password field filled")
                
                # Find and click login button
                login_button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    'input[type="submit"]',
                    'button.login-btn',
                    'button.btn-primary'
                ]
                
                login_button = None
                for selector in login_button_selectors:
                    try:
                        login_button = await self.page.wait_for_selector(selector, timeout=2000)
                        if login_button:
                            print(f"[+] Found login button with selector: {selector}")
                            break
                    except:
                        continue
                
                if not login_button:
                    print("[!] Could not find login button")
                    return False
                
                await login_button.click()
                print("[+] Login button clicked")
                
                # Wait for login to complete
                await self.page.wait_for_timeout(5000)
                
                # Check if login was successful
                login_success = False
                for indicator in dashboard_indicators:
                    try:
                        await self.page.wait_for_selector(indicator, timeout=3000)
                        login_success = True
                        print(f"[+] Login successful - found {indicator}")
                        break
                    except:
                        continue
                
                if not login_success:
                    print("[!] Login may have failed")
                    return False
                
                # Extract cookies
                cookies = await self.page.context.cookies()
                cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
                
                # Save cookies to file
                with open('cookies.txt', 'w') as f:
                    f.write(cookie_string)
                print(f"[+] Login cookies saved to cookies.txt")
                
                # Update requests session
                self.session.headers.update({'Cookie': cookie_string})
                self.logged_in = True
                
                # Keep browser open - DO NOT CLOSE
                print("[+] Browser session kept open for workflow")
                return True
            else:
                print("[!] Unknown page state")
                return False
                
        except Exception as e:
            print(f"[!] Error during login: {e}")
            return False

    async def find_class5_books_single_browser(self):
        """Find all Class 5 ebooks using existing browser session"""
        if not self.logged_in:
            print("[!] Please login first")
            return []
        
        try:
            # We're already using the same browser session, no need to load cookies
            # Navigate to bookshelf if not already there
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            # Take screenshot for debugging
            await self.page.screenshot(path="bookshelf_debug.png")
            print("[+] Bookshelf debug screenshot saved as bookshelf_debug.png")
            
            # Find Class 5 books using the exact HTML structure you provided
            class5_books = []
            
            # Look for the exact HTML structure: div with ng-if containing collectionType and class bookTitleText
            exact_book_elements = await self.page.query_selector_all(
                'div[ng-if*="collectionType"][class*="bookTitleText"]'
            )
            
            print(f"[+] Found {len(exact_book_elements)} elements with bookTitleText class")
            
            for element in exact_book_elements:
                try:
                    # Get the title from aria-label attribute
                    title = await element.get_attribute('aria-label')
                    
                    if title and '5' in title:
                        print(f"[+] Found Class 5 book: {title}")
                        
                        # Find the clickable parent (div with onclick or ng-click)
                        clickable_parent = await element.closest('div[onclick], div[ng-click], .book, .collection, [role="button"]')
                        
                        book_info = {
                            'title': title.strip(),
                            'element': element,
                            'clickable_parent': clickable_parent,
                            'aria_label': title
                        }
                        class5_books.append(book_info)
                        
                except Exception as e:
                    print(f"[!] Error processing book element: {e}")
                    continue
            
            # Alternative method: Use JavaScript to find elements
            if not class5_books:
                print("[+] Using JavaScript to find Class 5 books...")
                
                js_books = await self.page.evaluate('''
                    () => {
                        const books = [];
                        const elements = document.querySelectorAll('div[ng-if*="collectionType"][class*="bookTitleText"]');
                        
                        elements.forEach((element, index) => {
                            const title = element.getAttribute('aria-label');
                            if (title && title.includes('5')) {
                                // Find clickable parent
                                let clickableParent = element.closest('div[onclick], div[ng-click], [role="button"], .book, .collection');
                                
                                books.push({
                                    title: title.trim(),
                                    element: element,
                                    clickableParent: clickableParent,
                                    ariaLabel: title
                                });
                            }
                        });
                        
                        return books;
                    }
                ''')
                
                for book_data in js_books:
                    print(f"[+] Found Class 5 book (JS): {book_data['title']}")
                    class5_books.append(book_data)
            
            print(f"[+] Found {len(class5_books)} Class 5 books:")
            for i, book in enumerate(class5_books, 1):
                print(f"    {i}. {book['title']}")
            
            return class5_books
            
        except Exception as e:
            print(f"[!] Error finding Class 5 books: {e}")
            return []

    async def get_book_collection_single_browser(self):
        """Get book collection using existing browser session"""
        try:
            # Click on the first Class 5 book
            if not hasattr(self, 'class5_books') or not self.class5_books:
                print("[!] No Class 5 books available")
                return None
            
            selected_book = self.class5_books[0]
            
            if selected_book['clickable_parent']:
                await selected_book['clickable_parent'].click()
                print("[+] Book clicked, waiting for collection to load...")
                
                # Wait for collection view to appear
                await self.page.wait_for_selector('.allCategoeryCollectionView, .collection, .bookThumbnailImages', timeout=10000)
                
                # Extract collection information
                collection_info = await self.page.evaluate('''
                    () => {
                        const collectionDiv = document.querySelector('.allCategoeryCollectionView');
                        if (!collectionDiv) return null;
                        
                        const titleElement = collectionDiv.querySelector('.collectionTitle');
                        const itemsElement = collectionDiv.querySelector('.totalItems');
                        const bookElements = collectionDiv.querySelectorAll('.collectionBookContainer');
                        
                        const books = [];
                        bookElements.forEach((bookEl, index) => {
                            const titleEl = bookEl.querySelector('.bookTitleText');
                            const imgEl = bookEl.querySelector('.bookThumbnailImages');
                            const typeEl = bookEl.querySelector('.bookType');
                            
                            if (titleEl && imgEl) {
                                books.push({
                                    index: index,
                                    title: titleEl.textContent.trim(),
                                    ariaLabel: imgEl.getAttribute('aria-label'),
                                    type: typeEl ? typeEl.textContent.trim() : 'CHAPTER',
                                    onclick: imgEl.getAttribute('onclick'),
                                    ngClick: imgEl.getAttribute('ng-click')
                                });
                            }
                        });
                        
                        return {
                            title: titleElement ? titleElement.textContent.trim() : 'Unknown',
                            totalItems: itemsElement ? itemsElement.textContent.trim() : '0',
                            books: books
                        };
                    }
                ''')
                
                if collection_info:
                    print(f"[+] Collection found: {collection_info['title']}")
                    print(f"[+] Total items: {collection_info['totalItems']}")
                    print(f"[+] Found {len(collection_info['books'])} books in collection")
                    
                    return collection_info
                else:
                    print("[!] No collection found")
                    return None
            else:
                print("[!] No clickable element found for selected book")
                return None
                
        except Exception as e:
            print(f"[!] Error getting book collection: {e}")
            return None

    async def get_book_id_from_toc_single_browser(self, book_info):
        """Get book ID from toc.xml using existing browser session"""
        try:
            # Set up response interceptor to capture toc.xml request
            toc_data = {}
            
            async def handle_response(response):
                if 'toc.xml' in response.url:
                    print(f"[+] Intercepted toc.xml: {response.url}")
                    
                    # Extract book ID from URL
                    book_id_match = re.search(r'/s3view/(\d+)/html5/', response.url)
                    if book_id_match:
                        book_id = book_id_match.group(1)
                        toc_data['book_id'] = book_id
                        
                        # Get cookies from response headers
                        cookies = response.headers.get('set-cookie', '')
                        toc_data['cookies'] = cookies
                        
                        print(f"[+] Found book ID: {book_id}")
                    toc_data['status'] = response.status
            
            self.page.on('response', handle_response)
            
            # Find and click on the specific book
            book_selector = f'[aria-label="{book_info["ariaLabel"]}"]'
            await self.page.wait_for_selector(book_selector, timeout=10000)
            await self.page.click(book_selector)
            print(f"[+] Clicked on book: {book_info['title']}")
            
            # Wait for toc.xml request to be intercepted
            await self.page.wait_for_timeout(5000)
            
            # Remove response handler
            self.page.remove_listener('response', handle_response)
            
            if 'book_id' in toc_data:
                # Update cookies if new ones were received
                if 'cookies' in toc_data and toc_data['cookies']:
                    current_cookies = ''
                    try:
                        with open('cookies.txt', 'r') as f:
                            current_cookies = f.read().strip()
                        
                        # Parse and update cookies
                        updated_cookies = current_cookies + '; ' + toc_data['cookies']
                        with open('cookies.txt', 'w') as f:
                            f.write(updated_cookies)
                        
                        self.session.headers.update({'Cookie': updated_cookies})
                    except:
                        pass
                
                return toc_data['book_id']
            else:
                print(f"[!] Could not get book ID for: {book_info['title']}")
                return None
                
        except Exception as e:
            print(f"[!] Error getting book ID: {e}")
            return None

async def main():
    """Main function to run the complete workflow"""
    oxford = Oxford()
    await oxford.run_complete_workflow()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
