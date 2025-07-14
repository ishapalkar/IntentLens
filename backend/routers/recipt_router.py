from fastapi import APIRouter, UploadFile, File
from services.ocr_service import (
    extract_text_from_image, 
    extract_items_with_brands, 
    get_available_products_by_category,
    suggest_alternatives
)
from services.recommendation_service import get_recommendations
import os, shutil

router = APIRouter()

@router.post("/recommend/")
async def recommend(file: UploadFile = File(...)):
    os.makedirs("receipts", exist_ok=True)
    path = f"receipts/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Enhanced text extraction
    raw_text = extract_text_from_image(path)
    
    # Extract only product items (filtered)
    extracted_items = extract_items_with_brands(raw_text)
    
    # Get available products by category
    available_products = get_available_products_by_category()
    
    # Generate alternatives for extracted items
    alternatives = suggest_alternatives(extracted_items)
    
    # Simple fallback if enhanced extraction fails
    if not extracted_items:
        items = [line.strip() for line in raw_text.split("\n") if line.strip()][:10]
        extracted_items = [{"product_name": item, "original_text": item, "brands": [], "categories": []} for item in items]

    token = "YOUR_EBAY_OAUTH_TOKEN"  # 🔐 Replace with your actual eBay token
    
    # Get recommendations for the first few items
    item_texts = [item["product_name"] for item in extracted_items[:5]]
    recommendations = get_recommendations(item_texts, token)

    return {
        "raw_extracted_text": raw_text,
        "filtered_items": extracted_items,
        "alternatives": alternatives,
        "available_products_by_category": available_products,
        "recommendations": recommendations,
        "summary": {
            "total_items_found": len(extracted_items),
            "items_with_brands": len([item for item in extracted_items if item["brands"]]),
            "categories_found": list(set([cat for item in extracted_items for cat in item["categories"]]))
        }
    }

@router.get("/available-products/")
async def get_available_products():
    """Get all available products organized by category"""
    available_products = get_available_products_by_category()
    return {
        "products_by_category": available_products,
        "total_categories": len(available_products),
        "total_brands": sum(len(brands) for brands in available_products.values())
    }
