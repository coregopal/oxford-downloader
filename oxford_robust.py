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

class OxfordRobust:
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
        """Run the complete workflow with robust error handling"""
        print("[+] Starting robust automated workflow...")
        
        try:
            # Initialize browser
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Step 1: Navigate to bookshelf and handle login
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf: {await self.page.title()}")
            
            # Wait and analyze page
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot
            await self.page.screenshot(path="step1_initial.png")
            print("[+] Step 1 screenshot saved")
            
            # Check if we need to login
            page_content = await self.page.content()
            
            # Look for login indicators
            login_indicators = ['input[name="username"', 'input[type="email"', 'placeholder="email"']
            needs_login = any(indicator in page_content for indicator in login_indicators)
            
            if needs_login:
                print("[+] Login form detected - performing login...")
                
                # Fill username
                try:
                    await self.page.fill('input[name="username"], input[type="email"], input[placeholder*="email"]', "gopalprasadpatel@gmail.com")
                    print("[+] Username filled")
                except Exception as e:
                    print(f"[!] Error filling username: {e}")
                    return
                
                # Fill password
                try:
                    await self.page.fill('input[name="password"], input[type="password"]', "London@12")
                    print("[+] Password filled")
                except Exception as e:
                    print(f"[!] Error filling password: {e}")
                    return
                
                # Click login button
                try:
                    await self.page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
                    print("[+] Login button clicked")
                except Exception as e:
                    print(f"[!] Error clicking login: {e}")
                    return
                
                # Wait for login to complete
                await self.page.wait_for_timeout(8000)
                
                # Take screenshot after login
                await self.page.screenshot(path="step2_after_login.png")
                print("[+] Step 2 screenshot saved")
                
                # Check if login successful
                page_after_login = await self.page.content()
                dashboard_indicators = ['bookshelf', 'dashboard', 'collection', 'bookThumbnailImages']
                login_success = any(indicator in page_after_login.lower() for indicator in dashboard_indicators)
                
                if not login_success:
                    print("[!] Login may have failed - no dashboard indicators found")
                    return
                
                print("[+] Login successful!")
            
            # Extract cookies
            cookies = await self.page.context.cookies()
            cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            
            with open('cookies.txt', 'w') as f:
                f.write(cookie_string)
            print(f"[+] Cookies saved to cookies.txt")
            
            self.session.headers.update({'Cookie': cookie_string})
            self.logged_in = True
            
            # Step 2: Find Class 5 books
            print("\n[+] Looking for Class 5 books...")
            
            # Navigate to bookshelf again to ensure we're on right page
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot
            await self.page.screenshot(path="step3_bookshelf.png")
            print("[+] Step 3 screenshot saved")
            
            # Get page content
            page_content = await self.page.content()
            
            # Save HTML for analysis
            with open('bookshelf_analysis.html', 'w', encoding='utf-8') as f:
                f.write(page_content)
            print("[+] Bookshelf HTML saved to bookshelf_analysis.html")
            
            # Search for Class 5 books using multiple methods
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
            
            # Method 2: JavaScript search
            if not class5_books:
                try:
                    print("[+] Using JavaScript search...")
                    
                    js_books = await self.page.evaluate('''
                        () => {
                            const books = [];
                            const allElements = document.querySelectorAll('*');
                            
                            allElements.forEach((element) => {
                                const ariaLabel = element.getAttribute('aria-label');
                                const className = element.className || '';
                                
                                if (ariaLabel && ariaLabel.includes('5') && 
                                    className.includes('bookTitleText')) {
                                    books.push({
                                        title: ariaLabel.trim(),
                                        tagName: element.tagName,
                                        className: className,
                                        ariaLabel: ariaLabel
                                    });
                                }
                            });
                            
                            return books;
                        }
                    ''')
                    
                    for book_data in js_books:
                        print(f"[+] Found Class 5 book (JS): {book_data['title']}")
                        
                        book_info = {
                            'title': book_data['title'],
                            'found_by': 'javascript_search'
                        }
                        
                        # Avoid duplicates
                        if not any(book['title'] == book_info['title'] for book in class5_books):
                            class5_books.append(book_info)
                            
                except Exception as e:
                    print(f"[!] Error with JavaScript search: {e}")
            
            # Method 3: Text search in HTML
            if not class5_books:
                print("[+] Using text search in HTML...")
                
                text_search = re.findall(r'aria-label="([^"]*5[^"]*)"', page_content)
                print(f"[+] Found {len(text_search)} aria-label elements with '5'")
                
                for match in text_search:
                    title = match[1] if len(match) > 1 else match[0]
                    if title and len(title) > 5:  # Filter out short matches
                        print(f"[+] Found Class 5 book (text): {title}")
                        
                        book_info = {
                            'title': title.strip(),
                            'found_by': 'text_search'
                        }
                        
                        # Avoid duplicates
                        if not any(book['title'] == book_info['title'] for book in class5_books):
                            class5_books.append(book_info)
            
            self.class5_books = class5_books
            
            print(f"\n[+] Found {len(class5_books)} Class 5 books:")
            for i, book in enumerate(class5_books, 1):
                print(f"    {i}. {book['title']}")
            
            if not class5_books:
                print("[!] No Class 5 books found")
                return
            
            print(f"\n[+] Successfully found {len(class5_books)} Class 5 books!")
            print("[+] Workflow completed successfully!")
            
            # Keep browser open for manual inspection
            print("\n[+] Browser kept open for inspection...")
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
    """Main function to run robust workflow"""
    oxford = OxfordRobust()
    await oxford.run_complete_workflow()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
