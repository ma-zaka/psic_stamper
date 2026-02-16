// MongoDB setup script for PDF Stamper
// Run with: mongo setup_db.js

// Create the database and collections
db = db.getSiblingDB('pdf_stamper');

// Create the agencies collection for storing agency information
db.createCollection('agencies');

// Create an index on the agency name for faster lookups
db.agencies.createIndex({ name: 1 }, { unique: true });

// Example document structure:
// {
//   "name": "Agency Name",
//   "signature_id": ObjectId("..."),  // Reference to GridFS file
//   "stamp_id": ObjectId("..."),      // Reference to GridFS file
//   "created_at": ISODate("..."),
//   "updated_at": ISODate("...")
// }

print("PDF Stamper database setup complete!");