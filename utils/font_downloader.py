# font_downloader.py
import os
import urllib.request
from typing import Dict

class FontDownloader:
    def __init__(self):
        self.fonts_dir = 'fonts'
        self.font_urls: Dict[str, str] = {
            'Roboto-Regular': 'https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf',
            'Roboto-Bold': 'https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf',
            'Roboto-Light': 'https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Light.ttf',
            # Updated Montserrat URLs
            'Montserrat-Regular': 'https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf',
            'Montserrat-Bold': 'https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf',
            # Open Sans URLs (these work fine)
            'OpenSans-Regular': 'https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Regular.ttf',
            'OpenSans-Bold': 'https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf'
        }

    def create_fonts_directory(self) -> None:
        """Create fonts directory if it doesn't exist"""
        if not os.path.exists(self.fonts_dir):
            print(f"Creating fonts directory at {self.fonts_dir}")
            os.makedirs(self.fonts_dir, exist_ok=True)

    def get_font_path(self, font_name: str) -> str:
        """Get the local path for a font file"""
        return os.path.join(self.fonts_dir, f"{font_name}.ttf")

    def is_font_downloaded(self, font_name: str) -> bool:
        """Check if a font is already downloaded"""
        return os.path.exists(self.get_font_path(font_name))

    def download_single_font(self, font_name: str, url: str) -> bool:
        """Download a single font file"""
        font_path = self.get_font_path(font_name)
        try:
            print(f"Downloading {font_name}...")
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Successfully downloaded {font_name}")
            return True
        except Exception as e:
            print(f"Error downloading {font_name}: {str(e)}")
            if os.path.exists(font_path):
                os.remove(font_path)  # Clean up partial downloads
            return False

    def download_fonts(self) -> Dict[str, bool]:
        """Download all fonts and return status dictionary"""
        self.create_fonts_directory()
        download_status = {}

        for font_name, url in self.font_urls.items():
            if self.is_font_downloaded(font_name):
                print(f"{font_name} already exists, skipping download")
                download_status[font_name] = True
                continue

            download_status[font_name] = self.download_single_font(font_name, url)

        # Print summary of downloads
        print("\nDownload Summary:")
        successful_downloads = sum(1 for success in download_status.values() if success)
        print(f"Successfully downloaded {successful_downloads} of {len(self.font_urls)} fonts")
        
        return download_status

    def get_downloaded_fonts(self) -> list:
        """Get list of successfully downloaded fonts"""
        return [font for font in self.font_urls.keys() 
                if self.is_font_downloaded(font)]

    def cleanup_failed_downloads(self):
        """Remove any partially downloaded font files"""
        for font_name in self.font_urls.keys():
            font_path = self.get_font_path(font_name)
            if os.path.exists(font_path) and os.path.getsize(font_path) == 0:
                os.remove(font_path)
                print(f"Removed incomplete download: {font_name}")

if __name__ == "__main__":
    # Test the font downloader
    downloader = FontDownloader()
    status = downloader.download_fonts()
    
    print("\nDetailed Download Status:")
    for font, success in status.items():
        print(f"{font}: {'✓' if success else '✗'}")
    
    print("\nAvailable fonts:")
    for font in downloader.get_downloaded_fonts():
        print(f"- {font}")
    
    # Clean up any failed downloads
    downloader.cleanup_failed_downloads()