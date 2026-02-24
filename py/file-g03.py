import requests


class MediaProcessor:
    def process_media(self, urls):
        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()  # Raise an HTTPError for bad responses
                # Process the response here
                print(f"Processing {url}")
            except requests.exceptions.HTTPError as e:
                print(f"404 Error: {e} - URL not found: {url}. Continuing to next media source.")
            except Exception as e:
                print(f"An error occurred: {e} - URL: {url}")
                

# Example usage:
urls = [
    'http://example.com/media1',  # This may cause a 404
    'http://example.com/media2',  # This may also cause a 404
]
processor = MediaProcessor()
processor.process_media(urls)