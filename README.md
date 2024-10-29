# Invoice Generator

## Overview
Professional PDF invoice generator for The On Demand Company. Generates beautifully formatted invoices from Google Sheets data.

## Features
- 🎨 Professional HTML/CSS template
- 📊 Google Sheets integration
- 📑 PDF generation with proper styling
- 🖼️ Logo integration
- 📱 Responsive design
- 💼 Business-ready formatting

## Project Structure
```
invoice_generator/
├── assets/
│   └── TODC-Horizontal.png
├── templates/
│   └── invoice_template.html
├── utils/
│   ├── __init__.py
│   ├── sheets_helper.py
│   ├── invoice_processor.py
│   └── pdf_generator.py
├── main.py
└── generated_invoices/
```

## Setup
1. Install dependencies:
```bash
pip install jinja2 pdfkit pandas google-api-python-client
```

2. System requirements:
- Python 3.7+
- wkhtmltopdf
- Google Sheets API credentials

3. Configuration:
- Place Google Sheets credentials in project root
- Add logo to assets folder
- Configure output directory in main.py

## Usage
```bash
python main.py
```

## Features
- Professional invoice layout
- Automated data processing
- Customizable styling
- Error handling
- Batch processing support

## Version History
- v1.0.0-polish: Professional template with enhanced styling
  - Polished visual design
  - Improved data presentation
  - Professional formatting
  - Optimized PDF generation

## Maintenance
- Generated PDFs are saved in `generated_invoices/`
- Logs are available for debugging
- Easy to customize templates

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
Proprietary - The On Demand Company