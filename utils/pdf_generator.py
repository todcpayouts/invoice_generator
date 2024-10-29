# utils/pdf_generator.py
import os
from jinja2 import Environment, FileSystemLoader
import pdfkit
import base64

class ModernPDFGenerator:
    def __init__(self, output_dir='generated_invoices'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup project paths
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.templates_dir = os.path.join(self.project_root, 'templates')
        self.logo_path = os.path.join(self.project_root, 'assets', 'TODC-Horizontal.png')
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True
        )
        
        # PDF options for wkhtmltopdf
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

    def get_base64_logo(self):
        """Convert logo to base64 string"""
        try:
            with open(self.logo_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
                return f'data:image/png;base64,{encoded_string}'
        except Exception as e:
            print(f"Error encoding logo: {str(e)}")
            return None

    def generate_pdf(self, data):
        """Generate PDF for a single owner's data"""
        try:
            # Get logo as base64
            logo_data = self.get_base64_logo()
            
            # Prepare template data
            template_data = {
                'data': data,
                'logo_base64': logo_data
            }
            
            # Render HTML
            template = self.env.get_template('invoice_template.html')
            html_content = template.render(**template_data)
            
            # Generate PDF
            output_file = os.path.join(
                self.output_dir, 
                f"{self.sanitize_filename(data['name'])}.pdf"
            )
            
            pdfkit.from_string(
                html_content,
                output_file,
                options=self.pdf_options
            )
            
            print(f"Generated PDF for {data['name']}")
            return output_file
            
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            raise

    def sanitize_filename(self, name):
        """Convert name to valid filename"""
        invalid_chars = '<>:"/\\|?*'
        filename = ''.join(c if c not in invalid_chars else '_' for c in name)
        return f"{filename}_invoice.pdf"