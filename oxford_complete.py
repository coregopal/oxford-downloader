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

class OxfordComplete:
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
        """Run the complete workflow with manual login handling"""
        print("[+] Starting complete automated workflow...")
        
        try:
            # Initialize browser with SSL certificate handling
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=['--ignore-certificate-errors', '--ignore-ssl-errors', '--ignore-certificate-errors-spki-list']
            )
            self.page = await self.browser.new_page()
            
            # Ignore SSL errors for the context
            await self.page.context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Step 1: Navigate to main Oxford URL first (this will redirect to login if needed)
            main_url = "https://www.oxfordeducate.in/reader/oupindia/"
            await self.page.goto(main_url, wait_until="networkidle")
            print(f"[+] Loaded main Oxford URL: {await self.page.title()}")
            
            # Wait for page to load completely
            await self.page.wait_for_timeout(8000)
            
            # Take screenshot
            await self.page.screenshot(path="step1_initial.png")
            print("[+] Step 1 screenshot saved")
            
            # Check current URL to see if we're on login page
            current_url = self.page.url
            print(f"[+] Current URL: {current_url}")
            
            # Check if we need to login - more robust detection
            page_content = await self.page.content()
            
            # Look for login indicators - check for actual login form elements
            login_indicators = [
                'input[name="username"',
                'input[type="email"',
                'placeholder="email"',
                'placeholder="username"',
                'input[name="password"',
                'input[type="password"',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'class="login"',
                'id="login"'
            ]
            
            # Also check for dashboard indicators - make them more specific
            dashboard_indicators = [
                'bookshelf',
                'allCategoeryCollectionView',
                'collectionTitle',
                'bookThumbnailImages',
                'collectionBookContainer',
                'totalItems'
            ]
            
            # Also check for login page specific indicators
            login_page_indicators = [
                'sign in',
                'register',
                'forgot password',
                'username',
                'password',
                'email id'
            ]
            
            login_found = any(indicator in page_content.lower() for indicator in login_indicators)
            dashboard_found = any(indicator in page_content.lower() for indicator in dashboard_indicators)
            login_page_found = any(indicator in page_content.lower() for indicator in login_page_indicators)
            
            print(f"[+] Login indicators found: {login_found}")
            print(f"[+] Dashboard indicators found: {dashboard_found}")
            print(f"[+] Login page indicators found: {login_page_found}")
            
            # If we have login page indicators, we're definitely on login page
            if login_page_found:
                print("[+] Login page detected - performing manual login...")
                
                # Manual login with explicit waits and verification
                try:
                    # First, check if we're on registration form by looking for registration-specific elements
                    is_registration_form = await self.page.evaluate('''
                        () => {
                            // Check for registration form indicators
                            const regIndicators = [
                                'registerEmail',
                                'phoneNumber', 
                                'schoolName',
                                'bookISBN',
                                'privacyCheckbox',
                                'Register via License Code'
                            ];
                            
                            const allElements = document.querySelectorAll('*');
                            for (let element of allElements) {
                                const text = element.textContent.toLowerCase();
                                const hasRegIndicator = regIndicators.some(indicator => 
                                    text.includes(indicator.toLowerCase()) || 
                                    element.getAttribute('ng-model') === indicator ||
                                    element.id === indicator
                                );
                                
                                if (hasRegIndicator) {
                                    console.log('Found registration indicator:', text);
                                    return true;
                                }
                            }
                            return false;
                        }
                    ''')
                    
                    if is_registration_form:
                        print("[+] On registration form - looking for Sign In link...")
                        
                        # Look for and click "Sign In" link to switch to login form
                        sign_in_clicked = await self.page.evaluate('''
                            () => {
                                // Look for "Sign In" or "Have an account?" text
                                const allElements = document.querySelectorAll('a, button, span, div, p');
                                for (let element of allElements) {
                                    const text = element.textContent.toLowerCase();
                                    if (text.includes('sign in') || text.includes('have an account') || text.includes('already have an account')) {
                                        console.log('Found sign in element:', element.textContent);
                                        element.click();
                                        return true;
                                    }
                                }
                                return false;
                            }
                        ''')
                        
                        if sign_in_clicked:
                            print("[+] Sign In link clicked, waiting for login form...")
                            await self.page.wait_for_timeout(5000)
                        else:
                            print("[!] Could not find Sign In link")
                            return
                    else:
                        print("[+] Already on login form - proceeding to fill fields...")
                    
                    # Now fill the actual login form
                    print("[+] Using JavaScript to fill login fields...")
                    
                    # Fill username field using JavaScript
                    await self.page.evaluate('''
                        () => {
                            const emailField = document.getElementById('userName');
                            if (emailField) {
                                emailField.focus();
                                emailField.value = '';
                                emailField.value = 'gopalprasadpatel@gmail.com';
                                
                                // Trigger multiple events to ensure the field is properly filled
                                emailField.dispatchEvent(new Event('focus', { bubbles: true }));
                                emailField.dispatchEvent(new Event('input', { bubbles: true }));
                                emailField.dispatchEvent(new Event('change', { bubbles: true }));
                                emailField.dispatchEvent(new Event('blur', { bubbles: true }));
                                
                                // Also try setting the model value if it's an Angular form
                                if (emailField.getAttribute('ng-model')) {
                                    const model = emailField.getAttribute('ng-model');
                                    window.eval(`${model} = 'gopalprasadpatel@gmail.com'`);
                                }
                            }
                        }
                    ''')
                    print("[+] Username filled using JavaScript")
                    
                    # Wait a moment to ensure the field is processed
                    await self.page.wait_for_timeout(2000)
                    
                    # Fill password field using JavaScript
                    await self.page.evaluate('''
                        () => {
                            const passwordField = document.getElementById('passwordField');
                            if (passwordField) {
                                const pwdField = passwordField;
                                pwdField.focus();
                                pwdField.value = '';
                                pwdField.value = 'London@12';
                                
                                // Trigger multiple events
                                pwdField.dispatchEvent(new Event('focus', { bubbles: true }));
                                pwdField.dispatchEvent(new Event('input', { bubbles: true }));
                                pwdField.dispatchEvent(new Event('change', { bubbles: true }));
                                pwdField.dispatchEvent(new Event('blur', { bubbles: true }));
                            }
                        }
                    ''')
                    print("[+] Password filled using JavaScript")
                    
                    # Wait for fields to be processed and button to become enabled
                    await self.page.wait_for_timeout(3000)
                    
                    # Wait for login button with correct class
                    print("[+] Looking for login button...")
                    
                    # Debug: Find all buttons on page
                    all_buttons = await self.page.evaluate('''
                        () => {
                            const buttons = document.querySelectorAll('button');
                            const buttonInfo = [];
                            buttons.forEach((button, index) => {
                                buttonInfo.push({
                                    index: index,
                                    text: button.textContent.trim(),
                                    className: button.className,
                                    ariaLabel: button.getAttribute('aria-label'),
                                    disabled: button.disabled
                                });
                            });
                            return buttonInfo;
                        }
                    ''')
                    
                    print(f"[+] Found {len(all_buttons)} buttons on page:")
                    for btn in all_buttons:
                        print(f"    {btn['index']}: '{btn['text']}' (class: {btn['className']}, aria-label: {btn['ariaLabel']}, disabled: {btn['disabled']})")
                    
                    # Try multiple approaches to find and click login button
                    print("[+] Looking for Sign In button...")
                    
                    # Wait for button to become enabled and click it
                    try:
                        # Wait for the Sign In button to be enabled (not disabled)
                        login_button = await self.page.wait_for_selector('button.signInButton[aria-label="Sign In"]:not([disabled])', timeout=10000)
                        await login_button.click()
                        print("[+] Sign In button clicked successfully!")
                    except:
                        print("[+] Waiting for button to enable, trying JavaScript...")
                        
                        # Use JavaScript to wait for button to be enabled and click
                        login_clicked = await self.page.evaluate('''
                            () => {
                                console.log('Looking for enabled Sign In button...');
                                
                                // Look for button with exact text "Sign In" and not disabled
                                const buttons = document.querySelectorAll('button');
                                for (let button of buttons) {
                                    const text = button.textContent.trim();
                                    const isDisabled = button.disabled || button.hasAttribute('disabled');
                                    
                                    console.log('Button found:', text, 'Class:', button.className, 'Disabled:', isDisabled);
                                    
                                    if (text.toLowerCase() === 'sign in' && !isDisabled) {
                                        console.log('Found enabled Sign In button, clicking:', text);
                                        
                                        // Try multiple click methods
                                        try {
                                            button.click();
                                            console.log('Standard click successful');
                                            return true;
                                        } catch(e) {
                                            console.log('Standard click failed:', e);
                                        }
                                        
                                        try {
                                            button.dispatchEvent(new Event('click', { bubbles: true }));
                                            console.log('Event dispatch successful');
                                            return true;
                                        } catch(e) {
                                            console.log('Event dispatch failed:', e);
                                        }
                                    }
                                }
                                return false;
                            }
                        ''')
                        
                        if login_clicked:
                            print("[+] Sign In button clicked using JavaScript")
                        else:
                            print("[!] Could not find enabled Sign In button")
                            return
                    
                    # Wait for login to complete
                    print("[+] Waiting for login to complete...")
                    await self.page.wait_for_timeout(12000)  # Wait 12 seconds for login
                    
                    # Check if login successful by looking for dashboard indicators
                    page_after_login = await self.page.content()
                    login_success = any(indicator in page_after_login.lower() for indicator in dashboard_indicators)
                    
                    if login_success:
                        print("[+] Login successful!")
                    else:
                        print("[!] Login may have failed - no dashboard indicators found")
                        # Take screenshot for debugging
                        await self.page.screenshot(path="login_failed_debug.png")
                        print("[+] Login failed screenshot saved")
                        return
                        
                except Exception as e:
                    print(f"[!] Error during login: {e}")
                    return
            
            elif dashboard_found and not login_page_found:
                print("[+] Already logged in - dashboard detected")
            else:
                print("[!] Unknown page state - checking current URL...")
                current_url = self.page.url
                print(f"[+] Current URL: {current_url}")
                
                if 'login' in current_url.lower():
                    print("[+] URL indicates login page - forcing login...")
                    # Force login approach here if needed
                else:
                    print("[!] Could not determine page state")
                    return
            
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
            bookshelf_url = "https://www.oxfordeducate.in/reader/oupindia/#!/bookshelf"
            
            if 'bookshelf' not in current_url.lower():
                print("\n[+] Navigating to bookshelf...")
                await self.page.goto(bookshelf_url, wait_until="networkidle")
                await self.page.wait_for_timeout(5000)
                
                # Take screenshot
                await self.page.screenshot(path="step2_bookshelf.png")
                print("[+] Step 2 screenshot saved")
            
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
            
            # Step 4: Click on the specific "Friday Afternoon Comprehension and Composition 5" book
            if self.class5_books:
                # Find the Friday Afternoon book specifically
                target_book = None
                for book in self.class5_books:
                    if "Friday Afternoon" in book['title']:
                        target_book = book
                        break
                
                if not target_book:
                    # Fallback to first book if Friday Afternoon not found
                    target_book = self.class5_books[0]
                
                print(f"[+] Selected book: {target_book['title']}")
                
                # Click on the specific book container that contains this book
                try:
                    # Look for the book container with the specific title
                    book_selector = f'div.bookContainer:has(div.bookTitleText[aria-label*="{target_book["title"]}"])'
                    book_container = await self.page.wait_for_selector(book_selector, timeout=10000)
                    await book_container.click()
                    print("[+] Target book container clicked!")
                except Exception as e:
                    print(f"[!] Error clicking target book container: {e}")
                    # Fallback to JavaScript click for specific book
                    await self.page.evaluate(f'''
                        () => {{
                            const bookContainers = document.querySelectorAll('div.bookContainer');
                            for (let container of bookContainers) {{
                                const titleElement = container.querySelector('div.bookTitleText');
                                if (titleElement && titleElement.getAttribute('aria-label').includes("{target_book['title']}")) {{
                                    container.click();
                                    return true;
                                }}
                            }}
                            return false;
                        }}
                    ''')
                    print("[+] Target book container clicked using JavaScript")
                
                # Wait for book collection to load
                await self.page.wait_for_timeout(5000)
                
                # Take screenshot of collection
                await self.page.screenshot(path="step3_book_collection.png")
                print("[+] Book collection screenshot saved")
                
                # Extract collection info
                collection_info = await self.extract_collection_info()
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
            else:
                print("[!] No Class 5 books found")
            
            print(f"\n[+] Workflow completed successfully!")
            print("[+] All files saved for analysis")
            print("[+] Browser kept open for inspection...")
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

async def extract_collection_info(self):
        """Extract collection information from the current page"""
        try:
            # Wait for collection to load
            await self.page.wait_for_timeout(3000)
            
            # Get page content
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Extract collection title and items
            collection_info = {
                'title': 'Unknown Collection',
                'totalItems': '0',
                'books': []
            }
            
            # Look for collection title
            title_element = soup.find('div', class_='collectionTitle')
            if title_element:
                collection_info['title'] = title_element.get_text(strip=True)
            
            # Look for total items
            items_element = soup.find('div', class_='totalItems')
            if items_element:
                collection_info['totalItems'] = items_element.get_text(strip=True)
            
            # Extract book/chapter information
            book_elements = soup.find_all('div', class_='bookContainer')
            for book_element in book_elements:
                try:
                    title_element = book_element.find('div', class_='bookTitleText')
                    img_element = book_element.find('div', class_='bookThumbnailImages')
                    type_element = book_element.find('span', class_='bookType')
                    
                    if title_element and img_element:
                        book_info = {
                            'title': title_element.get_text(strip=True),
                            'ariaLabel': img_element.get('aria-label', ''),
                            'type': type_element.get_text(strip=True) if type_element else 'CHAPTER',
                            'onclick': img_element.get('onclick', '')
                        }
                        collection_info['books'].append(book_info)
                except Exception as e:
                    print(f"[!] Error extracting book info: {e}")
                    continue
            
            return collection_info if collection_info['books'] else None
            
        except Exception as e:
            print(f"[!] Error extracting collection info: {e}")
            return None

async def main():
    """Main function to run complete workflow"""
    oxford = OxfordComplete()
    await oxford.run_complete_workflow()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
