from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Dict, List, Optional
from pydantic import Field

class Settings(BaseSettings):
    # Google Sheets
    SPREADSHEET_ID: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8080)
    
    # Optional Security
    API_KEY: Optional[str] = Field(default=None)
    ALLOWED_ORIGINS: List[str] = Field(default=["*"])
    
    # PDF Generation
    PDF_OUTPUT_DIR: str = Field(default="generated_invoices")
    
    # Sheet Configurations
    SHEET_DEFAULTS: Dict = Field(default={
        "INVOICE_SHEET_ID": "1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE",
        "MASTER_SHEET_ID": "1mVPlZe7kAVl1RclfDuuiIRbSThpggBUxhp9HKvVYeeE",
        "INVOICE_RANGE": "store_id_level_matched!A:Z",
        "MASTER_RANGE": "PD Store Level!A:K",
        "MAX_PDFS": -1
    })
    
    CUSTOMER_CONFIGS: Dict = Field(default={
        "customer1": {
            "INVOICE_SHEET_ID": "customer1_sheet_id",
            "INVOICE_RANGE": "customer1_range!A:Z",
        },
        "customer2": {
            "MASTER_SHEET_ID": "customer2_master_id",
            "MASTER_RANGE": "customer2_range!A:K",
        }
    })

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='allow'
    )

    def get_customer_config(self, customer_id: Optional[str]) -> Dict:
        """Get configuration for a specific customer or default"""
        if customer_id and customer_id in self.CUSTOMER_CONFIGS:
            return {**self.SHEET_DEFAULTS, **self.CUSTOMER_CONFIGS[customer_id]}
        return self.SHEET_DEFAULTS

@lru_cache()
def get_settings() -> Settings:
    return Settings()