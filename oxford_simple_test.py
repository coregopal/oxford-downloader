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

class OxfordSimple:
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
        """Run the complete automated workflow with single browser session"""
        print("[+] Starting complete automated workflow...")
        
        # Initialize browser once and keep it open
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            
            # Step 1: Login and check page state
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            await self.page.goto(bookshelf_url, wait_until="networkidle")
            print(f"[+] Loaded bookshelf: {await self.page.title()}")
            
            # Wait for page to load
            await self.page.wait_for_timeout(5000)
            
            # Take screenshot for debugging
            await self.page.screenshot(path="initial_page.png")
            print("[+] Initial page screenshot saved")
            
            # Check page content to understand what we're seeing
            page_content = await self.page.content()
            
            # Check if login form exists
            has_login = any(indicator in page_content.lower() for indicator in [
                'input[name="username"]',
                'input[type="email"]',
                'placeholder="email"',
                'placeholder="username"'
            ])
            
            # Check if dashboard exists
            has_dashboard = any(indicator in page_content.lower() for indicator in [
                'bookshelf',
                'dashboard', 
                'collection',
                'booktitletext',
                'collectiontitle'
            ])
            
            print(f"[+] Page analysis - Has login: {has_login}, Has dashboard: {has_dashboard}")
            
            if has_login:
                print("[+] Need to login...")
                
                # Find and fill username
                try:
                    await self.page.fill('input[name="username"], input[type="email"], input[placeholder*="email"]', "gopalprasadpatel@gmail.com")
                    print("[+] Username filled")
                except:
                    print("[!] Could not fill username")
                    return False
                
                # Find and fill password
                try:
                    await self.page.fill('input[name="password"], input[type="password"]', "London@12")
                    print("[+] Password filled")
                except:
                    print("[!] Could not fill password")
                    return False
                
                # Click login button
                try:
                    await self.page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
                    print("[+] Login button clicked")
                except:
                    print("[!] Could not click login button")
                    return False
                
                # Wait for login
                await self.page.wait_for_timeout(5000)
                
                # Re-check page after login
                page_content_after = await self.page.content()
                has_dashboard_after = any(indicator in page_content_after.lower() for indicator in [
                    'bookshelf', 'dashboard', 'collection', 'booktitletext'
                ])
                
                if has_dashboard_after:
                    print("[+] Login successful!")
                else:
                    print("[!] Login may have failed")
                    return False
            
            # Extract cookies regardless of login state
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
            await self.page.wait_for_timeout(3000)
            
            # Take screenshot of bookshelf
            await self.page.screenshot(path="bookshelf_page.png")
            print("[+] Bookshelf screenshot saved")
            
            # Get page content and search for Class 5 books
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Find all elements with the exact HTML structure you provided
            class5_books = []
            
            # Method 1: Use Playwright to find exact structure
            try:
                exact_books = await self.page.query_selector_all(
                    'div[ng-if*="collectionType"][class*="bookTitleText"]'
                )
                
                print(f"[+] Found {len(exact_books)} elements with exact structure")
                
                for element in exact_books:
                    try:
                        # Get the title from aria-label attribute
                        title = await element.get_attribute('aria-label')
                        
                        if title and '5' in title:
                            print(f"[+] Found Class 5 book: {title}")
                            
                            book_info = {
                                'title': title.strip(),
                                'element': element,
                                'tag': element.tag_name if hasattr(element, 'tag_name') else 'div',
                                'aria_label': title,
                                'found_by': 'exact_structure'
                            }
                            
                            # Avoid duplicates
                            if not any(book['title'] == book_info['title'] for book in class5_books):
                                class5_books.append(book_info)
                                
                    except Exception as e:
                        print(f"[!] Error processing exact book element: {e}")
                        continue
                        
            except Exception as e:
                print(f"[!] Error with exact structure search: {e}")
            
            # Method 2: Use JavaScript to find elements with exact structure
            if not class5_books:
                try:
                    print("[+] Using JavaScript to find exact structure...")
                    
                    js_books = await self.page.evaluate('''
                        () => {
                            const books = [];
                            const elements = document.querySelectorAll('div[ng-if*="collectionType"][class*="bookTitleText"]');
                            
                            elements.forEach((element, index) => {
                                const title = element.getAttribute('aria-label');
                                if (title && title.includes('5')) {
                                    books.push({
                                        title: title.trim(),
                                        element: element,
                                        tagName: element.tagName,
                                        className: element.className,
                                        ariaLabel: title,
                                        foundBy: 'javascript_exact'
                                    });
                                }
                            });
                            
                            return books;
                        }
                    ''')
                    
                    for book_data in js_books:
                        print(f"[+] Found Class 5 book (JS exact): {book_data['title']}")
                        
                        # Avoid duplicates
                        if not any(book['title'] == book_data['title'] for book in class5_books):
                            class5_books.append(book_data)
                            
                except Exception as e:
                    print(f"[!] Error with JavaScript exact search: {e}")
            
            # Method 3: Fallback - look for any div with aria-label containing "5" and bookTitleText in class
            if not class5_books:
                print("[+] Using fallback method...")
                
                fallback_elements = await self.page.query_selector_all('div[aria-label*="5"]')
                
                for element in fallback_elements:
                    try:
                        classes = await element.get_attribute('class') or ''
                        title = await element.get_attribute('aria-label') or ''
                        
                        if 'bookTitleText' in classes and '5' in title:
                            print(f"[+] Found Class 5 book (fallback): {title}")
                            
                            book_info = {
                                'title': title.strip(),
                                'element': element,
                                'found_by': 'fallback'
                            }
                            
                            if not any(book['title'] == book_info['title'] for book in class5_books):
                                class5_books.append(book_info)
                                
                    except Exception as e:
                        continue
            
            self.class5_books = class5_books
            
            print(f"[+] Found {len(class5_books)} Class 5 books:")
            for i, book in enumerate(class5_books, 1):
                print(f"    {i}. {book['title']}")
            
            if not class5_books:
                print("[!] No Class 5 books found")
                return
            
            # For now, just report success - we'll add collection handling next
            print(f"[+] Successfully found {len(class5_books)} Class 5 books!")
            print("[+] Browser session kept open for next steps")
            
            # Keep browser open - don't close it
            input("[+] Press Enter to close browser and continue...")
            
        except Exception as e:
            print(f"[!] Error in workflow: {e}")
        finally:
            # Only close browser at the very end
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

async def main():
    """Main function to run complete workflow"""
    oxford = OxfordSimple()
    await oxford.run_complete_workflow()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
