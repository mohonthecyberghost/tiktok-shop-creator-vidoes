# TikTok Product Scraper POC

A proof-of-concept application that scrapes product information from TikTok Shop videos. This tool allows you to extract detailed product information from TikTok videos that contain product links.

## Features

- Extract product information from TikTok Shop videos
- Web interface for easy video URL input
- Real-time processing status and progress tracking
- Detailed product information display including:
  - Product ID (with full precision)
  - Seller ID (with full precision)
  - Product title
  - Price and market price
  - Product images (with high-resolution preview)
  - Categories
  - Product status
  - Direct links to product pages
- Support for processing multiple videos in batch
- Automatic saving of results to JSON files
- JSON data viewing and downloading capabilities
- Silent operation (no audio output)
- No log file creation
- Organized JSON storage by video

## Requirements

- Python 3.8 or higher
- Chrome browser installed
- Internet connection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/TikTokShop-Intel.git
cd TikTokShop-Intel
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application using the provided batch file:
```bash
run.bat
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Enter TikTok video URLs (one per line) in the input field

4. Click "Process Videos" to start scraping

5. Monitor the progress in real-time:
   - Overall progress bar
   - Current video being processed
   - Status log with timestamps
   - Number of products found

6. View the results:
   - Product details with high-resolution images
   - Price information
   - Direct links to products
   - Category tags
   - View or download JSON data for each video

## Project Structure

```
TikTokShop-Intel/
├── app.py                 # Flask web application
├── tiktok_scraper.py      # Core scraping functionality
├── requirements.txt       # Python dependencies
├── run.bat               # Batch file to run the application
├── templates/
│   └── index.html        # Web interface template
└── product-jsons/        # Directory for JSON output files
    ├── video_*.json      # Individual video results
    └── all_products_*.json # Combined results
```

## Technical Details

### Backend
- Flask web server
- Selenium with undetected-chromedriver for web scraping
- Multi-threaded processing
- Real-time status updates
- JSON result storage
- Silent operation (no audio output)
- No log file creation

### Frontend
- Modern responsive design using Tailwind CSS
- Real-time progress tracking
- Interactive product display
- Status logging with timestamps
- Error handling and recovery
- JSON data viewing and downloading
- High-resolution image previews

### Data Extraction
- Full precision handling for product and seller IDs
- Comprehensive product information extraction
- Image URL collection
- Price and currency formatting
- Category and tag extraction
- SEO URL support

## Features

### JSON Management
- Individual JSON files for each video
- Combined JSON file for all videos
- In-browser JSON viewing
- JSON download capability
- Organized storage in product-jsons directory

### Performance Optimizations
- Silent operation (no audio output)
- No log file creation
- Efficient memory usage
- Automatic cleanup of resources

## Limitations

- Requires Chrome browser
- Processing speed depends on network conditions
- TikTok may implement rate limiting
- Some videos may require authentication

## Future Improvements

- Add authentication support
- Implement rate limiting handling
- Add export functionality for different formats
- Enhance error recovery mechanisms
- Add product image download capability
- Implement proxy support
- Add batch processing optimization

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Please respect TikTok's terms of service and use responsibly.
