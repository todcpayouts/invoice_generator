from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from datetime import datetime
import logging
import os
import numpy as np
import shutil
from pathlib import Path
import zipfile
from io import BytesIO
from fastapi.staticfiles import StaticFiles
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json  # Add this import


# At the top of the file, add this logging configuration
import logging
import sys
from datetime import datetime

from utils.store_validator import StoreValidator
from utils.sheets_helper import GoogleSheetsHelper
from utils.invoice_processor import InvoiceProcessor
from utils.pdf_generator import ModernPDFGenerator
from utils.invoice_validator import InvoiceValidator
from utils.store_id_comparison import StoreIDComparison
from utils.config import get_settings

# Get settings
settings = get_settings()
pdf_generation_status = {}


# Configure logging with JSON format
class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module
        }
        if hasattr(record, 'props'):
            log_record.update(record.props)
        return str(log_record)

# Initialize FastAPI app

def setup_logger():
    logger = logging.getLogger("invoice_generator")
    logger.setLevel(logging.DEBUG)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)

    # File Handler
    log_file = f"logs/invoice_generator_{datetime.now().strftime('%Y%m%d')}.log"
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

app = FastAPI(
    title="TODC Invoice Generator",
    description="Generate and download invoices from Google Sheets data",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error handler caught: {str(exc)}", 
                extra={"path": request.url.path})
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if app.debug else "An unexpected error occurred"
        }
    )

# Configure storage
BASE_DIR = Path(__file__).resolve().parent
INVOICE_DIR = Path(settings.PDF_OUTPUT_DIR)
INVOICE_DIR.mkdir(exist_ok=True)

# Store validation results
validation_store = {}

# Request Models
class StoreIDComparisonRequest(BaseModel):
    invoice_sheet_id: str = Field(
        default=settings.SHEET_DEFAULTS["INVOICE_SHEET_ID"],
        description="Invoice data sheet ID"
    )
    invoice_range: str = Field(
        default=settings.SHEET_DEFAULTS["INVOICE_RANGE"],
        description="Invoice data range"
    )
    master_sheet_id: str = Field(
        default=settings.SHEET_DEFAULTS["MASTER_SHEET_ID"],
        description="Master store list sheet ID"
    )
    master_range: str = Field(
        default=settings.SHEET_DEFAULTS["MASTER_RANGE"],
        description="Master store list range"
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Optional customer ID for custom configurations"
    )

class InvoiceRequest(BaseModel):
    spreadsheet_id: str = Field(
        default=settings.SHEET_DEFAULTS["INVOICE_SHEET_ID"],
        description="Google Sheets ID"
    )
    range_name: str = Field(
        default=settings.SHEET_DEFAULTS["INVOICE_RANGE"],
        description="Sheet range"
    )
    max_pdfs: int = Field(
        default=settings.SHEET_DEFAULTS["MAX_PDFS"],
        description="Maximum number of PDFs to generate (-1 for all)",
        ge=-1
    )
    customer_id: Optional[str] = Field(
        default=None,
        description="Optional customer ID for custom configurations"
    )

class ValidationResponse(BaseModel):
    validation_id: str
    status: str
    message: str
    data_summary: Dict
    validation_summary: Dict = Field(..., description="Detailed validation results")
    error_details: List[Dict] = []
    warning_details: List[Dict] = []

# ... (continued from Part 1) ...

@app.get("/", response_class=HTMLResponse)
async def root():
    """Simple welcome page"""
    return """
    <html>
        <body style="font-family: Arial; margin: 40px;">
            <h1>TODC Invoice Generator</h1>
            <p>Two-step process:</p>
            <ol>
                <li>Validate data</li>
                <li>Download PDFs</li>
            </ol>
            <a href="/docs" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                Open API Documentation
            </a>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint for GCP load balancer"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/analyze-store-matches")
async def analyze_store_matches(request: StoreIDComparisonRequest):
    """Analyze store matches and deposit ID status."""
    try:
        # Get customer-specific or default config
        config = settings.get_customer_config(request.customer_id)
        
        # Apply configuration
        request_dict = request.dict()
        request_dict.update(config)
        request = StoreIDComparisonRequest(**request_dict)

        comparison = StoreIDComparison()
        result = comparison.analyze_deposit_match_status(
            invoice_sheet_id=request.invoice_sheet_id,
            master_sheet_id=request.master_sheet_id,
            invoice_range=request.invoice_range,
            master_range=request.master_range
        )
        
        return {
            "status": "success",
            "analysis_timestamp": datetime.now().isoformat(),
            "results": result,
            "next_steps": [
                "Review unmatched stores",
                "Verify stores marked as matched but missing from master sheet",
                "Update master data if needed"
            ]
        }
    except Exception as e:
        logger.error(f"Store match analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Store match analysis failed",
                "error": str(e),
                "type": "analysis_error"
            }
        )

@app.post("/validate", response_model=ValidationResponse)
async def validate_data(request: InvoiceRequest):
    """Validate the data before generating PDFs"""
    try:
        # Apply customer config if provided
        config = settings.get_customer_config(request.customer_id)
        request_dict = request.dict()
        request_dict.update(config)
        request = InvoiceRequest(**request_dict)

        # Generate validation ID
        validation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Fetch data
        sheets_helper = GoogleSheetsHelper()
        df = sheets_helper.get_sheet_data(request.spreadsheet_id, request.range_name)
        
        # Create validator instance
        validator = InvoiceValidator()
        
        # Perform validation
        validation_passed, warnings = validator.validate_dataframe(df)
        
        # Get detailed error summary
        validation_summary = validator.get_error_summary()
        
        # Create data summary
        data_summary = {
            "total_records": len(df),
            "unique_bill_owners": len(set(df['BillOwnerName'])),
            "date_range": f"{df['Order Week'].min()} to {df['Order Week'].max()}",
            "platforms": list(set(df['Platform_x'])),
            "sample_restaurants": list(df['Restaurant'].unique())[:5],
            "total_orders": int(df['Sum of Order Count'].sum()),
            "total_payout": f"${df['Sum of Total payout'].sum():,.2f}",
            "platform_breakdown": df.groupby('Platform_x').size().to_dict()
        }
        
        # Store validation result
        validation_store[validation_id] = {
            "passed": validation_passed,
            "data": None,
            "request": request.dict()
        }

        if validation_passed:
            processor = InvoiceProcessor(df)
            invoice_data = processor.process_invoices()
            validation_store[validation_id]["data"] = invoice_data
        
        return ValidationResponse(
            validation_id=validation_id,
            status="valid" if validation_passed else "invalid",
            message="Validation successful! Ready to generate PDFs." if validation_passed 
                   else "Validation failed. Please fix the errors and try again.",
            data_summary=data_summary,
            validation_summary=validation_summary,
            error_details=validation_summary['error_details'],
            warning_details=validation_summary['warning_details']
        )
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Validation process failed",
                "error": str(e),
                "type": "validation_error"
            }
        )



# Configure logging


@app.post("/generate-pdfs/{validation_id}")
async def generate_pdfs(validation_id: str,background_tasks: BackgroundTasks):
    """Generate PDFs and return ZIP file"""
    output_dir = None
    
    try:
        # Validation checks
        if validation_id not in validation_store:
            logger.error(f"Validation ID {validation_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Validation ID not found. Please validate data first."
            )
            
        validation_result = validation_store[validation_id]
        if not validation_result["passed"]:
            logger.error("Validation failed")
            raise HTTPException(
                status_code=400,
                detail="Data validation failed. Cannot generate PDFs."
            )

        # Create output directory with absolute path
        output_dir = INVOICE_DIR / validation_id
        output_dir = output_dir.absolute()
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created directory: {output_dir}")

        # Initialize PDF generator with absolute path
        pdf_generator = ModernPDFGenerator(output_dir=str(output_dir))
        
        # Get data to process
        bill_owners = validation_result["data"]["bill_owners"]
        if validation_result["request"]["max_pdfs"] != -1:
            bill_owners = bill_owners[:validation_result["request"]["max_pdfs"]]
        
        logger.info(f"Processing {len(bill_owners)} bill owners")

        # Generate PDFs using batch processing
        batch_size = 5  # Adjust based on your needs
        generated_files = await pdf_generator.generate_pdfs_batch(
            data_list=bill_owners,
            batch_size=batch_size
        )

        if not generated_files:
            raise Exception("No PDFs were generated successfully")

        # Create ZIP file
        zip_path = output_dir / f"invoices_{validation_id}.zip"
        logger.info(f"Creating ZIP at: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in generated_files:
                if file and os.path.exists(file) and str(output_dir) in str(file):  # Check if file exists
                    archive_name = os.path.basename(file)
                    zip_file.write(file, archive_name)
                    logger.info(f"Added to ZIP: {archive_name}")

        if not os.path.exists(zip_path):
            raise Exception("ZIP file was not created")

        logger.info(f"ZIP created successfully: {zip_path}")

        def cleanup():
            try:
                if output_dir.exists():
                    shutil.rmtree(output_dir)
                if validation_id in validation_store:
                    del validation_store[validation_id]
                logger.info(f"Cleaned up resources for {validation_id}")
            except Exception as e:
                logger.error(f"Cleanup failed: {str(e)}")

        background_tasks.add_task(cleanup)

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"invoices_{validation_id}.zip"
        )

    except Exception as e:
        logger.exception("Error in generate_pdfs:")
        if output_dir and output_dir.exists():
            try:
                shutil.rmtree(output_dir)
                logger.info("Cleaned up after error")
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {str(cleanup_error)}")
        
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@app.post("/maintenance/cleanup")
async def cleanup_old_files():
    """Cleanup old generated files"""
    try:
        cleanup_count = 0
        current_time = datetime.now().timestamp()
        
        for item in INVOICE_DIR.glob("*"):
            if item.is_file():
                file_age = current_time - item.stat().st_mtime
                if file_age > 86400:  # 24 hours
                    item.unlink()
                    cleanup_count += 1
        
        return {
            "status": "success",
            "files_removed": cleanup_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup operation failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.API_HOST, 
        port=settings.API_PORT
    )