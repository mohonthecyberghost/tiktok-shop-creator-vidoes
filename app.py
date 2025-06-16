from flask import Flask, render_template, request, jsonify
from tiktok_scraper import TikTokScraper
import threading
import queue
import time
from datetime import datetime
import json
import os
import glob

app = Flask(__name__)

# Global queue to store processing results
processing_queue = queue.Queue()
active_scrapers = {}
task_results = {}

def get_scraping_history():
    """Get all scraping history from JSON files."""
    history = []
    if not os.path.exists('product-jsons'):
        return history
    
    # Get all JSON files
    json_files = glob.glob('product-jsons/*.json')
    
    for file_path in json_files:
        try:
            # Get file creation time
            creation_time = os.path.getctime(file_path)
            timestamp = datetime.fromtimestamp(creation_time)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add to history
            history.append({
                'file_name': os.path.basename(file_path),
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'video_count': len(data) if isinstance(data, list) else 1,
                'total_products': sum(len(video.get('products', [])) for video in (data if isinstance(data, list) else [data])),
                'file_path': file_path
            })
        except Exception as e:
            print(f"Error reading history file {file_path}: {str(e)}")
    
    # Sort by timestamp, newest first
    return sorted(history, key=lambda x: x['timestamp'], reverse=True)

def process_videos(video_urls, task_id):
    """Process videos in a separate thread."""
    scraper = TikTokScraper()
    try:
        all_results = []
        
        # Create product-jsons directory if it doesn't exist
        if not os.path.exists('product-jsons'):
            os.makedirs('product-jsons')
        
        for i, video_url in enumerate(video_urls):
            # Update progress
            progress = {
                'status': 'processing',
                'current_video': i + 1,
                'total_videos': len(video_urls),
                'current_url': video_url,
                'results': None
            }
            processing_queue.put((task_id, progress))
            
            # Process video
            html_content = scraper.get_page_html(video_url)
            if html_content:
                products = scraper.extract_product_info(html_content)
                video_results = {
                    'video_url': video_url,
                    'products': products
                }
                all_results.append(video_results)
                
                # Save individual video results
                video_id = video_url.split('/')[-1]  # Get video ID from URL
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                video_output_file = f'product-jsons/video_{video_id}_{timestamp}.json'
                
                with open(video_output_file, 'w', encoding='utf-8') as f:
                    json.dump(video_results, f, indent=4)
            
            # Add delay between requests
            time.sleep(5)
        
        # Save combined results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'product-jsons/all_products_{timestamp}.json'
        
        # Save results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=4)
        
        # Update final progress
        final_progress = {
            'status': 'completed',
            'results': all_results,
            'output_file': output_file
        }
        processing_queue.put((task_id, final_progress))
        task_results[task_id] = final_progress
        
    except Exception as e:
        error_progress = {
            'status': 'error',
            'error': str(e)
        }
        processing_queue.put((task_id, error_progress))
        task_results[task_id] = error_progress
    finally:
        scraper.close()
        if task_id in active_scrapers:
            del active_scrapers[task_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        # Get form data
        username = request.form.get('username', '').strip()
        if username.startswith('@'):
            username = username[1:]  # Remove @ if present
        
        if not username:
            return jsonify({'error': 'No username provided'}), 400
        
        # Get video limit (default to 10 if not specified)
        try:
            video_limit = int(request.form.get('video_limit', 10))
        except ValueError:
            video_limit = 10
        
        # Initialize scraper
        scraper = TikTokScraper()
        
        try:
            # Get videos with products from creator's profile
            videos = scraper.get_creator_videos(username, None, None, limit=video_limit)
            
            # Save results to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'product-jsons/products_{username}_{timestamp}.json'
            
            # Create product-jsons directory if it doesn't exist
            os.makedirs('product-jsons', exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(videos, f, indent=4)
            
            return jsonify({
                'success': True,
                'message': f'Successfully scraped {len(videos)} videos with products from @{username}',
                'output_file': output_file
            })
            
        finally:
            scraper.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/<filename>')
def get_history_file(filename):
    """Get the content of a specific history file."""
    try:
        file_path = os.path.join('product-jsons', filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    video_urls = data.get('video_urls', [])
    
    if not video_urls:
        return jsonify({'error': 'No video URLs provided'}), 400
    
    # Generate unique task ID
    task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Initialize task results
    task_results[task_id] = {'status': 'processing'}
    
    # Start processing in a separate thread
    thread = threading.Thread(
        target=process_videos,
        args=(video_urls, task_id)
    )
    thread.daemon = True
    thread.start()
    
    active_scrapers[task_id] = thread
    
    return jsonify({'task_id': task_id})

@app.route('/status/<task_id>')
def status(task_id):
    """Check the status of a processing task."""
    # First check if we have any updates in the queue
    while not processing_queue.empty():
        current_task_id, progress = processing_queue.get()
        if current_task_id == task_id:
            task_results[task_id] = progress
            return jsonify(progress)
    
    # If no updates in queue, check task_results
    if task_id in task_results:
        return jsonify(task_results[task_id])
    
    # If task is still active but no updates
    if task_id in active_scrapers:
        return jsonify({'status': 'processing'})
    
    # Task not found
    return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)