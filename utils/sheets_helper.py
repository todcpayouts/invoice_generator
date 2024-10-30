import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
import logging

class GoogleSheetsHelper:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
    
    def _get_credentials(self):
        """Get credentials from either file or environment variable"""
        try:
            # First try to get from environment (Cloud Run)
            creds_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_env:
                try:
                    # Try to parse as JSON (for Cloud Run secrets)
                    creds_dict = json.loads(creds_env)
                    return service_account.Credentials.from_service_account_info(
                        creds_dict, 
                        scopes=self.SCOPES
                    )
                except json.JSONDecodeError:
                    # If not JSON, treat as file path
                    if os.path.exists(creds_env):
                        return service_account.Credentials.from_service_account_file(
                            creds_env, 
                            scopes=self.SCOPES
                        )
            
            # Try local development path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths = [
                os.path.join(current_dir, 'service-account.json'),
                '/app/service-account.json',
                'service-account.json'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    logging.info(f"Using credentials from: {path}")
                    return service_account.Credentials.from_service_account_file(
                        path, 
                        scopes=self.SCOPES
                    )
            
            raise FileNotFoundError("No valid credentials found")
            
        except Exception as e:
            logging.error(f"Error loading credentials: {str(e)}")
            raise Exception(f"Failed to load credentials: {str(e)}")
    
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
            
            headers = values[0]
            data = values[1:]
            
            # Add warning if column count mismatch
            if data and len(data[0]) != len(headers):
                logging.warning(f"Column mismatch detected! Headers: {len(headers)}, Data columns: {len(data[0])}. "
                            f"Please check your spreadsheet for extra or missing columns.")
    
            df = pd.DataFrame(data, columns=headers)
            
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
            
            logging.info(f"Successfully loaded sheet data: {len(df)} rows")
            logging.debug(f"Columns in the sheet: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logging.error(f"Error reading sheet: {str(e)}")
            raise