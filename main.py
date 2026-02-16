import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw
import PyPDF2
import os
import io
import re
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from datetime import datetime
import tempfile

# Import the database manager
from db_manager import DatabaseManager

class PDFStamperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Stamper")
        self.root.geometry("800x600")
        
        # Initialize the database manager
        self.db_manager = DatabaseManager()
        self.db_connected = self.db_manager.connect()
        
        # Create assets directory if it doesn't exist
        self.assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Default signature and stamp paths
        self.default_signature_path = os.path.join(self.assets_dir, "default_signature.png")
        self.default_stamp_path = os.path.join(self.assets_dir, "default_stamp.png")
        
        # Create default signature and stamp if they don't exist
        self.create_default_images()
        
        # Variables
        self.pdf_path = tk.StringVar()
        self.signature_path = tk.StringVar(value=self.default_signature_path)
        self.stamp_path = tk.StringVar(value=self.default_stamp_path)
        self.date_value = tk.StringVar()
        self.detected_agency = tk.StringVar(value="None detected")
        self.use_database_assets = tk.BooleanVar(value=True)
        self.selected_agency = tk.StringVar()
        
        # Create the notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create the main processing tab
        self.process_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.process_tab, text="Process PDF")
        
        # Create the admin tab
        self.admin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.admin_tab, text="Agency Management")
        
        # Set up the main processing tab
        self.setup_process_tab()
        
        # Set up the admin tab
        self.setup_admin_tab()
        
        # Show database connection status
        if self.db_connected:
            self.status_var = tk.StringVar(value="Database: Connected")
        else:
            self.status_var = tk.StringVar(value="Database: Disconnected")
        
        # Status bar
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_process_tab(self):
        """Set up the main PDF processing tab"""
        frame = self.process_tab
        
        # File selection section
        ttk.Label(frame, text="PDF Processing", font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        # PDF file selection
        ttk.Label(frame, text="PDF File:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.pdf_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.select_pdf).grid(row=1, column=2)
        
        # Agency detection and selection
        ttk.Label(frame, text="Detected Agency:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(frame, textvariable=self.detected_agency).grid(row=2, column=1, sticky=tk.W)
        
        # Create a frame for agency selection
        agency_frame = ttk.LabelFrame(frame, text="Agency Selection")
        agency_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        # Database assets checkbox
        ttk.Checkbutton(
            agency_frame, 
            text="Use database assets for detected agency",
            variable=self.use_database_assets,
            command=self.toggle_database_assets
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Agency dropdown (for override)
        ttk.Label(agency_frame, text="Override with agency:").grid(row=1, column=0, sticky=tk.W)
        
        # Get agencies from database
        agencies = self.db_manager.get_all_agencies() if self.db_connected else []
        agencies.insert(0, "")  # Add empty option
        
        self.agency_combo = ttk.Combobox(agency_frame, textvariable=self.selected_agency, values=agencies)
        self.agency_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(agency_frame, text="Apply", command=self.apply_selected_agency).grid(row=1, column=2)
        
        # Signature file selection
        ttk.Label(frame, text="Signature:").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.signature_path, width=50).grid(row=4, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.select_signature).grid(row=4, column=2)
        
        # Stamp file selection
        ttk.Label(frame, text="Stamp:").grid(row=5, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.stamp_path, width=50).grid(row=5, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.select_stamp).grid(row=5, column=2)
        
        # Date input
        ttk.Label(frame, text="Date (optional):").grid(row=6, column=0, sticky=tk.W)
        date_entry = ttk.Entry(frame, textvariable=self.date_value, width=50)
        date_entry.grid(row=6, column=1, padx=5)
        ttk.Button(frame, text="Today", command=self.set_today_date).grid(row=6, column=2)
        
        # Add helper text
        ttk.Label(frame, text="Leave empty to use 'Date of inspection' from document").grid(row=7, column=1, sticky=tk.W, padx=5)
        
        # Process button
        ttk.Button(frame, text="Process PDF", command=self.process_pdf).grid(row=8, column=0, columnspan=3, pady=20)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)
    
    def setup_admin_tab(self):
        """Set up the agency management tab"""
        frame = self.admin_tab
        
        # Admin section
        ttk.Label(frame, text="Agency Management", font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        # Create frame for agency selection
        selection_frame = ttk.LabelFrame(frame, text="Select Agency")
        selection_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        # Get agencies from database
        agencies = self.db_manager.get_all_agencies() if self.db_connected else []
        
        # Agency selection dropdown
        ttk.Label(selection_frame, text="Agency:").grid(row=0, column=0, sticky=tk.W)
        self.admin_agency_combo = ttk.Combobox(selection_frame, values=agencies)
        self.admin_agency_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(selection_frame, text="Load", command=self.admin_load_agency).grid(row=0, column=2)
        ttk.Button(selection_frame, text="Delete", command=self.admin_delete_agency).grid(row=0, column=3)
        
        # Create frame for new agency
        new_agency_frame = ttk.LabelFrame(frame, text="Add/Update Agency")
        new_agency_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        # Agency name entry
        ttk.Label(new_agency_frame, text="Agency Name:").grid(row=0, column=0, sticky=tk.W)
        self.admin_agency_name = ttk.Entry(new_agency_frame, width=50)
        self.admin_agency_name.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Signature file selection
        ttk.Label(new_agency_frame, text="Signature:").grid(row=1, column=0, sticky=tk.W)
        self.admin_signature_path = tk.StringVar(value=self.default_signature_path)
        ttk.Entry(new_agency_frame, textvariable=self.admin_signature_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(new_agency_frame, text="Browse", command=self.admin_select_signature).grid(row=1, column=2)
        
        # Stamp file selection
        ttk.Label(new_agency_frame, text="Stamp:").grid(row=2, column=0, sticky=tk.W)
        self.admin_stamp_path = tk.StringVar(value=self.default_stamp_path)
        ttk.Entry(new_agency_frame, textvariable=self.admin_stamp_path, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(new_agency_frame, text="Browse", command=self.admin_select_stamp).grid(row=2, column=2)
        
        # Save button
        ttk.Button(new_agency_frame, text="Save to Database", command=self.admin_save_agency).grid(
            row=3, column=0, columnspan=3, pady=10)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)
        selection_frame.columnconfigure(1, weight=1)
        new_agency_frame.columnconfigure(1, weight=1)
    
    def admin_load_agency(self):
        """Load agency from the selection dropdown"""
        agency_name = self.admin_agency_combo.get()
        if not agency_name:
            messagebox.showerror("Error", "Please select an agency")
            return
        
        success, message, signature_path, stamp_path = self.db_manager.get_agency_assets(agency_name)
        
        if success:
            self.admin_agency_name.delete(0, tk.END)
            self.admin_agency_name.insert(0, agency_name)
            
            if signature_path:
                self.admin_signature_path.set(signature_path)
            else:
                self.admin_signature_path.set(self.default_signature_path)
                
            if stamp_path:
                self.admin_stamp_path.set(stamp_path)
            else:
                self.admin_stamp_path.set(self.default_stamp_path)
        else:
            messagebox.showerror("Error", message)
    
    def admin_delete_agency(self):
        """Delete the selected agency"""
        agency_name = self.admin_agency_combo.get()
        if not agency_name:
            messagebox.showerror("Error", "Please select an agency")
            return
            
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete agency '{agency_name}'?"):
            success, message = self.db_manager.delete_agency(agency_name)
            
            if success:
                messagebox.showinfo("Success", message)
                # Update the dropdown list
                agencies = self.db_manager.get_all_agencies()
                self.admin_agency_combo['values'] = agencies
                self.agency_combo['values'] = [""] + agencies
                # Clear the agency name field
                self.admin_agency_name.delete(0, tk.END)
            else:
                messagebox.showerror("Error", message)
    
    def admin_save_agency(self):
        """Save agency to database"""
        agency_name = self.admin_agency_name.get().strip()
        if not agency_name:
            messagebox.showerror("Error", "Please enter an agency name")
            return
            
        if not os.path.exists(self.admin_signature_path.get()):
            messagebox.showerror("Error", "Signature file not found")
            return
            
        if not os.path.exists(self.admin_stamp_path.get()):
            messagebox.showerror("Error", "Stamp file not found")
            return
        
        success, message = self.db_manager.add_update_agency(
            agency_name, 
            self.admin_signature_path.get(), 
            self.admin_stamp_path.get()
        )
        
        if success:
            messagebox.showinfo("Success", message)
            # Update the dropdown lists
            agencies = self.db_manager.get_all_agencies()
            self.admin_agency_combo['values'] = agencies
            self.agency_combo['values'] = [""] + agencies
        else:
            messagebox.showerror("Error", message)
    
    def admin_select_signature(self):
        """Select signature file for admin"""
        filename = filedialog.askopenfilename(
            title="Select Signature",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if filename:
            self.admin_signature_path.set(filename)
    
    def admin_select_stamp(self):
        """Select stamp file for admin"""
        filename = filedialog.askopenfilename(
            title="Select Stamp",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if filename:
            self.admin_stamp_path.set(filename)
    
    def apply_selected_agency(self):
        """Apply the selected agency from the dropdown"""
        agency_name = self.selected_agency.get()
        if agency_name:
            success, message, signature_path, stamp_path = self.db_manager.get_agency_assets(agency_name)
            
            if success:
                if signature_path:
                    self.signature_path.set(signature_path)
                if stamp_path:
                    self.stamp_path.set(stamp_path)
                messagebox.showinfo("Success", f"Agency '{agency_name}' assets loaded")
            else:
                messagebox.showerror("Error", message)
    
    def create_default_images(self):
        """Create default signature and stamp images if they don't exist"""
        # Create a simple signature image (white background with black text)
        if not os.path.exists(self.default_signature_path):
            img = Image.new('RGBA', (200, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.text((50, 40), "Signature", fill=(0, 0, 0, 255))
            img.save(self.default_signature_path)
        
        # Create a simple stamp image (red circle with text)
        if not os.path.exists(self.default_stamp_path):
            img = Image.new('RGBA', (150, 150), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((10, 10, 140, 140), outline=(255, 0, 0, 255), width=3)
            draw.text((40, 60), "STAMP", fill=(255, 0, 0, 255))
            img.save(self.default_stamp_path)
    
    def toggle_database_assets(self):
        """Toggle between database assets and manually selected assets"""
        if self.use_database_assets.get() and self.detected_agency.get() != "None detected":
            success, message, signature_path, stamp_path = self.db_manager.get_agency_assets(self.detected_agency.get())
            
            if success:
                if signature_path:
                    self.signature_path.set(signature_path)
                if stamp_path:
                    self.stamp_path.set(stamp_path)
            else:
                # Reset to defaults if agency not found
                self.reset_signature()
                self.reset_stamp()
        else:
            self.reset_signature()
            self.reset_stamp()
    
    def extract_agency_name(self, pdf_path):
        """Extract the agency name from the PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check only the first page for agency name
                page = pdf.pages[0]
                text = page.extract_text()
                if text:
                    # Look for "Agency:" pattern in the first few lines
                    lines = text.split('\n')
                    for line in lines[:5]:  # Check first 5 lines
                        agency_match = re.search(r'Agency:\s*(.+?)(?:\s{2,}|\n|$)', line)
                        if agency_match:
                            return agency_match.group(1).strip()
                    
                    # Try alternative pattern if not found
                    for line in lines[:5]:
                        if ":" in line and not re.search(r'(Date|Time|Location|Address):', line, re.IGNORECASE):
                            parts = line.split(':', 1)
                            if len(parts) == 2 and len(parts[0]) < 30:  # Typical name length
                                return parts[0].strip()
            
            return None
        except Exception as e:
            print(f"Error extracting agency name: {str(e)}")
            return None
    
    def set_today_date(self):
        """Set today's date in the date field"""
        today = datetime.now().strftime("%d/%m/%Y")
        self.date_value.set(today)
    
    def select_pdf(self):
        filename = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if filename:
            self.pdf_path.set(filename)
            
            # Extract agency name
            agency_name = self.extract_agency_name(filename)
            if agency_name:
                self.detected_agency.set(agency_name)
                
                # Try to load assets from the database if option is enabled
                if self.use_database_assets.get():
                    success, message, signature_path, stamp_path = self.db_manager.get_agency_assets(agency_name)
                    
                    if success:
                        if signature_path:
                            self.signature_path.set(signature_path)
                        if stamp_path:
                            self.stamp_path.set(stamp_path)
                    else:
                        messagebox.showinfo("Agency Not Found", 
                                          f"Agency '{agency_name}' not found in database. Using default assets.")
                        self.reset_signature()
                        self.reset_stamp()
            else:
                self.detected_agency.set("None detected")
                self.reset_signature()
                self.reset_stamp()
    
    def select_signature(self):
        filename = filedialog.askopenfilename(
            title="Select Signature",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if filename:
            self.signature_path.set(filename)
    
    def select_stamp(self):
        filename = filedialog.askopenfilename(
            title="Select Stamp",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if filename:
            self.stamp_path.set(filename)
    
    def reset_signature(self):
        self.signature_path.set(self.default_signature_path)
    
    def reset_stamp(self):
        self.stamp_path.set(self.default_stamp_path)
    
    def extract_inspection_date(self, pdf_path):
        """Extract the 'Date of inspection' from the PDF"""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    date_match = re.search(r'Date of inspection:\s*(\d{2}/\d{2}/\d{4})', text)
                    if date_match:
                        return date_match.group(1)
        return None
    
    def find_text_positions(self, pdf_path):
        """Find the positions of 'Seal of PSIA', 'Signature', and 'Date' text in the PDF using pdfplumber"""
        signature_pos = None
        seal_pos = None
        date_pos = None
        signature_page = None
        seal_page = None
        date_page = None
        
        with pdfplumber.open(pdf_path) as pdf:
            # Determine which pages to check
            if len(pdf.pages) >= 2:
                pages_to_check = [len(pdf.pages) - 2, len(pdf.pages) - 1]
            else:
                pages_to_check = [len(pdf.pages) - 1]
            
            for page_idx in pages_to_check:
                page = pdf.pages[page_idx]
                
                # Extract text with position information
                words = page.extract_words()
                
                # Look for "Seal of PSIA" text
                for i, word in enumerate(words):
                    if word['text'] == "Seal":
                        # Check if the next word is "of PSIA"
                        if i + 1 < len(words) and words[i + 1]['text'] == "of":
                            if i + 2 < len(words) and words[i + 2]['text'] == "PSIA":
                                # Found "Seal of PSIA"
                                seal_pos = {
                                    'x': word['x0'] + 30,
                                    'y': word['top'] + 120,  # Position below the text
                                    'width': 130,
                                    'height': 130
                                }
                                seal_page = page_idx
                                break
                
                # Look for "Signature" text
                for word in words:
                    if word['text'] == "Signature":
                        # Found "Signature"
                        signature_pos = {
                            'x': word['x0'] + 60,
                            'y': word['top'] + 20,  # Position below the text
                            'width': 180,
                            'height': 55
                        }
                        signature_page = page_idx
                
                # Look for "Date" text
                for word in words:
                    if word['text'] == "Date":
                        # Found "Date"
                        date_pos = {
                            'x': word['x0'] + 30,  # Position to the right of "Date"
                            'y': word['top'] - 3,  # Same vertical position as "Date"
                            'width': 100,
                            'height': 20
                        }
                        date_page = page_idx
        
        return signature_page, seal_page, date_page, signature_pos, seal_pos, date_pos
    
    def process_pdf(self):
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return
            
        try:
            # Find the positions of the text elements
            signature_page, seal_page, date_page, signature_pos, seal_pos, date_pos = self.find_text_positions(self.pdf_path.get())
            
            if signature_page is None and seal_page is None and date_page is None:
                messagebox.showerror("Error", "Could not find 'Seal of PSIA', 'Signature', or 'Date' text in the PDF")
                return
            
            # Get date to use (either from input or from document)
            date_to_use = self.date_value.get()
            if not date_to_use:
                # Extract date from the document
                date_to_use = self.extract_inspection_date(self.pdf_path.get())
                if not date_to_use:
                    date_to_use = datetime.now().strftime("%d/%m/%Y")  # Default to today if not found
            
            # Open the PDF
            pdf_reader = PyPDF2.PdfReader(self.pdf_path.get())
            pdf_writer = PyPDF2.PdfWriter()
            
            # Load signature and stamp images
            signature_img = Image.open(self.signature_path.get())
            stamp_img = Image.open(self.stamp_path.get())
            
            # Process each page
            for i, page in enumerate(pdf_reader.pages):
                # Create a new PDF to overlay on the current page
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                
                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Flag to check if we need to add any overlay
                add_overlay = False
                
                # Add signature if position was found and this is the right page
                if signature_pos and i == signature_page:
                    can.drawImage(
                        ImageReader(signature_img), 
                        signature_pos['x'], 
                        page_height - signature_pos['y'],  # Convert from top-left to bottom-left coordinates
                        width=signature_pos['width'], 
                        height=signature_pos['height'], 
                        mask='auto'
                    )
                    add_overlay = True
                
                # Add stamp (seal) if position was found and this is the right page
                if seal_pos and i == seal_page:
                    can.drawImage(
                        ImageReader(stamp_img), 
                        seal_pos['x'], 
                        page_height - seal_pos['y'],  # Convert from top-left to bottom-left coordinates
                        width=seal_pos['width'], 
                        height=seal_pos['height'], 
                        mask='auto'
                    )
                    add_overlay = True
                
                # Add date if position was found and this is the right page
                if date_pos and i == date_page and date_to_use:
                    can.setFont("Helvetica", 12)
                    can.drawString(
                        date_pos['x'],
                        page_height - date_pos['y'] - 10,  # Position slightly below the "Date" text
                        date_to_use
                    )
                    add_overlay = True
                
                # Save the canvas only if we added any elements
                if add_overlay:
                    can.save()
                    
                    # Move to the beginning of the BytesIO buffer
                    packet.seek(0)
                    
                    # Create a new PDF with the signature and/or stamp
                    overlay = PyPDF2.PdfReader(packet)
                    
                    # Merge the original page with the overlay
                    page.merge_page(overlay.pages[0])
                
                # Add the page to the output
                pdf_writer.add_page(page)
            
            # Save the output
            output_path = os.path.join(
                os.path.dirname(self.pdf_path.get()),
                "stamped_" + os.path.basename(self.pdf_path.get())
            )
            
            with open(output_path, "wb") as output_file:
                pdf_writer.write(output_file)
            
            messagebox.showinfo("Success", f"PDF processed successfully!\nSaved as: {output_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def __del__(self):
        """Clean up resources when the app is closed"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()

def main():
    root = tk.Tk()
    app = PDFStamperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
                                    