import os
import logging
import asyncio
import tempfile
from jinja2 import Environment, FileSystemLoader
import pdfkit
import base64
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import List, Dict, Optional

class ModernPDFGenerator:
    def __init__(self, output_dir='generated_invoices', max_workers=None):
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Basic setup
        self.output_dir = output_dir
        self.max_workers = max_workers or min(16, (os.cpu_count() or 1) * 2)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Setup project paths
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.templates_dir = os.path.join(self.project_root, 'templates')
        self.logo_path = os.path.join(self.project_root, 'assets', 'TODC-Horizontal.png')
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True,
            cache_size=1000,
            auto_reload=False,  # Disable in production
            optimized=True
        )
        
        # Cache the template
        self.template = self.env.get_template('invoice_template.html')
        
        # Cache the logo
        self._logo_data = None
        
        # PDF options for wkhtmltopdf - removed landscape orientation
        self.pdf_options = {
            'page-size': 'Letter',
            'orientation': 'Landscape',
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': True,
            'print-media-type': None,
            'enable-smart-shrinking': None,
            'javascript-delay': '1000',
            'quiet': None
        }

        
        
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix='pdf_worker'
        )

    @property
    def logo_data(self) -> Optional[str]:
        """Cached logo data"""
        if self._logo_data is None:
            self._logo_data = self.get_base64_logo()
        return self._logo_data

    def get_base64_logo(self) -> Optional[str]:
        """Convert logo to base64 string"""
        try:
            with open(self.logo_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
                return f'data:image/png;base64,{encoded_string}'
        except Exception as e:
            self.logger.error(f"Error encoding logo: {str(e)}")
            return None

    def generate_pdf(self, data: Dict) -> Optional[str]:
        """Generate single PDF synchronously"""
        try:
            # Use template data with cached logo
            template_data = {
                'data': data,
                'logo_base64': self.logo_data
            }
            
            # Generate HTML
            html_content = self.template.render(**template_data)
            
            # Create output file path
            output_file = os.path.join(
                self.output_dir, 
                f"{data['name']}.pdf"
            )
            
            self.logger.info(f"Generating PDF for {data['name']}")
            
            # Generate PDF with optimized settings
            pdfkit.from_string(
                html_content,
                output_file,
                options=self.pdf_options
            )
            
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"PDF file was not created: {output_file}")
                
            self.logger.info(f"Successfully generated PDF: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error generating PDF for {data.get('name', 'Unknown')}: {str(e)}")
            return None

    async def generate_pdfs_batch(self, data_list: List[Dict], batch_size=5) -> List[str]:
        """Generate PDFs in optimized batches"""
        all_results = []
        
        # Process in smaller batches to optimize memory usage
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.generate_pdf_async(data) for data in batch]
            )
            all_results.extend([r for r in batch_results if r])
            
            # Small delay to prevent CPU spikes
            await asyncio.sleep(0.1)
        
        return all_results

    async def generate_pdf_async(self, data: Dict) -> Optional[str]:
        """Asynchronous PDF generation for single file"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._generate_pdf_sync,
                data
            )
        except Exception as e:
            self.logger.error(f"Async PDF generation failed for {data.get('name')}: {str(e)}")
            return None

    def _generate_pdf_sync(self, data: Dict) -> Optional[str]:
        """Synchronous PDF generation with optimizations"""
        try:
            # Use template data with cached logo
            template_data = {
                'data': data,
                'logo_base64': self.logo_data
            }
            
            # Generate HTML
            html_content = self.template.render(**template_data)
            
            # Create output file path
            output_file = os.path.join(
                self.output_dir, 
                f"{data['name']}.pdf"
            )
            
            self.logger.info(f"Generating PDF for {data['name']}")
            
            # Generate PDF with optimized settings
            pdfkit.from_string(
                html_content,
                output_file,
                options=self.pdf_options
            )
            
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"PDF file was not created: {output_file}")
                
            self.logger.info(f"Successfully generated PDF: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"PDF generation failed for {data.get('name')}: {str(e)}")
            return None

    def __del__(self):
        """Cleanup resources"""
        try:
            # Clean up temp directory
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
            
            # Shutdown executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Cleanup failed: {str(e)}")
            else:
                print(f"Cleanup failed: {str(e)}")