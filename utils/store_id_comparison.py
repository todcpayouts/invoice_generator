from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
import pandas as pd
from datetime import datetime
from .sheets_helper import GoogleSheetsHelper
import logging

@dataclass
class StoreIDComparisonResult:
    missing_store_ids: List[Dict[str, str]]
    comparison_summary: Dict[str, Any]
    validation_issues: Dict[str, List] = None
    validation_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")

class StoreIDComparison:
    def __init__(self):
        self.sheets_helper = GoogleSheetsHelper()

    def analyze_deposit_match_status(self, 
        invoice_sheet_id: str = "1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE",
        master_sheet_id: str = "1mVPlZe7kAVl1RclfDuuiIRbSThpggBUxhp9HKvVYeeE",
        invoice_range: str = "store_id_level_all!A:Z",
        master_range: str = "PD Store Level!A:K"
    ) -> Dict[str, Any]:
        """
        Analyzes store IDs based on their Deposit_ID_Match_Status against master sheet.
        Returns analysis of matched/unmatched stores and their presence in master sheet.
        """
        try:
            # Get data from sheets
            invoice_data = self.sheets_helper.get_sheet_data(invoice_sheet_id, invoice_range)
            master_data = self.sheets_helper.get_sheet_data(master_sheet_id, master_range)
            
            # Initialize validation issues tracking
            validation_issues = {
                'missing_store_ids': [],
                'not_in_master': [],
                'platform_distribution': {},
                'deposit_status_issues': []
            }

            # Analyze Deposit_ID_Match_Status values
            print("\n=== Deposit ID Match Status Distribution ===\n")
            unique_statuses = invoice_data['Deposit_ID_Match_Status'].unique()
            status_counts = {}
            for status in unique_statuses:
                count = len(invoice_data[invoice_data['Deposit_ID_Match_Status'] == status])
                status_counts[status] = int(count)  # Convert numpy.int64 to int
                print(f"Status: '{status}' - Count: {count}")
            print("-" * 80)
            
            # Filter for matched and unmatched stores
            matched_stores = invoice_data[
                (invoice_data['Deposit_ID_Match_Status'] == 'Matched') |
                (invoice_data['Deposit_ID_Match_Status'] == 'True')
            ]
            
            unmatched_stores = invoice_data[
                ~((invoice_data['Deposit_ID_Match_Status'] == 'Matched') |
                  (invoice_data['Deposit_ID_Match_Status'] == 'True'))
            ]
            
            # Calculate counts
            total_stores = len(invoice_data)
            matched_count = len(matched_stores)
            unmatched_count = len(unmatched_stores)
            false_count = len(invoice_data[invoice_data['Deposit_ID_Match_Status'] == 'False'])
            
            print(f"\nTotal stores in invoice data: {total_stores}")
            print(f"Total matched stores: {matched_count}")
            
            print("\n=== VALIDATION REPORT ===")
            print("\nStores marked as matched but requiring verification:")
            print("-" * 80)
            
            stores_requiring_verification = []
            
            for _, store in matched_stores.iterrows():
                store_id = store.get('Store ID', 'N/A')
                name = store.get('Restaurant', 'Unknown')
                platform = store.get('Platform', 'Unknown')
                deposit_status = store.get('Deposit_ID_Match_Status', 'Unknown')
                bill_owner = store.get('BillOwnerName', 'Unknown')
                
                # Track platform distribution
                validation_issues['platform_distribution'][platform] = \
                    validation_issues['platform_distribution'].get(platform, 0) + 1

                # Validate store ID
                if pd.isna(store_id) or store_id == 'N/A':
                    issue_data = {
                        'store_id': str(store_id),
                        'name': str(name),
                        'platform': str(platform),
                        'deposit_status': str(deposit_status),
                        'bill_owner': str(bill_owner),
                        'issue': 'Missing Store ID'
                    }
                    validation_issues['missing_store_ids'].append(issue_data)
                    stores_requiring_verification.append(issue_data)
                    print(f"""
    🚨 CRITICAL: Missing Store ID
    Store Name: {name}
    Platform: {platform}
    Bill Owner: {bill_owner}
    Action Required: Obtain valid store ID
    ---""")

                # Check master sheet presence
                if store_id not in master_data['Store ID'].values:
                    issue_data = {
                        'store_id': str(store_id),
                        'name': str(name),
                        'platform': str(platform),
                        'deposit_status': str(deposit_status),
                        'bill_owner': str(bill_owner),
                        'issue': 'Not in Master Sheet'
                    }
                    validation_issues['not_in_master'].append(issue_data)
                    stores_requiring_verification.append(issue_data)
                    print(f"""
    ⚠️ WARNING: Store Not in Master Sheet
    Store Name: {name}
    Store ID: {store_id}
    Platform: {platform}
    Bill Owner: {bill_owner}
    Action Required: Verify and add to master sheet
    ---""")

            print("\n=== Platform Distribution of Issues ===")
            for platform, count in validation_issues['platform_distribution'].items():
                print(f"    {platform}: {count} stores")

            # Prepare final result with all native Python types
            result = {
                'status_counts': {
                    str(status): int(count) 
                    for status, count in status_counts.items()
                },
                'matched_count': int(matched_count),
                'unmatched_count': int(unmatched_count),
                'false_count': int(false_count),
                'total_stores': int(total_stores),
                'total_matched': int(matched_count),
                'platform_distribution': {
                    str(platform): int(count) 
                    for platform, count in validation_issues['platform_distribution'].items()
                },
                'stores_requiring_verification': stores_requiring_verification,
                'validation_issues': {
                    'missing_store_ids': validation_issues['missing_store_ids'],
                    'not_in_master': validation_issues['not_in_master'],
                    'platform_distribution': {
                        str(platform): int(count)
                        for platform, count in validation_issues['platform_distribution'].items()
                    }
                }
            }
            
            return result
                
        except Exception as e:
            logging.error(f"Error in analyze_deposit_match_status: {str(e)}")
            raise

    def compare_store_ids(
        self,
        invoice_sheet_id: str,
        master_sheet_id: str,
        invoice_range: str = "store_id_level_matched!A:Z",
        master_range: str = "PD Store Level!A:K"
    ) -> StoreIDComparisonResult:
        """
        Compares store IDs between invoice and master sheets.
        Returns detailed analysis of missing stores and comparison summary.
        """
        try:
            # Get data from both sheets
            invoice_df = self.sheets_helper.get_sheet_data(invoice_sheet_id, invoice_range)
            master_df = self.sheets_helper.get_sheet_data(master_sheet_id, master_range)
            
            # Clean and convert Store IDs to strings
            invoice_df['Store ID'] = invoice_df['Store ID'].astype(str)
            master_df['Store ID'] = master_df['Store ID'].astype(str)
            
            # Get sets of Store IDs
            invoice_store_ids = set(invoice_df['Store ID'])
            master_store_ids = set(master_df['Store ID'])
            
            # Find missing Store IDs
            missing_ids = invoice_store_ids - master_store_ids
            
            # Create detailed missing stores list with enhanced metadata
            missing_stores = []
            for store_id in missing_ids:
                store_data = invoice_df[invoice_df['Store ID'] == store_id].iloc[0]
                missing_stores.append({
                    'store_id': str(store_id),
                    'restaurant_name': str(store_data['Restaurant']),
                    'platform': str(store_data['Platform_x']),
                    'bill_owner': str(store_data['BillOwnerName']),
                    'deposit_status': str(store_data.get('Deposit_ID_Match_Status', 'Unknown'))
                })
            
            # Enhanced summary with validation issues
            summary = {
                'total_invoice_stores': int(len(invoice_store_ids)),
                'total_master_stores': int(len(master_store_ids)),
                'missing_store_count': int(len(missing_stores)),
                'platforms': [str(p) for p in invoice_df['Platform_x'].unique().tolist()],
                'validation_timestamp': datetime.now().isoformat()
            }
            
            return StoreIDComparisonResult(
                missing_store_ids=missing_stores,
                comparison_summary=summary,
                validation_issues={'store_validation': missing_stores}
            )

        except Exception as e:
            logging.error(f"Error in store ID comparison: {str(e)}")
            raise