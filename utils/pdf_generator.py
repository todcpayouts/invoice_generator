from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.colors import HexColor
import os

class PDFInvoiceGenerator:
    def __init__(self, output_dir='generated_invoices'):
        self.output_dir = output_dir
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        self.brand_colors = {
            'primary': HexColor('#1B5E20'),      # Darker green for main elements
            'table_header': HexColor('#2E7D32'),  # Slightly lighter green for headers
            'highlight': HexColor('#43A047'),     # Medium green for highlights
            'accent': HexColor('#F1F8E9'),       # Very light green for backgrounds
            'text': HexColor('#212121'),         # Darker text for better readability
            'negative': HexColor('#C62828'),     # Professional red for negative values
            'positive': HexColor('#2E7D32')      # Professional green for positive values
        }
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            'MainTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=15,
            textColor=self.brand_colors['primary'],
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            'SubTitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=8,
            textColor=self.brand_colors['text'],
            fontName='Helvetica-Bold',
            leading=16
        ))
        
        self.styles.add(ParagraphStyle(
            'LocationText',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            textColor=self.brand_colors['text'],
            fontName='Helvetica',
            leading=14
        ))
        
        self.styles.add(ParagraphStyle(
            'NormalText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=self.brand_colors['text'],
            leading=13
        ))
        
        self.styles.add(ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            spaceBefore=2,
            spaceAfter=2,
            textColor=self.brand_colors['text']
        ))

        self.styles.add(ParagraphStyle(
            'PlatformCell',
            parent=self.styles['TableCell'],
            leftIndent=20,
            fontSize=9,
            leading=11
        ))

        self.styles.add(ParagraphStyle(
            'PeriodText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=4,
            spaceAfter=12,
            textColor=self.brand_colors['text'],
            leading=13,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

    def format_currency(self, amount, include_space=True):
        """Format amount as currency with optional space after $"""
        if amount == 0:
            return "$ -"
        formatted = f"$ {abs(amount):,.2f}" if include_space else f"${abs(amount):,.2f}"
        return f"-{formatted}" if amount < 0 else formatted

    def wrap_text(self, text, style='TableCell'):
        """Wrap text in a Paragraph object for table cells"""
        return Paragraph(str(text), self.styles[style])

    def sanitize_filename(self, name):
        """Convert owner name to valid filename"""
        invalid_chars = '<>:"/\\|?*'
        filename = ''.join(c if c not in invalid_chars else '_' for c in name)
        filename = filename.strip().replace(' ', '_')
        return f"{filename}.pdf"

    def generate_pdfs_for_all_owners(self, data):
        """Generate PDFs for all bill owners in the data"""
        generated_files = []
        for owner_data in data['bill_owners']:
            filepath = self.generate_pdf_for_owner(owner_data)
            generated_files.append(filepath)
        return generated_files

    def generate_pdf_for_owner(self, owner_data):
        """Generate PDF for a single bill owner"""
        filename = self.sanitize_filename(owner_data['name'])
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(letter),
            rightMargin=42,
            leftMargin=42,
            topMargin=42,
            bottomMargin=42
        )

        story = []

        # Title and owner information
        story.append(Paragraph("Detailed Payout Summary", self.styles['MainTitle']))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(owner_data['name'], self.styles['SubTitle']))
        story.append(Spacer(1, 5))

        # Thank you message and period
        story.append(Paragraph(
            "Thank you for your business with The On Demand Company. "
            "Please find below your sales report for the period:",
            self.styles['NormalText']
        ))
        
        story.append(Paragraph(
            f"<b>{owner_data['period']}</b>",
            self.styles['PeriodText']
        ))
        
        # Payment Summary
        story.append(Paragraph("Payment Summary:", self.styles['SubTitle']))
        story.append(Spacer(1, 8))

        # Payment Summary Table
        payment_data = [
            ["Grand Total", self.format_currency(owner_data['financials']['total_payout'])],
            ["Ad Fees", self.format_currency(-owner_data['financials']['ad_fees'])],
            ["Aggregator Fee", self.format_currency(owner_data['financials']['aggregator_fee'])],
            ["Total Net Payout", self.format_currency(owner_data['financials']['final_net_payout'])]
        ]
        
        payment_table = self.create_payment_summary_table(payment_data)
        story.append(payment_table)
        story.append(Spacer(1, 20))

        # Create detailed breakdown for all restaurants
        header, detail_data = self.prepare_restaurant_breakdown(owner_data['restaurants'])
        detail_table = self.create_detail_table(header, detail_data)
        story.append(detail_table)

        doc.build(story)
        return filepath

    def create_payment_summary_table(self, payment_data):
        """Create a styled table for payment summary"""
        table = Table(payment_data, colWidths=[4*inch, 1.75*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), self.brand_colors['table_header']),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, self.brand_colors['primary']),
            ('BOX', (0, 0), (-1, -1), 1, self.brand_colors['primary']),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ]))
        return table

    def create_detail_table(self, header, data):
        """Create a styled table for detailed breakdown"""
        table = Table(
            header + data,
            colWidths=[2.3*inch, 1.1*inch, 0.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1*inch],
            repeatRows=1
        )
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.brand_colors['table_header']),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, self.brand_colors['primary']),
            ('BOX', (0, 0), (-1, -1), 1, self.brand_colors['primary']),
            ('BACKGROUND', (0, -1), (-1, -1), self.brand_colors['table_header']),
            *[('BACKGROUND', (0, i), (-1, i), self.brand_colors['accent'])
              for i in range(1, len(data), 2)]
        ]))
        return table

    def prepare_restaurant_breakdown(self, restaurants):
        """Prepare header and data for restaurant breakdown table"""
        header = [[
            self.wrap_text('<font color="white">Virtual Brand Name</font>'),
            self.wrap_text('<font color="white">Platform</font>'),
            self.wrap_text('<font color="white"># of Orders</font>'),
            self.wrap_text('<font color="white">Gross Pay</font>'),
            self.wrap_text('<font color="white">Taxes Transferred</font>'),
            self.wrap_text('<font color="white">Platform Taxes</font>'),
            self.wrap_text('<font color="white">Subtotal</font>'),
            self.wrap_text('<font color="white">Adjustments</font>'),
            self.wrap_text('<font color="white">Net Pay</font>')
        ]]

        table_data = []
        current_restaurant = None
        
        for restaurant in restaurants:
            restaurant_name = restaurant['name']
            has_platforms = False
            
            for platform in restaurant['platforms']:
                has_platforms = True
                row = [
                    self.wrap_text(restaurant_name if current_restaurant != restaurant_name else "", style='TableCell'),
                    self.wrap_text(platform['platform'], style='PlatformCell'),
                    platform['orders'] or '-',
                    self.format_currency(platform['gross_pay']),
                    self.format_currency(platform['taxes_transferred']),
                    self.format_currency(platform['taxes_platform']),
                    self.format_currency(platform['subtotal']),
                    self.format_currency(platform['error_charges']),
                    self.format_currency(platform['net_pay'])
                ]
                table_data.append(row)
                current_restaurant = restaurant_name

            if not has_platforms:
                row = [
                    self.wrap_text(restaurant_name),
                    '-', '-', '$ -', '$ -', '$ -', '$ -', '$ -', '$ -'
                ]
                table_data.append(row)

        # Add totals row
        totals = self.calculate_totals(restaurants)
        totals_row = [
            self.wrap_text('<font color="white"><b>Grand Total</b></font>'),
            '',
            str(totals['order_count']),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["gross_pay"])}</font>'),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["taxes_transferred"])}</font>'),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["taxes_platform"])}</font>'),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["subtotal"])}</font>'),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["error_charges"])}</font>'),
            self.wrap_text(f'<font color="white">{self.format_currency(totals["net_pay"])}</font>')
        ]
        table_data.append(totals_row)

        return header, table_data

    def calculate_totals(self, restaurants):
        """Calculate totals across all restaurants"""
        totals = {
            'order_count': 0,
            'gross_pay': 0,
            'taxes_transferred': 0,
            'taxes_platform': 0,
            'subtotal': 0,
            'error_charges': 0,
            'net_pay': 0
        }
        
        for restaurant in restaurants:
            for platform in restaurant['platforms']:
                totals['order_count'] += platform.get('orders', 0) or 0
                totals['gross_pay'] += platform.get('gross_pay', 0) or 0
                totals['taxes_transferred'] += platform.get('taxes_transferred', 0) or 0
                totals['taxes_platform'] += platform.get('taxes_platform', 0) or 0
                totals['subtotal'] += platform.get('subtotal', 0) or 0
                totals['error_charges'] += platform.get('error_charges', 0) or 0
                totals['net_pay'] += platform.get('net_pay', 0) or 0
        
        return totals