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

class OxfordWorking:
    def __init__(self, ebook_id=None):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        self.encryption_key = ""
        self.ebook_id = ebook_id
        self.logged_in = False
        self.playwright = None
        self.browser = None
        self.page = None
        self.class5_books = []
        
    async def run_complete_workflow(self):
        """Run the complete workflow with proper login handling"""
        print("[+] Starting working automated workflow...")
        
        try:
            # Initialize browser
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Step 1: Navigate to bookshelf URL directly
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf URL: {await self.page.title()}")
            
            # Wait for page to load
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot
            await self.page.screenshot(path="step1_bookshelf.png")
            print("[+] Step 1 screenshot saved")
            
            # Check if we need to login
            page_content = await self.page.content()
            
            # Look for login indicators
            login_indicators = ['input[name="username"', 'input[type="email"', 'placeholder="email"']
            needs_login = any(indicator in page_content for indicator in login_indicators)
            
            if needs_login:
                print("[+] Login form detected - performing login...")
                
                # Fill username with multiple selectors
                username_selectors = [
                    'input[name="username"]',
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                    'input[id*="email" i]',
                    'input[id*="username" i]',
                    'input.form-control[type="email"]'
                ]
                
                username_filled = False
                for selector in username_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element:
                            await element.fill("gopalprasadpatel@gmail.com")
                            print(f"[+] Username filled using selector: {selector}")
                            username_filled = True
                            break
                    except:
                        continue
                
                if not username_filled:
                    print("[!] Could not find username field")
                    return
                
                # Fill password with multiple selectors
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[placeholder*="password" i]',
                    'input[id*="password" i]',
                    'input.form-control[type="password"]'
                ]
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element:
                            await element.fill("London@12")
                            print(f"[+] Password filled using selector: {selector}")
                            password_filled = True
                            break
                    except:
                        continue
                
                if not password_filled:
                    print("[!] Could not find password field")
                    return
                
                # Click login button with multiple selectors
                login_button_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    'input[type="submit"]',
                    'button.login-btn',
                    'button.btn-primary',
                    'button.md-primary',
                    '[class*="login"]'
                ]
                
                login_clicked = False
                for selector in login_button_selectors:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000)
                        if element:
                            await element.click()
                            print(f"[+] Login button clicked using selector: {selector}")
                            login_clicked = True
                            break
                    except:
                        continue
                
                if not login_clicked:
                    print("[!] Could not find login button")
                    return
                
                # Wait for login to complete - longer wait
                print("[+] Waiting for login to complete...")
                await self.page.wait_for_timeout(10000)
                
                # Check if login successful
                page_after_login = await self.page.content()
                dashboard_indicators = ['bookshelf', 'dashboard', 'collection', 'bookThumbnailImages', 'ng-view', 'bookTitleText']
                login_success = any(indicator in page_after_login.lower() for indicator in dashboard_indicators)
                
                if not login_success:
                    print("[!] Login may have failed - no dashboard indicators found")
                    # Take screenshot for debugging
                    await self.page.screenshot(path="login_failed.png")
                    print("[+] Login failed screenshot saved")
                    return
                
                print("[+] Login successful!")
                
                # Take screenshot after successful login
                await self.page.screenshot(path="step2_logged_in.png")
                print("[+] Step 2 screenshot saved")
            
            else:
                print("[+] Already logged in or no login needed")
            
            # Extract cookies
            cookies = await self.page.context.cookies()
            cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            
            with open('cookies.txt', 'w') as f:
                f.write(cookie_string)
            print(f"[+] Cookies saved to cookies.txt")
            
            self.session.headers.update({'Cookie': cookie_string})
            self.logged_in = True
            
            # Step 2: Navigate to bookshelf if not already there
            current_url = self.page.url
            if 'bookshelf' not in current_url.lower():
                print("\n[+] Navigating to bookshelf...")
                await self.page.goto(bookshelf_url, wait_until="networkidle")
                await self.page.wait_for_timeout(5000)
                
                # Take screenshot
                await self.page.screenshot(path="step3_bookshelf.png")
                print("[+] Step 3 screenshot saved")
            
            # Save HTML for analysis
            page_content = await self.page.content()
            with open('bookshelf_final.html', 'w', encoding='utf-8') as f:
                f.write(page_content)
            print("[+] Bookshelf HTML saved to bookshelf_final.html")
            
            # Step 3: Find Class 5 books with comprehensive search
            print("\n[+] Searching for Class 5 books...")
            class5_books = []
            
            # Method 1: Look for exact HTML structure
            try:
                exact_books = await self.page.query_selector_all(
                    'div[ng-if*="collectionType"][class*="bookTitleText"]'
                )
                
                print(f"[+] Found {len(exact_books)} elements with bookTitleText class")
                
                for element in exact_books:
                    title = await element.get_attribute('aria-label')
                    if title and '5' in title:
                        print(f"[+] Found Class 5 book: {title}")
                        
                        book_info = {
                            'title': title.strip(),
                            'element': element,
                            'found_by': 'exact_structure'
                        }
                        class5_books.append(book_info)
                        
            except Exception as e:
                print(f"[!] Error with exact search: {e}")
            
            # Method 2: JavaScript comprehensive search
            if not class5_books:
                try:
                    print("[+] Using comprehensive JavaScript search...")
                    
                    js_books = await self.page.evaluate('''
                        () => {
                            const books = [];
                            const allElements = document.querySelectorAll('*');
                            
                            allElements.forEach((element) => {
                                const ariaLabel = element.getAttribute('aria-label');
                                const className = element.className || '';
                                const textContent = element.textContent || '';
                                
                                // Look for Class 5 books with multiple criteria
                                if ((ariaLabel && ariaLabel.includes('5')) || 
                                    (textContent && textContent.includes('5')) ||
                                    (className.includes('bookTitleText') && ariaLabel && ariaLabel.includes('5'))) {
                                    
                                    books.push({
                                        title: ariaLabel ? ariaLabel.trim() : textContent.trim(),
                                        tagName: element.tagName,
                                        className: className,
                                        ariaLabel: ariaLabel,
                                        textContent: textContent
                                    });
                                }
                            });
                            
                            return books;
                        }
                    ''')
                    
                    for book_data in js_books:
                        title = book_data['title']
                        if title and '5' in title and len(title) > 5:
                            print(f"[+] Found Class 5 book (JS): {title}")
                            
                            book_info = {
                                'title': title.strip(),
                                'found_by': 'javascript_comprehensive'
                            }
                            
                            # Avoid duplicates
                            if not any(book['title'] == book_info['title'] for book in class5_books):
                                class5_books.append(book_info)
                            
                except Exception as e:
                    print(f"[!] Error with JavaScript search: {e}")
            
            self.class5_books = class5_books
            
            print(f"\n[+] Found {len(class5_books)} Class 5 books:")
            for i, book in enumerate(class5_books, 1):
                print(f"    {i}. {book['title']}")
            
            if not class5_books:
                print("[!] No Class 5 books found")
                return
            
            # Step 4: Click on first Class 5 book
            if self.class5_books:
                selected_book = self.class5_books[0]
                print(f"\n[+] Selected book: {selected_book['title']}")
                
                # Click on the book
                if 'element' in selected_book:
                    try:
                        await selected_book['element'].click()
                        print("[+] Book clicked!")
                        
                        # Wait for collection to load
                        await self.page.wait_for_timeout(5000)
                        
                        # Take screenshot of collection
                        await self.page.screenshot(path="collection_page.png")
                        print("[+] Collection screenshot saved")
                        
                        # Extract collection info
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
                            
                            # Save collection info
                            with open('collection_info.json', 'w') as f:
                                json.dump(collection_info, f, indent=2)
                            print("[+] Collection info saved to collection_info.json")
                        
                        else:
                            print("[!] Could not extract collection info")
                    except Exception as e:
                        print(f"[!] Error clicking book: {e}")
            
            print(f"\n[+] Workflow completed successfully!")
            print("[+] Browser kept open for manual inspection...")
            print("[+] Press Enter to close browser")
            
            # Wait for user input before closing
            input()
            
        except Exception as e:
            print(f"[!] Error in workflow: {e}")
        finally:
            # Close browser
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

async def main():
    """Main function to run working workflow"""
    oxford = OxfordWorking()
    await oxford.run_complete_workflow()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
