import pandas as pd
from utils.sheets_helper import GoogleSheetsHelper
from utils.invoice_processor import InvoiceProcessor
from utils.pdf_generator import PDFInvoiceGenerator
import os
import shutil
import logging

def fetch_data():
    """Fetch data from source (e.g., CSV, Google Sheets, etc.)"""
    try:
        print("Fetching data from Google Sheets...")
        # Replace this with your actual data source
        df = pd.read_csv('your_data.csv')  # or your actual data source
        print(f"Columns in the sheet: {df.columns.tolist()}")
        print(f"Total rows: {len(df)}")
        return df
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        raise

def generate_invoices():
    SPREADSHEET_ID = '1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE'
    RANGE_NAME = 'store_id_level_matched!A:Z'
    OUTPUT_DIR = 'generated_invoices'
    
    try:
        # Clean up old invoices
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)
        
        # Fetch data
        print("Fetching data from Google Sheets...")
        sheets_helper = GoogleSheetsHelper()
        df = sheets_helper.get_sheet_data(SPREADSHEET_ID, RANGE_NAME)
        
        # Process invoices
        print("Processing invoice data...")
        processor = InvoiceProcessor(df)
        invoice_data = processor.process_invoices()
        
        # Generate PDFs
        print("\nGenerating PDF invoices...")
        pdf_generator = PDFInvoiceGenerator(output_dir=OUTPUT_DIR)
        
        # Generate PDFs for all owners
        generated_files = pdf_generator.generate_pdfs_for_all_owners(invoice_data)
        
        # Print summary with progress
        total_owners = len(invoice_data['bill_owners'])
        print(f"\nGenerating PDFs for {total_owners} bill owners:")
        
        # Print detailed summary
        print(f"\nGenerated {len(generated_files)} PDF invoices:")
        print("-" * 60)
        print(f"{'Bill Owner':<30} {'Period':<15} {'Amount':>15}")
        print("-" * 60)
        
        for owner in invoice_data['bill_owners']:
            print(f"{owner['name'][:30]:<30} {owner['period']:<15} ${owner['financials']['final_net_payout']:>14,.2f}")
        
        print("-" * 60)
        print(f"\nPDF invoices have been generated in: {OUTPUT_DIR}/")
        
        return generated_files
        
    except Exception as e:
        print(f"Error generating invoices: {str(e)}")
        raise

if __name__ == "__main__":
    generated_files = generate_invoices()