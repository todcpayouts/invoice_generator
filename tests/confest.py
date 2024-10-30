import os
import sys
import pytest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture
def sheets_helper():
    """Fixture to provide GoogleSheetsHelper instance"""
    from utils.sheets_helper import GoogleSheetsHelper
    return GoogleSheetsHelper()

@pytest.fixture
def test_data():
    """Fixture to provide test data"""
    return {
        "spreadsheet_id": "1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE",
        "range_name": "store_id_level_matched!A:Z",
        "max_pdfs": 2
    }