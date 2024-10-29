# invoice_processor.py
import pandas as pd
from datetime import datetime
from typing import Dict, List

class InvoiceProcessor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.clean_monetary_columns()

    def clean_column_names(self):
        """Clean whitespace from column names."""
        self.df.columns = self.df.columns.str.strip()

    def clean_currency(self, x) -> float:
        """Convert currency string to float."""
        if pd.isna(x):
            return 0.0
        if isinstance(x, str):
            return float(x.replace('$', '').replace(',', '') or 0)
        return float(x or 0)

    def clean_monetary_columns(self):
        """Clean all monetary columns in the dataframe."""
        monetary_columns = [
            'Additional Fees',
            'Sum of Total payout',
            'Final Net Payout with Agg Fee',
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
            'ad_fee'
        ]
        
        for column in monetary_columns:
            if column in self.df.columns:
                self.df[column] = self.df[column].apply(self.clean_currency)

    def process_invoices(self) -> Dict:
        """Process invoice data and return structured dictionary."""
        self.clean_column_names()
        
        # First level grouping by BillOwnerName and Order Week
        owner_groups = self.df.groupby(['BillOwnerName', 'Order Week'])
        
        # Create structure for all bill owners
        bill_owners = []
        
        for (owner, week), owner_data in owner_groups:
            # Calculate owner totals
            total_payout = owner_data['Sum of Total payout'].sum()
            final_net_payout = owner_data['Final Net Payout with Agg Fee'].sum()
            ad_fees = owner_data['ad_fee'].sum()
            aggregator_fee = owner_data['Additional Fees'].max()
            
            # Group by Restaurant and Platform for breakdown
            restaurant_breakdown = []
            for restaurant, rest_data in owner_data.groupby('Restaurant'):
                platform_data = []
                for platform, plat_data in rest_data.groupby('Platform_x'):
                    platform_info = {
                        'platform': platform,
                        'orders': int(plat_data['Sum of Order Count'].sum()),
                        'gross_pay': float(plat_data['Sum of Total payout'].sum()),
                        'taxes_transferred': float(plat_data['Sum of Passed on Tax'].sum()),
                        'taxes_platform': float(plat_data['Sum of Marketplace Facilitator Tax'].sum()),
                        'subtotal': float(plat_data['Sum of Sales (excl. tax)'].sum()),
                        'error_charges': 0.0,
                        'net_pay': float(plat_data['Final Net Payout with Agg Fee'].sum()),
                        'marketplace_fee': float(plat_data['Sum of Marketplace fee'].sum())
                    }
                    platform_data.append(platform_info)
                
                restaurant_info = {
                    'name': restaurant,
                    'platforms': platform_data
                }
                restaurant_breakdown.append(restaurant_info)

            # Create bill owner data structure
            owner_data = {
                'name': owner,
                'period': week,
                'restaurants': restaurant_breakdown,
                'financials': {
                    'total_payout': float(total_payout),
                    'final_net_payout': float(final_net_payout),
                    'ad_fees': 0,
                    'aggregator_fee': float(aggregator_fee)
                }
            }
            bill_owners.append(owner_data)
        
        return {'bill_owners': bill_owners}