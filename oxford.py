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

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def sanitize_filename(filename):
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, '_', filename)

'''
what you need:
- cookies
- encryption_key: on console -> window.angularComponentRef.render.settings.encResource
- ebook_id
'''

@dataclass
class Book:
    title: str
    pages: int
    description: str
    author: str
    isbn: str

class Oxford:
    def __init__(self, ebook_id):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        self.session.headers.update(self.parse_cookies())
        self.encryption_key = ""
        self.ebook_id = ebook_id

    @staticmethod
    def parse_cookies():
        with open('cookies.txt', 'r') as f: cookie_string = f.readline().strip()
        keys = ["CloudFront-Policy", "CloudFront-Signature", "CloudFront-Key-Pair-Id", "kitaboo_metadata", "kitaboo_metadata_chain_0", "JSESSIONID", "AWSALB","AWSALBCORS"]
        result = []
        for key in keys:
            pattern = f'{key}=([^;]*)'
            if match := re.search(pattern, cookie_string):
                result.append(f'{key}={match[1]}')
        return {'Cookie': '; '.join(result)}

    def get_toc(self):
        soup = BeautifulSoup(self.session.get(f'https://www.oxfordeducate.in/ContentServer/mvc/s3view/{self.ebook_id}/html5/{self.ebook_id}/OPS/toc.xml').content, 'xml')
        def dictify(node):
            result = {}
            for child_node in node.find_all("node", recursive=False):
                page_id = child_node['id']
                # Handle non-numeric page IDs by setting them to 1
                page = 1 if any(char.isalpha() for char in page_id) else int(page_id)
                key = child_node['title']
                result[key] = [page, dictify(child_node) if child_node.find("node") else None]
            return result

        def tocify(toc_dict):
            toc = []
            for key, value in toc_dict.items():
                # Ensure page number is at least 1
                page_num = max(1, value[0])
                toc.append([1, key, page_num])
                if value[1]:
                    for sub_key, sub_value in value[1].items():
                        sub_page_num = max(1, sub_value[0])
                        toc.append([2, sub_key, sub_page_num])
            return toc

        return tocify(dictify(soup.toc))

    def get_page(self, url):
        response = self.session.get(url)
        if response.headers.get('X-Amz-Server-Side-Encryption') == 'AES256':
            cipher = AES.new(self.encryption_key.encode('utf-8'), AES.MODE_CBC, iv=self.encryption_key.encode('utf-8'))
            decrypted_bytes = cipher.decrypt(base64.b64decode(response.text))
            decrypted_text = decrypted_bytes.rstrip(b"\x01...\x0F").decode('utf-8')
            return decrypted_text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()
        return response.text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()

    def download_ebook(self):
        response = self.session.get(f'https://www.oxfordeducate.in/ContentServer/mvc/s3view/{self.ebook_id}/html5/{self.ebook_id}/OPS/content.opf')
        soup = BeautifulSoup(response.text, 'lxml')
        book = Book(title=soup.find('dc:title').text, pages=int(soup.select('itemref')[-1]['idref'].removeprefix('page')), description=soup.find('dc:description').text, author=soup.find('dc:author').text, isbn=soup.find('dc:identifier').text.split(':')[2])
        print(f'''
[+] Book Found:
    - title: {book.title}
    - author: {book.author}
    - isbn: {book.isbn}
    - pages: {book.pages}
''')
        items = {}
        for item in soup.find_all('item'):
            media_type = item.get('media-type')
            if media_type in ['image/svg+xml', 'image/png', 'image/jpeg']:
                items[item.get('id')] = item.get('href')

        pdf_file = fitz.Document()
        itemrefs = soup.find_all('itemref')
        print(f"\n[+] Found {len(itemrefs)} pages to download")
        
        for idx, itemref in enumerate(tqdm(itemrefs, desc="Downloading", ncols=100)):
            idref = itemref.get('idref')
            if not idref.startswith('page'):
                print(f"\n[!] Skipping non-page item: {idref}")
                continue
                
            img_url = f'https://www.oxfordeducate.in/ContentServer/mvc/s3view/{self.ebook_id}/html5/{self.ebook_id}/OPS/{items.get(f"images{idref}svgz", items.get(f"images{idref}png", items.get(f"images{idref}jpg")))}'
            print(f"\n[+] Downloading page {idx + 1}/{len(itemrefs)}: {img_url}")
            
            try:
                if 'svgz' in img_url:
                    svg = fitz.open(stream=self.get_page(img_url), filetype="svg")
                    pdf_file.insert_pdf(fitz.open(stream=svg.convert_to_pdf()))
                else: # any other image format
                    img_data = self.get_page(img_url)
                    pix = fitz.Pixmap(img_data)
                    # Create a new page with the image dimensions
                    page = pdf_file.new_page(width=pix.width, height=pix.height)
                    # Insert the image into the page
                    page.insert_image((0, 0, page.rect.width, page.rect.height), pixmap=pix)
                    pix = None  # Free the pixmap memory
            except Exception as e:
                print(f"\n[!] Error downloading page {idx + 1}: {str(e)}")
                continue

        print(f"\n[+] Downloaded {pdf_file.page_count} pages")
        try: 
            toc = self.get_toc()
            if toc and pdf_file.page_count > 0:
                pdf_file.set_toc(toc)
        except Exception as e:
            print(f"\n[!] Error setting TOC: {str(e)}")
            pass

        output_file = f"{sanitize_filename(book.title)}.pdf"
        try:
            pdf_file.save(output_file, garbage=4, deflate=True, clean=True)
            print(f"\n[+] PDF saved as: {output_file}")
            print(f"[+] Total pages in saved PDF: {pdf_file.page_count}")
        except Exception as e:
            print(f"\n[!] Error saving PDF: {str(e)}")
            try:
                pdf_file.save(output_file, garbage=3)
                print(f"\n[+] PDF saved with alternative method as: {output_file}")
            except Exception as e2:
                print(f"\n[!] Alternative save also failed: {str(e2)}")


if __name__ == "__main__":
    BOOKID = "680165"
    oxford_instance = Oxford(BOOKID)
    oxford_instance.download_ebook() 