# utils/store_validator.py

from dataclasses import dataclass
from typing import List, Dict, Tuple, Set
import pandas as pd
from datetime import datetime
from rapidfuzz import fuzz
import logging
from utils.sheets_helper import GoogleSheetsHelper

@dataclass
class ValidationResult:
    validation_id: str
    matched_stores: List[str]
    missing_in_master: List[str]
    missing_in_invoice: List[str]
    potential_matches: List[Tuple[str, str]]
    summary: Dict
    timestamp: str

class StoreValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sheets_helper = GoogleSheetsHelper()

    def validate_from_sheets(self,
                           invoice_sheet_id: str,
                           invoice_range: str,
                           master_sheet_id: str,
                           master_range: str) -> ValidationResult:
        """
        Validate stores by comparing two Google Sheets
        """
        try:
            # Fetch data from both sheets
            invoice_df = self.sheets_helper.get_sheet_data(invoice_sheet_id, invoice_range)
            master_df = self.sheets_helper.get_sheet_data(master_sheet_id, master_range)
            
            # Perform comparison
            result = self.compare_stores(invoice_df, master_df)
            
            # Generate validation ID
            result.validation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            raise

    def compare_stores(self,
                      invoice_df: pd.DataFrame,
                      master_df: pd.DataFrame,
                      fuzzy_threshold: float = 0.85) -> ValidationResult:
        """
        Compare stores between invoice and master data
        """
        # Clean and standardize restaurant names
        invoice_stores = self._clean_names(invoice_df['Restaurant'])
        master_stores = self._clean_names(master_df['RestaurantName'])
        
        # Find exact matches
        matched = set(invoice_stores) & set(master_stores)
        missing_in_master = set(invoice_stores) - set(master_stores)
        missing_in_invoice = set(master_stores) - set(invoice_stores)
        
        # Find potential matches using fuzzy matching
        potential_matches = self._find_potential_matches(
            missing_in_master,
            missing_in_invoice,
            fuzzy_threshold
        )
        
        # Create summary
        summary = {
            'matched_count': len(matched),
            'missing_in_master_count': len(missing_in_master),
            'missing_in_invoice_count': len(missing_in_invoice),
            'potential_matches_count': len(potential_matches),
            'total_invoice_stores': len(invoice_stores),
            'total_master_stores': len(master_stores),
            'match_percentage': round(len(matched) / len(invoice_stores) * 100, 2)
        }
        
        return ValidationResult(
            validation_id="",  # Set when validating from sheets
            matched_stores=list(matched),
            missing_in_master=list(missing_in_master),
            missing_in_invoice=list(missing_in_invoice),
            potential_matches=potential_matches,
            summary=summary,
            timestamp=datetime.now().isoformat()
        )

    def _clean_names(self, names: pd.Series) -> Set[str]:
        """Clean and standardize restaurant names"""
        return set(names.str.lower()
                       .str.replace(r'[^\w\s]', '', regex=True)
                       .str.strip())

    def _find_potential_matches(self,
                              set1: Set[str],
                              set2: Set[str],
                              threshold: float) -> List[Tuple[str, str]]:
        """Find potential matches using fuzzy string matching"""
        potential_matches = []
        
        for name1 in set1:
            for name2 in set2:
                ratio = fuzz.ratio(name1, name2) / 100
                if ratio >= threshold:
                    potential_matches.append((name1, name2))
                    
        return potential_matches

    def generate_report(self, result: ValidationResult) -> Dict:
        """Generate a detailed validation report"""
        report = {
            'validation_id': result.validation_id,
            'timestamp': result.timestamp,
            'summary': result.summary,
            'details': {
                'matched_stores': result.matched_stores,
                'missing_in_master': result.missing_in_master,
                'missing_in_invoice': result.missing_in_invoice,
                'potential_matches': result.potential_matches
            },
            'recommendations': []
        }
        
        # Add recommendations based on results
        if result.missing_in_master:
            report['recommendations'].append(
                f"Add {len(result.missing_in_master)} missing stores to master data"
            )
        
        if result.potential_matches:
            report['recommendations'].append(
                f"Review {len(result.potential_matches)} potential matches for similar names"
            )
            
        return report