# YouTube Comments Extractor

A simple web application to extract random 100 comments from any YouTube video and export them as a CSV file with pipe delimiter (`|`).

## Features

- 🎯 **Search Engine-like Interface**: Clean, intuitive design similar to Google search
- 📝 **Easy Comment Extraction**: Just paste a YouTube video link
- 📊 **CSV Export**: Download comments with columns: Nickname, Date, Comment, Has Replies (Y/N)
- 📋 **Copy to Clipboard**: Copy extracted comments directly to clipboard
- 🎲 **Random Selection**: Randomly selects 100 comments from available ones
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices

## Project Structure

```
YT_Comments_Export_Random/
├── app.py                 # Flask backend application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # HTML frontend
└── static/
    ├── style.css         # CSS styling
    └── script.js         # JavaScript functionality
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/YT_Comments_Export_Random
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your browser:**
   - Navigate to `http://localhost:5000`

3. **Using the application:**
   - Copy a YouTube video link (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
   - Paste it in the search box
   - Click "Extract Comments"
   - View the results in the table below
   - Download as CSV or copy to clipboard

## Supported YouTube URL Formats

The application supports standard YouTube URLs:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`
- `https://www.youtube.com/watch?v=VIDEO_ID&t=123`

## CSV Export Format

The CSV file uses pipe (`|`) as delimiter with the following columns:

```
Nickname|Date|Comment|Has Replies
User123|3 months ago|Great video!|Y
User456|2 months ago|Thanks for sharing|N
```

## Features in Detail

### Extract Comments
- Connects to YouTube using yt-dlp library
- Extracts available comments from the video
- Randomly selects up to 100 comments
- Displays results in an easy-to-read table

### Download CSV
- Creates a properly formatted CSV file with pipe delimiters
- Filename includes timestamp: `youtube_comments_YYYYMMDD_HHMM.csv`
- Opens download dialog automatically

### Copy to Clipboard
- Copies all comments in CSV format
- Includes visual feedback (button changes to "✓ Copied!")
- Ready to paste into spreadsheets or text editors

## Limitations

- Only extracts comments if the video has comments enabled
- Some videos may have restricted comment access
- Comment extraction speed depends on video's comment count and internet connection
- YouTube may have rate limiting for large-scale extraction

## Troubleshooting

### "Could not extract comments" error
- Check if the video has comments enabled
- Try another video to verify the tool works
- Ensure your internet connection is stable

### Port already in use
- Change the port in `app.py` (default is 5000)
- Or stop other applications using port 5000

### Dependencies installation fails
- Make sure you're using Python 3.7+
- Try upgrading pip: `pip install --upgrade pip`
- Delete `requirements.txt` and reinstall specific packages

## Dependencies

- **Flask** - Web framework
- **yt-dlp** - YouTube content downloader and extractor
- **requests** - HTTP library (for yt-dlp)

## License

This project is provided as-is for educational and personal use.

## Notes

- Large comment extractions may take a few moments
- Videos with disabled comments won't return any results
- The application stores comments in memory during extraction
- No data is stored on the server permanently

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are installed correctly
3. Try restarting the Flask server
4. Check your internet connection
