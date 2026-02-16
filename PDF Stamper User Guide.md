# PDF Stamper User Guide

This application allows you to automatically add signatures, stamps and dates to PDF documents, with support for storing agency-specific assets in a MongoDB database.

## Setup Instructions

1. Run `setup.bat` to set up the Python environment and dependencies
2. Install MongoDB Community Server if you haven't already
3. Make sure MongoDB service is running
4. Run the MongoDB setup script: `mongosh --file setup_db.js`
5. Start the application by running `run_pdf_stamper.bat`

## Using the Application

The application has two main tabs:

### Process PDF Tab

This tab allows you to process PDFs by adding signatures, stamps, and dates.

1. **Select PDF**: Click "Browse" to select a PDF file for processing
2. **Agency Detection**: The application will attempt to detect the agency name from the PDF
3. **Agency Selection**:
   - If "Use database assets for detected agency" is checked, the application will automatically load signature and stamp images for the detected agency
   - You can override with a different agency by selecting from the dropdown and clicking "Apply"
4. **Signature and Stamp**: You can also manually select signature and stamp images
5. **Date**: You can enter a date or click "Today" to use today's date. If left empty, the application will try to extract "Date of inspection" from the PDF
6. **Process PDF**: Click this button to create a stamped version of the PDF

### Agency Management Tab

This tab allows you to manage agency signatures and stamps in the database.

1. **Select Agency**: Choose an existing agency from the dropdown to load or delete
2. **Add/Update Agency**:
   - Enter agency name
   - Select signature and stamp images
   - Click "Save to Database" to store or update the agency's assets

## Important Notes

- The application looks for text like "Signature", "Seal of PSIA", and "Date" in the PDF to determine where to place elements
- Processed PDFs are saved with a "stamped_" prefix in the same folder as the original
- Agency names are extracted from the first few lines of the PDF, looking for patterns like "Agency:" or similar text
- All database operations require an active MongoDB connection

## Troubleshooting

- If the database connection fails, check if MongoDB is running on localhost:27017
- If elements are not being placed properly, verify that the PDF contains the expected text markers
- If agency detection fails, you can manually select an agency from the dropdown