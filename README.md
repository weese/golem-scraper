# Golem.de Article Scraper

A Python script to download articles from Golem.de for offline reading on e-readers. Designed for Golem Plus subscribers to access their subscribed content in EPUB format.

## Features

- **Google OAuth Login**: Securely log in using your Google account
- **RSS/OPML Support**: Fetch articles from RSS feeds or OPML collections
- **Full Content Download**: Downloads complete article text, images, and hyperlinks
- **EPUB Output**: Creates e-reader-friendly EPUB files
- **Batch Download**: Download multiple articles at once
- **Polite Scraping**: Includes delays between requests to be respectful to the server

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers**:
```bash
playwright install chromium
```

## Usage

### Basic Usage

Download all articles from the Softwareentwicklung RSS feed:

```bash
python golem_scraper.py
```

This will:
1. Open a browser window for Google login
2. Fetch all articles from the default feed
3. Download each article with images
4. Create an EPUB file in the `downloads/` directory

### Custom Feed URL

Download from a specific feed:

```bash
python golem_scraper.py "https://rss.golem.de/rss.php?feed=RSS2.0"
```

### Advanced Options

```bash
# Specify output filename
python golem_scraper.py -o my_articles.epub

# Limit number of articles
python golem_scraper.py -n 10

# Custom download directory
python golem_scraper.py -d ~/Documents/golem

# Show browser during login (helpful for debugging)
python golem_scraper.py --visible

# Skip login (for public articles only)
python golem_scraper.py --no-login
```

### Complete Example

```bash
python golem_scraper.py \
  "https://rss.golem.de/rss.php?ms=softwareentwicklung&feed=OPML" \
  -o softwareentwicklung.epub \
  -n 20 \
  --visible
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `feed_url` | RSS or OPML feed URL (optional, defaults to Softwareentwicklung) |
| `-o, --output` | Output EPUB filename |
| `-d, --download-dir` | Directory to save downloads (default: `downloads`) |
| `-n, --max-articles` | Maximum number of articles to download |
| `--no-login` | Skip login (only works for public articles) |
| `--visible` | Show browser window during login |

## How It Works

1. **Authentication**: Opens a browser using Playwright and navigates to the Golem.de login page. You manually authenticate via Google OAuth, and the script captures the session cookies.

2. **Feed Parsing**: Fetches the RSS or OPML feed and extracts article URLs.

3. **Content Download**: For each article:
   - Downloads the full HTML content
   - Extracts the main article text
   - Downloads all images
   - Preserves hyperlinks

4. **EPUB Creation**: Packages everything into a well-formatted EPUB file with:
   - Table of contents
   - Embedded images
   - Proper styling for e-readers
   - Article metadata (author, date, source URL)

## Output Format

The generated EPUB files include:

- **Article Title** as chapter heading
- **Author and Date** (when available)
- **Source URL** for reference
- **Full Article Text** with formatting preserved
- **Embedded Images** properly sized for e-readers
- **Hyperlinks** to external resources
- **Table of Contents** for easy navigation

## Troubleshooting

### Login Issues

- Use `--visible` flag to see what's happening during login
- Make sure you complete the Google authentication in the browser window
- The script will wait up to 2 minutes for login completion

### Missing Content

- Ensure you're logged in with a Golem Plus account
- Some articles may have different HTML structures
- Check the console output for specific errors

### Playwright Installation

If you get errors about Playwright browsers:

```bash
playwright install chromium
```

## Legal Notice

This script is intended for **personal use only** by legitimate Golem Plus subscribers. It helps you access content you've already paid for in a format suitable for offline reading on e-readers.

Please respect Golem.de's terms of service and use this tool responsibly:
- Only for personal, non-commercial use
- Do not redistribute downloaded content
- Do not circumvent paywalls for content you haven't subscribed to
- Be respectful with request rates (delays are built-in)

## License

This script is provided as-is for personal use. Use at your own risk.

## Support

For issues with:
- **Your Golem.de subscription**: Contact account@golem.de
- **This script**: Check the console output for error messages

