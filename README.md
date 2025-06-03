# Oxford Educate PDF Downloader

A Python script to download and convert Oxford Educate ebooks to PDF format.

## Features

- Downloads ebooks from Oxford Educate platform
- Converts SVG and image content to PDF
- Maintains table of contents
- Handles encrypted content
- Sanitizes filenames for compatibility

## Prerequisites

- Python 3.6 or higher
- Valid Oxford Educate account and cookies

## Installation

1. Clone the repository:
```bash
git clone https://github.com/coregopal/oxford-downloader.git
cd oxford-downloader
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Get your cookies from Oxford Educate:
   - Log in to your Oxford Educate account
   - Open browser developer tools (F12)
   - Go to Network tab
   - Find any request to oxfordeducate.in
   - Copy the Cookie header value

2. Create a `cookies.txt` file in the project directory and paste your cookies:
```bash
echo "your_cookie_string" > cookies.txt
```

3. Run the script with your book ID:
```bash
python oxford.py
```

To download a specific book, modify the `BOOKID` in `oxford.py`:
```python
if __name__ == "__main__":
    BOOKID = "your_book_id"  # Replace with your book ID
    oxford_instance = Oxford(BOOKID)
    oxford_instance.download_ebook()
```

## How it Works

1. The script authenticates using your cookies
2. Fetches the book metadata and content structure
3. Downloads each page as SVG or image
4. Converts the content to PDF format
5. Adds table of contents
6. Saves the final PDF with sanitized filename

## Troubleshooting

- If you get SSL errors, the script automatically disables SSL verification
- If the PDF fails to save, check if the filename contains invalid characters
- Make sure your cookies are valid and not expired

## Security Note

- Keep your `cookies.txt` file secure and never share it
- The script disables SSL verification for compatibility, use with caution
- Consider using a virtual environment for isolation

## License

This project is for educational purposes only. Use responsibly and respect copyright laws.


