from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from routers import recipt_router

app = FastAPI()

# Allow frontend to talk to backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recipt_router.router)

class GoalRequest(BaseModel):
    goal: str

# Simple rule-based mapping
goal_to_categories = {
    "moving": ["Cleaning", "Cookware", "Storage"],
    "camping": ["Tent", "Lighting", "Snacks"],
    "baby": ["Baby care", "Decor", "Gifts"]
}

# Load product catalog (optional: move to DB later)
all_products = []
with open("intent_dataset.jsonl") as f:
    for line in f:
        if line.strip():  # Skip empty lines
            data = json.loads(line.strip())
            # Parse the nested JSON in the output field
            output_data = json.loads(data["output"])
            # Create a flattened structure for easier processing
            processed_item = {
                "input": data["input"],
                "intent": output_data["intent"],
                "categories": output_data["categories"],
                "urgency": output_data.get("urgency", "medium"),
                "budgetRange": output_data.get("budgetRange", "medium")
            }
            all_products.append(processed_item)

@app.post("/api/generate-cart")
def generate_cart(data: GoalRequest):
    user_goal = data.goal.lower()
    matched_categories = []

    for keyword in goal_to_categories:
        if keyword in user_goal:
            matched_categories = goal_to_categories[keyword]
            break

    # Check if any of the product's categories match our target categories
    matched_products = []
    for product in all_products:
        if any(cat.lower() in [mc.lower() for mc in matched_categories] for cat in product["categories"]):
            matched_products.append(product)

    return {"intent": keyword if matched_categories else "unknown", "products": matched_products}
