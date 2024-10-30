# invoice_processor.py
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging

class ValidationError:
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[any] = None):
        self.message = message
        self.field = field
        self.value = value

class InvoiceProcessor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.errors = []
        self.warnings = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='invoice_processing.log'
        )
        
        # Required columns for validation
        self.required_columns = {
            'BillOwnerName': str,
            'Order Week': str,
            'Restaurant': str,
            'Platform_x': str,
            'Sum of Order Count': float,
            'Sum of Total payout': float,
            'Final Net Payout with Agg Fee': float,
            'Sum of Sales (excl. tax)': float,
            'Sum of Passed on Tax': float,
            'Sum of Marketplace Facilitator Tax': float,
            'Additional Fees': float,
            'ad_fee': float
        }
        
        # Valid platforms
        self.valid_platforms = {'Grubhub', 'DoorDash', 'UberEats'}
        
        # Clean monetary columns
        self.clean_monetary_columns()

    def validate_data(self) -> bool:
        """Validate the dataframe before processing"""
        self.errors = []
        self.warnings = []
        
        # Check required columns
        missing_columns = [col for col in self.required_columns if col not in self.df.columns]
        if missing_columns:
            self.errors.append(ValidationError(
                f"Missing required columns: {', '.join(missing_columns)}",
                "columns"
            ))
            return False

        # Validate data types and values
        self._validate_data_types()
        self._validate_values()

        if self.errors:
            self.logger.error(f"Validation failed with {len(self.errors)} errors")
            self._print_validation_report()
            return False

        if self.warnings:
            self.logger.warning(f"Validation passed with {len(self.warnings)} warnings")
            self._print_validation_report()

        return True

    def _validate_data_types(self):
        """Validate data types for all columns"""
        for col, expected_type in self.required_columns.items():
            non_null_values = self.df[col].dropna()
            if not all(isinstance(x, expected_type) or isinstance(float(x), expected_type) 
                      for x in non_null_values):
                self.errors.append(ValidationError(
                    f"Column {col} contains invalid data types",
                    col
                ))

    def _validate_values(self):
        """Validate specific value constraints"""
        # Check for negative orders
        negative_orders = self.df[self.df['Sum of Order Count'] < 0]
        if not negative_orders.empty:
            self.errors.append(ValidationError(
                "Negative order counts found",
                "Sum of Order Count",
                negative_orders.index.tolist()
            ))

        # Validate platforms
        invalid_platforms = self.df[~self.df['Platform_x'].isin(self.valid_platforms)]
        if not invalid_platforms.empty:
            self.warnings.append(ValidationError(
                f"Invalid platform names found: {invalid_platforms['Platform_x'].unique().tolist()}",
                "Platform_x"
            ))

        # Check for suspicious amounts (e.g., very large payouts)
        suspicious_payouts = self.df[self.df['Sum of Total payout'] > 10000]
        if not suspicious_payouts.empty:
            self.warnings.append(ValidationError(
                "Unusually large payout amounts found",
                "Sum of Total payout",
                suspicious_payouts['Sum of Total payout'].tolist()
            ))

    def _validate_totals(self):
        """Validate that totals add up correctly"""
        for owner in self.df['BillOwnerName'].unique():
            owner_data = self.df[self.df['BillOwnerName'] == owner]
            
            # Check if total payout matches calculations
            total_payout = owner_data['Sum of Total payout'].sum()
            net_payout = owner_data['Final Net Payout with Agg Fee'].sum()
            
            if not abs(total_payout - net_payout) <= 0.01:  # Allow small float differences
                self.warnings.append(ValidationError(
                    f"Total payout mismatch for {owner}",
                    "payout_validation",
                    {"total": total_payout, "net": net_payout}
                ))

    def _print_validation_report(self):
        """Print a formatted validation report"""
        if self.errors:
            print("\n🚨 Validation Errors:")
            for error in self.errors:
                print(f"- {error.message}")
                if error.field:
                    print(f"  Field: {error.field}")
                if error.value:
                    print(f"  Value: {error.value}")

        if self.warnings:
            print("\n⚠️ Validation Warnings:")
            for warning in self.warnings:
                print(f"- {warning.message}")
                if warning.field:
                    print(f"  Field: {warning.field}")
                if warning.value:
                    print(f"  Value: {warning.value}")

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
        # Validate data before processing
        if not self.validate_data():
            raise ValueError("Data validation failed. Check the validation report for details.")

        self.logger.info("Starting invoice processing")
        self.clean_column_names()
        
        try:
            # First level grouping by BillOwnerName and Order Week
            owner_groups = self.df.groupby(['BillOwnerName', 'Order Week'])
            
            # Create structure for all bill owners
            bill_owners = []
            
            for (owner, week), owner_data in owner_groups:
                try:
                    # Calculate owner totals
                    total_payout = owner_data['Sum of Total payout'].sum()
                    final_net_payout = owner_data['Final Net Payout with Agg Fee'].sum()
                    ad_fees = owner_data['ad_fee'].sum()
                    aggregator_fee = owner_data['Additional Fees'].max()
                    
                    # Group by Restaurant and Platform for breakdown
                    restaurant_breakdown = self._process_restaurant_breakdown(owner_data)

                    # Create bill owner data structure
                    owner_info = {
                        'name': owner,
                        'period': week,
                        'restaurants': restaurant_breakdown,
                        'financials': {
                            'total_payout': float(total_payout),
                            'final_net_payout': float(final_net_payout),
                            'ad_fees': float(ad_fees),
                            'aggregator_fee': float(aggregator_fee)
                        }
                    }
                    bill_owners.append(owner_info)
                    self.logger.info(f"Processed data for owner: {owner}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing owner {owner}: {str(e)}")
                    raise
            
            self.logger.info(f"Successfully processed {len(bill_owners)} bill owners")
            return {'bill_owners': bill_owners}
            
        except Exception as e:
            self.logger.error(f"Error in invoice processing: {str(e)}")
            raise

    def _process_restaurant_breakdown(self, owner_data: pd.DataFrame) -> List[Dict]:
        """Process restaurant breakdown with validation"""
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
            
        return restaurant_breakdown