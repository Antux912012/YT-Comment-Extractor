from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import csv
import io
import random
import json
import re
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime, timedelta

try:
    from youtube_comment_downloader import YoutubeCommentDownloader
    YOUTUBE_COMMENT_DOWNLOADER_AVAILABLE = True
except ImportError:
    YOUTUBE_COMMENT_DOWNLOADER_AVAILABLE = False
    print("Warning: youtube_comment_downloader not available, will use fallback methods")

app = Flask(__name__)

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    try:
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc:
            if 'v' in parse_qs(parsed.query):
                return parse_qs(parsed.query)['v'][0]
            if '/shorts/' in parsed.path or '/live/' in parsed.path:
                return parsed.path.split('/')[-1]
        elif 'youtu.be' in parsed.netloc:
            return parsed.path.strip('/').split('?')[0]
    except Exception as e:
        print(f"Error extracting video ID: {e}")
    return None

def parse_relative_date_text(text):
    """Parse relative time strings like '2 days ago', '1 week ago' into a date"""
    if not text:
        return None
    
    value = text.strip().lower()
    
    if value == 'today':
        return datetime.utcnow()
    if value == 'yesterday':
        return datetime.utcnow() - timedelta(days=1)
    
    # Match patterns like "2 days ago", "1 week ago", "3 months ago"
    match = re.search(r'(\d+)\s*(second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s+ago', value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'second': 1, 'seconds': 1,
            'minute': 60, 'minutes': 60,
            'hour': 3600, 'hours': 3600,
            'day': 86400, 'days': 86400,
            'week': 604800, 'weeks': 604800,
            'month': 2592000, 'months': 2592000,  # Approximate
            'year': 31536000, 'years': 31536000,
        }
        
        seconds = amount * multipliers.get(unit, 0)
        return datetime.utcnow() - timedelta(seconds=seconds)
    
    # Try to parse as date directly (e.g., "Aug 1, 2023")
    try:
        # Attempt to parse various date formats
        for fmt in ['%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    except:
        pass
    
    return None

def parse_comment_date_value(value):
    """Parse various date formats into DD-MM-YYYY"""
    if value is None or value == '':
        return ''
    
    # Handle dictionaries (YouTube API style with simpleText or runs)
    if isinstance(value, dict):
        extracted = value.get('simpleText')
        if not extracted and 'runs' in value:
            extracted = ''.join([run.get('text', '') for run in value.get('runs', [])])
        if extracted:
            return parse_comment_date_value(extracted)
        return ''
    
    # Handle numeric timestamps (from yt-dlp or youtube-comment-downloader)
    if isinstance(value, (int, float)):
        try:
            timestamp = int(value)
            # Handle milliseconds vs seconds
            if timestamp > 10**12:
                timestamp = timestamp / 1000
            return datetime.utcfromtimestamp(timestamp).strftime('%d-%m-%Y')
        except Exception:
            return ''
    
    value = str(value).strip()
    if not value:
        return ''
    
    # Check if it's all digits (Unix timestamp as string)
    if value.isdigit():
        try:
            timestamp = int(value)
            if timestamp > 10**12:
                timestamp = timestamp / 1000
            return datetime.utcfromtimestamp(timestamp).strftime('%d-%m-%Y')
        except:
            pass
    
    # Try ISO format
    try:
        iso_value = value.replace('Z', '+00:00')
        dt = datetime.fromisoformat(iso_value)
        return dt.strftime('%d-%m-%Y')
    except:
        pass
    
    # Try standard formats
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d-%m-%Y']:
        try:
            return datetime.strptime(value, fmt).strftime('%d-%m-%Y')
        except:
            pass
    
    # Try relative dates (e.g., "2 days ago")
    relative = parse_relative_date_text(value)
    if relative:
        return relative.strftime('%d-%m-%Y')
    
    return str(value)  # Return as-is if we can't parse

def get_comment_date(comment):
    """Extract date from comment dict checking various field names"""
    if not isinstance(comment, dict):
        return ''
    
    # Check various possible date field names from different sources
    date_keys = [
        'timestamp',           # yt-dlp Unix timestamp
        'time_parsed',         # youtube-comment-downloader Unix timestamp
        'publishedAt',         # YouTube API ISO format
        'published_at',
        'date',
        'time',                # Relative text like "2 days ago"
        'created_at',
        'publishedTime',
        'publishedTimeText',
        'createdTime',
    ]
    
    for key in date_keys:
        if key in comment and comment[key] is not None:
            parsed = parse_comment_date_value(comment[key])
            if parsed:
                return parsed
    
    return ''

def extract_total_comments(video_url):
    """Get total comment count from video metadata"""
    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info and 'comment_count' in info:
                return info['comment_count']
    except Exception as e:
        print(f"Could not extract total comment count: {e}")
    return 0

def get_comments(video_url, max_comments=None):
    """Extract comments using multiple methods"""
    video_id = extract_video_id(video_url)
    if not video_id:
        return []
    
    print(f"Processing video ID: {video_id}")
    all_comments = []
    
    # Method 1: youtube-comment-downloader (fastest for top comments)
    if YOUTUBE_COMMENT_DOWNLOADER_AVAILABLE:
        try:
            print("[Attempting Method 1] youtube-comment-downloader...")
            comments = extract_with_downloader(video_id, max_comments)
            if comments:
                all_comments.extend(comments)
                print(f"✅ Method 1 success: {len(comments)} comments")
                if max_comments and len(all_comments) >= max_comments:
                    return all_comments[:max_comments]
        except Exception as e:
            print(f"❌ Method 1 failed: {e}")
    
    # Method 2: yt-dlp (most reliable for timestamp data)
    if not all_comments or len(all_comments) < 10:
        try:
            print("[Attempting Method 2] yt-dlp extraction...")
            comments = extract_with_ytdlp(video_url, max_comments)
            if comments:
                all_comments.extend(comments)
                print(f"✅ Method 2 success: {len(comments)} comments")
        except Exception as e:
            print(f"❌ Method 2 failed: {e}")
    
    return all_comments

def extract_with_downloader(video_id, max_comments=None):
    """Extract using youtube-comment-downloader"""
    comments = []
    try:
        downloader = YoutubeCommentDownloader()
        comments_gen = downloader.get_comments_from_url(f"https://www.youtube.com/watch?v={video_id}")
        
        count = 0
        for comment in comments_gen:
            try:
                text = comment.get('text', '').strip()
                if not text or len(text) <= 2:
                    continue
                
                # Debug: Print available keys to console (remove after testing)
                # print(f"Comment keys: {comment.keys()}")
                
                comment_date = get_comment_date(comment)
                if not comment_date:
                    # Fallback: try to extract from 'time' field directly
                    time_str = comment.get('time', '')
                    comment_date = parse_comment_date_value(time_str)
                
                comments.append({
                    'nickname': comment.get('author', 'Anonymous'),
                    'date': comment_date or 'Unknown',
                    'comment': text[:1000]
                })
                
                count += 1
                if max_comments and count >= max_comments:
                    break
                    
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Downloader error: {e}")
        raise Exception(f"Downloader error: {str(e)}")
    
    return comments

def extract_with_ytdlp(video_url, max_comments=None):
    """Extract using yt-dlp - most accurate for dates"""
    comments = []
    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'getcomments': True,
            'extractor_args': {
                'youtube': {
                    'max_comments': ['all', 'all', 'all', 'all']  # top, recent, replies, hearted
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info and 'comments' in info:
                raw_comments = info['comments']
                print(f" Found {len(raw_comments)} comments from yt-dlp")
                
                for i, comment in enumerate(raw_comments):
                    try:
                        text = comment.get('text', '').strip()
                        if not text:
                            continue
                        
                        # Get date - yt-dlp provides 'timestamp' (Unix)
                        comment_date = get_comment_date(comment)
                        
                        # Fallback if get_comment_date didn't find it
                        if not comment_date and 'timestamp' in comment:
                            comment_date = parse_comment_date_value(comment['timestamp'])
                        
                        comments.append({
                            'nickname': comment.get('author', 'Anonymous'),
                            'date': comment_date or 'Unknown',
                            'comment': text[:1000]
                        })
                        
                        if max_comments and len(comments) >= max_comments:
                            break
                            
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"yt-dlp error: {e}")
    
    return comments

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    """API endpoint to extract comments"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        video_url = data.get('url', '').strip()
        num_comments = data.get('num_comments', 100)
        
        if not video_url:
            return jsonify({'error': 'Please provide a valid YouTube URL'}), 400
        
        try:
            num_comments = int(num_comments)
            num_comments = max(1, min(num_comments, 1000))
        except:
            num_comments = 100
        
        total_available = extract_total_comments(video_url)
        print(f"Video reports {total_available} total comments")
        
        # Get comments
        all_comments = get_comments(video_url, max_comments=num_comments)
        
        if not all_comments:
            return jsonify({
                'error': 'No comments found. This may be because:\n'
                         '1. Comments are disabled\n'
                         '2. The video is private/restricted\n'
                         '3. The video has no comments yet'
            }), 404
        
        # If we have more than requested, randomly sample
        if len(all_comments) > num_comments:
            selected = random.sample(all_comments, num_comments)
        else:
            selected = all_comments
        
        print(f"Returning {len(selected)} comments")
        
        # Debug: Check if dates are present
        sample_with_date = sum(1 for c in selected if c.get('date') and c['date'] != 'Unknown')
        print(f"Comments with dates: {sample_with_date}/{len(selected)}")
        
        return jsonify({
            'success': True,
            'comments': selected,
            'count': len(selected),
            'total_available': total_available or len(all_comments),
            'message': f'Successfully extracted {len(selected)} comments'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """Download comments as CSV - NOW WITH DATE COLUMN"""
    try:
        data = request.get_json()
        comments = data.get('comments', [])
        
        if not comments:
            return jsonify({'error': 'No comments to download'}), 400
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter='|', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # FIXED: Added 'Date' to header
        writer.writerow(['Nickname', 'Date', 'Comment'])
        
        # FIXED: Added date to each row
        for comment in comments:
            writer.writerow([
                comment.get('nickname', 'Anonymous'),
                comment.get('date', 'Unknown'),
                comment.get('comment', '')
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'youtube_comments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error creating CSV: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
