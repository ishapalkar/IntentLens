import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import json
import re

# ✅ Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(image_path):
    """Preprocess image for better OCR results"""
    # Read image with OpenCV
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply threshold to get better contrast
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphological operations to clean up the image
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned

def extract_text_from_image(image_path):
    """Extract text from receipt image with enhanced OCR configuration"""
    try:
        # Preprocess the image
        processed_img = preprocess_image(image_path)
        
        # Convert back to PIL Image for pytesseract
        pil_img = Image.fromarray(processed_img)
        
        # Enhanced OCR configuration for receipts
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,-₹$() '
        
        # Extract text with custom configuration
        text = pytesseract.image_to_string(pil_img, config=custom_config)
        
        # Clean up the extracted text
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 1:  # Filter out single characters and empty lines
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
        
    except Exception as e:
        print(f"OCR Error: {e}")
        # Fallback to basic OCR
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)

def extract_items_with_brands(text, category_brands_path="category_to_brands.json"):
    """Extract only product items and match them with known brands"""
    try:
        # Load brand categories
        with open(category_brands_path, 'r') as f:
            brand_data = json.load(f)
        
        # Create a flat list of all brands
        all_brands = []
        brand_to_category = {}
        for category, brands in brand_data.items():
            for brand in brands:
                all_brands.append(brand.lower())
                brand_to_category[brand.lower()] = category
        
        # Common store/receipt keywords to filter out
        filter_keywords = [
            'receipt', 'bill', 'invoice', 'store', 'mall', 'supermarket', 'shop',
            'address', 'phone', 'tel', 'fax', 'email', 'website', 'www',
            'thank you', 'thanks', 'welcome', 'visit again', 'customer',
            'cashier', 'counter', 'total', 'subtotal', 'tax', 'gst', 'vat',
            'cash', 'card', 'payment', 'change', 'balance', 'tender',
            'date', 'time', 'transaction', 'ref', 'reference', 'no.',
            'ltd', 'pvt', 'private', 'limited', 'company', 'corp',
            'branch', 'outlet', 'location', 'center', 'centre'
        ]
        
        # Extract potential items from text
        lines = text.split('\n')
        extracted_items = []
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:  # Skip very short lines
                continue
            
            line_lower = line.lower()
            
            # Skip lines that contain store/receipt keywords
            if any(keyword in line_lower for keyword in filter_keywords):
                continue
            
            # Skip lines that are mostly numbers or special characters
            if re.match(r'^[\d\s\-\.\,\:\(\)]+$', line):
                continue
            
            # Skip lines that look like addresses or phone numbers
            if re.search(r'\d{10,}|\d+\s*-\s*\d+|\d+\s*,\s*\d+', line):
                continue
            
            # Look for lines that might contain product names
            # Products usually have some alphabetic characters and may have prices
            if re.search(r'[a-zA-Z]{2,}', line):
                # Check if any known brand is in this line
                matched_brands = []
                matched_categories = []
                
                for brand in all_brands:
                    if brand in line_lower:
                        matched_brands.append(brand.title())
                        matched_categories.append(brand_to_category[brand])
                
                # Extract just the product name (remove price patterns)
                product_name = re.sub(r'[\d\.,]*\s*[₹Rs\$]\s*[\d\.,]*', '', line).strip()
                product_name = re.sub(r'\s*x\s*\d+\s*', '', product_name).strip()  # Remove quantity
                product_name = re.sub(r'\s+', ' ', product_name)  # Clean multiple spaces
                
                if product_name and len(product_name) > 2:
                    item_info = {
                        "product_name": product_name,
                        "original_text": line,
                        "brands": matched_brands,
                        "categories": list(set(matched_categories))
                    }
                    extracted_items.append(item_info)
        
        return extracted_items
        
    except Exception as e:
        print(f"Brand extraction error: {e}")
        # Fallback to simple line extraction
        lines = text.split('\n')
        filtered_items = []
        
        for line in lines:
            line = line.strip()
            if (line and len(line) > 2 and 
                not re.match(r'^[\d\s\-\.\,\:\(\)]+$', line) and
                re.search(r'[a-zA-Z]{2,}', line)):
                
                product_name = re.sub(r'[\d\.,]*\s*[₹Rs\$]\s*[\d\.,]*', '', line).strip()
                if product_name:
                    filtered_items.append({
                        "product_name": product_name,
                        "original_text": line,
                        "brands": [],
                        "categories": []
                    })
        
        return filtered_items

def get_available_products_by_category(category_brands_path="category_to_brands.json"):
    """Get all available products organized by category"""
    try:
        with open(category_brands_path, 'r') as f:
            brand_data = json.load(f)
        
        return brand_data
    except Exception as e:
        print(f"Error loading product categories: {e}")
        return {}

def suggest_alternatives(extracted_items, category_brands_path="category_to_brands.json"):
    """Suggest alternative products based on extracted items"""
    try:
        with open(category_brands_path, 'r') as f:
            brand_data = json.load(f)
        
        suggestions = {}
        
        for item in extracted_items:
            if item["categories"]:
                for category in item["categories"]:
                    if category in brand_data:
                        # Get other brands in the same category
                        alternative_brands = [brand for brand in brand_data[category] 
                                            if brand.lower() not in [b.lower() for b in item["brands"]]]
                        
                        if alternative_brands:
                            suggestions[item["product_name"]] = {
                                "category": category,
                                "alternatives": alternative_brands,
                                "original_brands": item["brands"]
                            }
            else:
                # Try to match by product name keywords
                product_lower = item["product_name"].lower()
                for category, brands in brand_data.items():
                    # Simple keyword matching for categories
                    category_keywords = {
                        "Dairy": ["milk", "cheese", "yogurt", "curd", "butter"],
                        "Instant Food": ["noodles", "pasta", "instant", "ready"],
                        "Flour": ["flour", "atta", "maida", "wheat"],
                        "Spices": ["spice", "masala", "powder", "turmeric", "chili"],
                        "Snacks": ["chips", "namkeen", "biscuit", "cookie"],
                        "Beverages": ["juice", "drink", "water", "cola", "tea", "coffee"]
                    }
                    
                    if category in category_keywords:
                        if any(keyword in product_lower for keyword in category_keywords[category]):
                            suggestions[item["product_name"]] = {
                                "category": category,
                                "alternatives": brands,
                                "original_brands": []
                            }
                            break
        
        return suggestions
    except Exception as e:
        print(f"Error generating suggestions: {e}")
        return {}
