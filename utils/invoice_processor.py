# invoice_processor.py
import pandas as pd
from datetime import datetime
from typing import Dict, List

class InvoiceProcessor:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def clean_column_names(self):
        self.df.columns = self.df.columns.str.strip()

    def process_invoices(self) -> Dict:
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
                    'ad_fees': float(ad_fees),
                    'aggregator_fee': 0.0
                }
            }
            bill_owners.append(owner_data)
        
        return {'bill_owners': bill_owners}