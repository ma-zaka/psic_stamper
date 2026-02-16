import pymongo
import gridfs
import os
import tempfile
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.fs = None
        self.agencies_collection = None
        self.connected = False
        self.temp_files = []
    
    def connect(self, connection_string="mongodb://localhost:27017/"):
        """Connect to MongoDB database"""
        try:
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client["pdf_stamper"]
            self.agencies_collection = self.db["agencies"]
            self.fs = gridfs.GridFS(self.db)
            self.connected = True
            return True
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            self.connected = False
            return False
    
    def is_connected(self):
        """Check if connected to database"""
        return self.connected
    
    def add_update_agency(self, agency_name, signature_path, stamp_path):
        """Add or update an agency in the database"""
        if not self.connected:
            return False, "Database not connected"
        
        try:
            # Read image files
            with open(signature_path, 'rb') as signature_file:
                signature_data = signature_file.read()
                
            with open(stamp_path, 'rb') as stamp_file:
                stamp_data = stamp_file.read()
            
            # Store images in GridFS
            signature_id = self.fs.put(signature_data, filename=f"{agency_name}_signature.png")
            stamp_id = self.fs.put(stamp_data, filename=f"{agency_name}_stamp.png")
            
            # Check if agency already exists
            existing_agency = self.agencies_collection.find_one({"name": agency_name})
            
            if existing_agency:
                # Delete old files if they exist
                if 'signature_id' in existing_agency:
                    self.fs.delete(existing_agency['signature_id'])
                if 'stamp_id' in existing_agency:
                    self.fs.delete(existing_agency['stamp_id'])
                
                # Update the agency
                self.agencies_collection.update_one(
                    {"name": agency_name},
                    {"$set": {
                        "signature_id": signature_id,
                        "stamp_id": stamp_id,
                        "updated_at": datetime.now()
                    }}
                )
                return True, f"Agency '{agency_name}' updated successfully"
            else:
                # Insert new agency
                self.agencies_collection.insert_one({
                    "name": agency_name,
                    "signature_id": signature_id,
                    "stamp_id": stamp_id,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
                return True, f"Agency '{agency_name}' added successfully"
                
        except Exception as e:
            return False, f"Failed to add/update agency: {str(e)}"
    
    def get_agency_assets(self, agency_name):
        """Get signature and stamp images for an agency"""
        if not self.connected:
            return False, "Database not connected", None, None
        
        try:
            # Find the agency in the database
            agency = self.agencies_collection.find_one({"name": agency_name})
            if not agency:
                return False, f"Agency '{agency_name}' not found", None, None
            
            # Create temporary files for the images
            temp_signature_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_stamp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            
            # Get signature from GridFS
            if 'signature_id' in agency:
                signature_file = self.fs.get(agency['signature_id'])
                temp_signature_file.write(signature_file.read())
                temp_signature_file.close()
                # Add to temp files list for cleanup later
                self.temp_files.append(temp_signature_file.name)
            else:
                temp_signature_file.close()
                os.unlink(temp_signature_file.name)
                temp_signature_file = None
            
            # Get stamp from GridFS
            if 'stamp_id' in agency:
                stamp_file = self.fs.get(agency['stamp_id'])
                temp_stamp_file.write(stamp_file.read())
                temp_stamp_file.close()
                # Add to temp files list for cleanup later
                self.temp_files.append(temp_stamp_file.name)
            else:
                temp_stamp_file.close()
                os.unlink(temp_stamp_file.name)
                temp_stamp_file = None
                
            return True, "Assets loaded successfully", \
                   temp_signature_file.name if temp_signature_file else None, \
                   temp_stamp_file.name if temp_stamp_file else None
                   
        except Exception as e:
            return False, f"Failed to load agency assets: {str(e)}", None, None
    
    def get_all_agencies(self):
        """Get a list of all agency names"""
        if not self.connected:
            return []
        
        try:
            agencies = self.agencies_collection.find({}, {"name": 1, "_id": 0})
            return [agency["name"] for agency in agencies]
        except Exception as e:
            print(f"Error getting agencies: {str(e)}")
            return []
    
    def delete_agency(self, agency_name):
        """Delete an agency from the database"""
        if not self.connected:
            return False, "Database not connected"
        
        try:
            # Find the agency
            agency = self.agencies_collection.find_one({"name": agency_name})
            if not agency:
                return False, f"Agency '{agency_name}' not found"
            
            # Delete associated files
            if 'signature_id' in agency:
                self.fs.delete(agency['signature_id'])
            if 'stamp_id' in agency:
                self.fs.delete(agency['stamp_id'])
            
            # Delete the agency record
            self.agencies_collection.delete_one({"name": agency_name})
            
            return True, f"Agency '{agency_name}' deleted successfully"
            
        except Exception as e:
            return False, f"Failed to delete agency: {str(e)}"
    
    def cleanup_temp_files(self):
        """Clean up all temporary files"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error cleaning up temp file {file_path}: {str(e)}")
        
        self.temp_files = []
    
    def close(self):
        """Close database connection and clean up resources"""
        self.cleanup_temp_files()
        if self.client:
            self.client.close()
            self.connected = False