# Golem.de Article Scraper

A Python script to download articles from Golem.de for offline reading on e-readers. Designed for Golem Plus subscribers to access their subscribed content in clean, well-formatted EPUB files.

## Features

- **Topic-Based Downloads**: Simply specify a topic (e.g., `security`, `ki`, `softwareentwicklung`)
- **Plus Archive Download**: Download all articles from the Golem Plus archive page in one command
- **Google OAuth Login**: Securely log in using your Google account with persistent sessions
- **Multi-Page Article Support**: Automatically follows pagination to download complete articles
- **Full Content Download**: Downloads complete article text, images, and hyperlinks
- **Clean EPUB Output**: E-reader-friendly EPUB files with:
  - Embedded images
  - Monospace fonts for code blocks
  - German date formatting
  - Source links
  - No ads, navigation, or clutter
- **Session Persistence**: Login once, then use headless mode for automated downloads
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

### Quick Start

Download security articles (default: 1 article):

```bash
python golem_scraper.py security
```

Download 10 articles on AI/Machine Learning:

```bash
python golem_scraper.py ki -n 10
```

Download software development articles (default topic):

```bash
python golem_scraper.py -n 5
```

### Available Topics

Popular Golem.de topics you can use:
- `security` - Security & cybersecurity news
- `softwareentwicklung` - Software development (default)
- `ki` - AI & Machine Learning
- `internet` - Internet & web news
- `mobil` - Mobile devices
- `wissenschaft` - Science & technology
- `plus-archive` - All articles from the Golem Plus archive page

### Advanced Options

```bash
# Download all articles from Golem Plus archive
python golem_scraper.py plus-archive -n 20

# Custom output filename
python golem_scraper.py security -o my_security_articles.epub

# Custom download directory
python golem_scraper.py ki -d ~/Documents/golem

# Headless mode (requires existing login session)
python golem_scraper.py security -n 10 --headless

# Debug mode (shows cookies, URLs, etc.)
python golem_scraper.py security -n 2 --debug

# Skip login (for public articles only)
python golem_scraper.py --no-login -n 5
```

### Session Persistence & Headless Mode

The script saves your login session, so you only need to log in once:

1. **First run** (visible browser for login):
```bash
python golem_scraper.py security -n 10
```

2. **Subsequent runs** (headless mode, no browser window):
```bash
python golem_scraper.py ki -n 10 --headless
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `topic` | Topic to download (e.g., security, ki, plus-archive). Default: softwareentwicklung |
| `-o, --output` | Output EPUB filename (default: `golem_{topic}_{timestamp}.epub`) |
| `-d, --download-dir` | Directory to save downloads (default: `downloads`) |
| `-n, --max-articles` | Maximum number of articles to download (default: 1) |
| `--no-login` | Skip login (only works for public articles) |
| `--headless` | Run browser in headless mode (requires existing login session) |
| `--cookies` | Path to JSON file with cookies (alternative to automated login) |
| `--debug` | Enable debug output |

## How It Works

1. **Authentication**: Opens a browser using Playwright and navigates to the Golem.de login page. You manually authenticate via Google OAuth, and the script saves the session cookies to `downloads/browser_profile/`.

2. **Feed Construction**: Builds the RSS feed URL from the topic (e.g., `security` → `https://rss.golem.de/rss.php?ms=security`)

3. **Content Download**: For each article:
   - Downloads the full HTML content
   - Follows pagination links to get complete multi-page articles
   - Downloads all images
   - Removes ads, navigation, teaser blocks, and other clutter
   - Preserves hyperlinks and code blocks

4. **EPUB Creation**: Packages everything into a clean EPUB file with:
   - Table of contents
   - Embedded images
   - Monospace fonts for code blocks
   - German date formatting (e.g., "29. Oktober 2025, 10:36 Uhr")
   - Source link at the end of each article
   - Optimized styling for e-readers

## Output Format

The generated EPUB files include:

- **Clean Article Layout**: Starts directly with the article's own header (no metadata duplication)
- **Multi-Page Articles**: All pages automatically combined into one chapter
- **German Dates**: Human-friendly date format (e.g., "1. November 2025, 14:30 Uhr")
- **Code Blocks**: Properly formatted with monospace fonts and gray backgrounds
- **Embedded Images**: All images downloaded and included
- **Source Link**: Clickable link at the end of each article
- **Table of Contents**: Easy navigation between articles
- **Topic in Filename**: e.g., `golem_security_20251101_143052.epub`

## Troubleshooting

### Login Issues

- The browser should open automatically - complete the Google authentication
- If you see "This browser may not be secure" from Google, the script uses workarounds to appear as a regular browser
- Session cookies are saved, so you only need to log in once
- Use `--debug` flag to see detailed login information

### Headless Mode Issues

- Headless mode (`--headless`) only works if you've logged in before
- First login must be done with a visible browser (without `--headless`)
- After that, use `--headless` for automated downloads

### Missing Content

- Ensure you're logged in with a Golem Plus account
- Some articles may require manual cookie consent - accept it in the browser
- Check the console output for specific errors
- Use `--debug` flag for detailed information

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

