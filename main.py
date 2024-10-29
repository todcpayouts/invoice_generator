import pandas as pd
from utils.sheets_helper import GoogleSheetsHelper
from utils.invoice_processor import InvoiceProcessor
from utils.invoice_processor import InvoiceProcessor
from utils.pdf_generator import ModernPDFGenerator
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
        
        pdf_generator = ModernPDFGenerator(output_dir='generated_invoices')
        
        generated_files = []
        for owner_data in invoice_data['bill_owners']:
            try:
                filepath = pdf_generator.generate_pdf(owner_data)
                generated_files.append(filepath)
            except Exception as e:
                print(f"Error generating PDF for {owner_data['name']}: {str(e)}")
                continue
        
        return generated_files
        
    except Exception as e:
        print(f"Error generating invoices: {str(e)}")
        raise

if __name__ == "__main__":
    generated_files = generate_invoices()