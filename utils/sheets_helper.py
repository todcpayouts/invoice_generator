# utils/sheets_helper.py
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

class GoogleSheetsHelper:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        service_account_file = os.path.join(current_dir, 'service-account.json')
        
        self.credentials = service_account.Credentials.from_service_account_file(
            service_account_file, 
            scopes=self.SCOPES
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)
    
    def get_sheet_data(self, spreadsheet_id: str, range_name: str) -> pd.DataFrame:
        """Fetches data from Google Sheets and returns as a pandas DataFrame with proper data types"""
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                raise ValueError('No data found in the specified range.')
            
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # Convert numeric columns to float
            numeric_columns = [
                'Sum of Total payout',
                'Sum of Order Count',
                'Sum of Sales (excl. tax)',
                'Sum of Passed on Tax',
                'Sum of Marketplace Facilitator Tax',
                'Sum of Marketplace fee',
                'Sum of Promotions on items',
                'Refund',
                'delivery fee',
                'Other 3P fee',
                'adjustment',
                'store_payment',
                'tips',
                'ad_fee',
                'Final Net Payout with Agg Fee'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    # Remove any currency symbols and commas
                    df[col] = df[col].replace(r'[$,]', '', regex=True)
                    # Convert to float, replacing empty strings with 0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            print(f"\nColumns in the sheet: {list(df.columns)}")
            print(f"Total rows: {len(df)}")
            
            return df
            
        except Exception as e:
            print(f"Error reading sheet: {str(e)}")
            raise