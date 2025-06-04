import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import shutil # Import shutil for rmtree

def scrape_data(keyword):
    """
    Scrapes data (prices, headlines, descriptions, images, videos) from a given
    URL or a Google search result for a keyword.
    The scraped data is saved into a uniquely named folder.
    """
    # Create a unique folder for each scrape operation
    # Using a relative path within the current working directory
    # Ensure the folder name is safe for file systems by removing invalid characters
    sanitized_keyword = re.sub(r'[\\/*?:"<>|]', '', keyword).replace(' ', '_')
    folder = os.path.join("scraped_data", sanitized_keyword)

    # Clean up previous scrape data for the same keyword if it exists
    # This ensures fresh data for each request and prevents accumulation of old files.
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder, exist_ok=True)

    # Determine if the keyword is a URL or a search query
    # If it starts with "http", treat it as a direct URL; otherwise, perform a Google search.
    url = keyword if keyword.startswith("http") else f"https://www.google.com/search?q={keyword}"
    
    try:
        # Make a request to the URL with a user-agent header to mimic a browser.
        # This can help avoid some website blocking.
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- Scrape Prices ---
        # Finds patterns like "₹1,234" or "$9.99" in the entire response text.
        prices = re.findall(r"₹[0-9,]+|\$[0-9.]+", response.text)
        with open(os.path.join(folder, "price.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(prices or ["No prices found."]))

        # --- Scrape Headlines ---
        # Finds all h1, h2, or h3 tags and extracts their text.
        # Changed .docx to .txt as we are writing plain text content.
        headlines = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
        with open(os.path.join(folder, "headline.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(headlines or ["No headlines found."]))

        # --- Scrape Paragraphs (Descriptions) ---
        # Finds all <p> tags and extracts their text, limiting to the first 20.
        # Changed .docx to .txt as we are writing plain text content.
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')][:20] 
        with open(os.path.join(folder, "description.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(paragraphs or ["No descriptions found."]))

        # --- Scrape Images (up to 5) ---
        img_tags = soup.find_all('img')
        for idx, img in enumerate(img_tags[:5]): # Limit to first 5 images
            src = img.get('src')
            if src:
                # Construct absolute URL for images using urljoin for robustness.
                img_url = urljoin(url, src)
                try:
                    # Download image content.
                    img_data = requests.get(img_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).content
                    with open(os.path.join(folder, f"image{idx+1}.jpg"), "wb") as img_file:
                        img_file.write(img_data)
                except requests.exceptions.RequestException as img_e:
                    print(f"Failed to download image {img_url}: {img_e}")
                except Exception as img_e:
                    print(f"Error saving image {img_url}: {img_e}")

        # --- Scrape Videos (up to 3) ---
        video_sources = []
        # Find video tags directly
        video_tags = soup.find_all('video')
        for vid in video_tags:
            if vid.get('src'):
                video_sources.append(vid.get('src'))
            # Check for source tags within video tags (e.g., <video><source src="...">)
            for source_tag in vid.find_all('source'):
                if source_tag.get('src'):
                    video_sources.append(source_tag.get('src'))
        
        # Also look for common video file extensions in <a> tags (links to video files)
        a_tags_with_videos = soup.find_all('a', href=re.compile(r'\.(mp4|webm|ogg|mov|avi)$', re.IGNORECASE))
        for a_tag in a_tags_with_videos:
            if a_tag.get('href'):
                video_sources.append(a_tag.get('href'))

        video_sources = list(set(video_sources)) # Remove duplicate URLs

        for idx, video_src in enumerate(video_sources[:3]): # Limit to first 3 videos
            if video_src:
                # Construct absolute URL for videos.
                video_url = urljoin(url, video_src)
                try:
                    # Determine file extension from the URL.
                    parsed_video_url = urlparse(video_url)
                    video_ext = os.path.splitext(parsed_video_url.path)[1]
                    if not video_ext: # Default to .mp4 if no extension found in URL
                        video_ext = ".mp4" 
                    
                    # Download video content.
                    video_data = requests.get(video_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}).content
                    with open(os.path.join(folder, f"video{idx+1}{video_ext}"), "wb") as video_file:
                        video_file.write(video_data)
                except requests.exceptions.RequestException as video_e:
                    print(f"Failed to download video {video_url}: {video_e}")
                except Exception as video_e:
                    print(f"Error saving video {video_url}: {video_e}")

    except requests.exceptions.RequestException as e:
        # Catch network-related or HTTP errors during the main request.
        print(f"Network or HTTP error during scraping: {e}")
        # Create an error file to inform the user about the failure.
        with open(os.path.join(folder, "error.txt"), "w", encoding="utf-8") as f:
            f.write(f"Scraping failed due to network or HTTP error: {e}")
    except Exception as e:
        # Catch any other unexpected errors during the scraping process.
        print(f"An unexpected error occurred during scraping: {e}")
        with open(os.path.join(folder, "error.txt"), "w", encoding="utf-8") as f:
            f.write(f"Scraping failed due to an unexpected error: {e}")

    # Return the path to the folder containing scraped data.
    # The zip_and_send function will then handle zipping and sending.
    return folder
          
