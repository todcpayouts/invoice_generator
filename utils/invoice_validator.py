from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
import pandas as pd
import logging

@dataclass
class ValidationError:
    error_type: str
    message: str
    row_index: int = None
    field: str = None
    value: Any = None
    severity: str = 'error'

class InvoiceValidator:
    def __init__(self, config: dict = None):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.passed_tests: List[str] = []
        self.logger = logging.getLogger(__name__)
        
        # Define default configuration
        self.config = {
            'required_columns': {
                'BillOwnerName': str,
                'Platform_x': str,
                'Order Week': str,
                'Sum of Order Count': (int, float),
                'Sum of Total payout': float,
                'Sum of Sales (excl. tax)': float,
                'Sum of Passed on Tax': float,
                'Sum of Marketplace Facilitator Tax': float,
                'Additional Fees': float,
                'Final Net Payout with Agg Fee': float
            },
            'valid_platforms': {'Grubhub', 'DoorDash', 'UberEats'},
            'suspicious_payout_threshold': 1000000,
            'negative_order_count_threshold': 0,
            'maximum_payout_percentage': 1.1  # 10% variance allowed
        }
        
        # Update configuration with user-provided values
        if config:
            self.config.update(config)

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, List[ValidationError]]:
        """Main validation method for the entire dataframe"""
        self.errors = []
        self.warnings = []
        self.passed_tests = []
        
        # Check for required columns
        missing_columns = self._check_missing_columns(df)
        if missing_columns:
            self.errors.append(ValidationError(
                error_type="missing_columns",
                message=f"Missing required columns: {', '.join(missing_columns)}",
                severity='error'
            ))
            return False, self.warnings
        else:
            self.passed_tests.append("Required columns check")

        # Validate each row
        for index, row in df.iterrows():
            self._validate_row(row, index)
            
        # Validate totals across the dataframe
        self._validate_totals(df)
        
        self._log_passed_tests()
        
        return len(self.errors) == 0, self.warnings

    def _check_missing_columns(self, df: pd.DataFrame) -> List[str]:
        """Check for any missing required columns"""
        return [col for col in self.config['required_columns'] if col not in df.columns]

    def _validate_row(self, row: pd.Series, index: int):
        """Validate a single row of data"""
        # Validate BillOwnerName
        if pd.isna(row['BillOwnerName']) or str(row['BillOwnerName']).strip() == '':
            self.errors.append(ValidationError(
                error_type="invalid_owner",
                message="BillOwnerName cannot be empty",
                row_index=index,
                field='BillOwnerName',
                severity='error'
            ))
        else:
            self.passed_tests.append(f"BillOwnerName validation for row {index + 1}")

        # Validate Platform
        if row['Platform_x'] not in self.config['valid_platforms']:
            self.warnings.append(ValidationError(
                error_type="invalid_platform",
                message=f"Invalid platform: {row['Platform_x']}. Must be one of {self.config['valid_platforms']}",
                row_index=index,
                field='Platform_x',
                value=row['Platform_x'],
                severity='warning'
            ))
        else:
            self.passed_tests.append(f"Platform validation for row {index + 1}")

        # Validate numeric fields
        self._validate_numeric_fields(row, index)

    def _validate_numeric_fields(self, row: pd.Series, index: int):
        """Validate all numeric fields in a row"""
        numeric_fields = [field for field in self.config['required_columns'] if self.config['required_columns'][field] in (int, float)]

        for field in numeric_fields:
            value = row[field]
            
            # Check for null values
            if pd.isna(value):
                self.errors.append(ValidationError(
                    error_type="null_value",
                    message=f"{field} cannot be null",
                    row_index=index,
                    field=field,
                    severity='error'
                ))
            else:
                self.passed_tests.append(f"{field} validation for row {index + 1}")
                
            try:
                value = float(value)
                
                # Order count should be positive
                if field == 'Sum of Order Count' and value < self.config['negative_order_count_threshold']:
                    self.errors.append(ValidationError(
                        error_type="negative_orders",
                        message="Order count cannot be negative",
                        row_index=index,
                        field=field,
                        value=value,
                        severity='error'
                    ))
                else:
                    self.passed_tests.append(f"{field} (positive) validation for row {index + 1}")

                # Check for unreasonable values
                if field == 'Sum of Total payout' and abs(value) > self.config['suspicious_payout_threshold']:
                    self.warnings.append(ValidationError(
                        error_type="suspicious_amount",
                        message=f"Suspicious payout amount: ${value:,.2f}",
                        row_index=index,
                        field=field,
                        value=value,
                        severity='warning'
                    ))
                else:
                    self.passed_tests.append(f"{field} (amount) validation for row {index + 1}")

            except (ValueError, TypeError):
                if field != 'Order Week':
                    self.errors.append(ValidationError(
                        error_type="invalid_number",
                        message=f"Invalid numeric value in {field}",
                        row_index=index,
                        field=field,
                        value=value,
                        severity='error'
                    ))
                else:
                    self.passed_tests.append(f"{field} validation for row {index + 1}")

    def _validate_totals(self, df: pd.DataFrame):
        """Validate that totals add up correctly"""
        for owner in df['BillOwnerName'].unique():
            owner_data = df[df['BillOwnerName'] == owner]
            
            # Calculate totals
            total_payout = owner_data['Sum of Total payout'].sum()
            final_net_payout = owner_data['Final Net Payout with Agg Fee'].sum()
            
            # Validate the difference between total payout and final net payout
            if not abs(total_payout - final_net_payout) <= total_payout * self.config['maximum_payout_percentage']:
                self.warnings.append(ValidationError(
                    error_type="total_mismatch",
                    message=(f"Total payout (${total_payout:,.2f}) does not match "
                             f"final net payout (${final_net_payout:,.2f}) for {owner}"),
                    field='total_validation',
                    value={'owner': owner, 'difference': total_payout - final_net_payout},
                    severity='warning'
                ))
            else:
                self.passed_tests.append(f"Total payout validation for {owner}")

    def _log_passed_tests(self):
        """Log the successful validation tests"""
        if self.passed_tests:
            self.logger.info("The following validation tests passed:")
            for test in self.passed_tests:
                self.logger.info(f"- {test}")

    def get_error_summary(self) -> Dict:
        """Generate a summary of validation errors and warnings"""
        summary = {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'error_types': {},
            'warning_types': {},
            'error_details': [],
            'warning_details': []
        }

        for error in self.errors:
            # Count error types
            if error.error_type not in summary['error_types']:
                summary['error_types'][error.error_type] = 0
            summary['error_types'][error.error_type] += 1

            # Add detailed error info
            detail = {
                'type': error.error_type,
                'message': error.message,
                'severity': error.severity
            }
            if error.row_index is not None:
                detail['row'] = error.row_index
            if error.field is not None:
                detail['field'] = error.field
            if error.value is not None:
                detail['value'] = error.value

            summary['error_details'].append(detail)

        for warning in self.warnings:
            # Count warning types
            if warning.error_type not in summary['warning_types']:
                summary['warning_types'][warning.error_type] = 0
            summary['warning_types'][warning.error_type] += 1

            # Add detailed warning info
            detail = {
                'type': warning.error_type,
                'message': warning.message,
                'severity': warning.severity
            }
            if warning.row_index is not None:
                detail['row'] = warning.row_index
            if warning.field is not None:
                detail['field'] = warning.field
            if warning.value is not None:
                detail['value'] = warning.value

            summary['warning_details'].append(detail)

        return summary

    def print_error_report(self):
        """Print a formatted error and warning report"""
        if not self.errors and not self.warnings:
            print("✅ No validation errors or warnings found")
            return

        if self.errors:
            print("\n🚨 Validation Errors Found:")
            print("=" * 50)

            for error in self.errors:
                print(f"\nError Type: {error.error_type}")
                print(f"Message: {error.message}")
                print(f"Severity: {error.severity}")
                if error.row_index is not None:
                    print(f"Row: {error.row_index + 1}")  # +1 for human-readable row numbers
                if error.field is not None:
                    print(f"Field: {error.field}")
                if error.value is not None:
                    print(f"Value: {error.value}")
                print("-" * 30)

        if self.warnings:
            print("\n⚠️ Validation Warnings Found:")
            print("=" * 50)

            for warning in self.warnings:
                print(f"\nWarning Type: {warning.error_type}")
                print(f"Message: {warning.message}")
                print(f"Severity: {warning.severity}")
                if warning.row_index is not None:
                    print(f"Row: {warning.row_index + 1}")  # +1 for human-readable row numbers
                if warning.field is not None:
                    print(f"Field: {warning.field}")
                if warning.value is not None:
                    print(f"Value: {warning.value}")
                print("-" * 30)