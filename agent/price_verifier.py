
from vertexai.generative_models import GenerativeModel
import json
import re
from config import settings
from typing import List, Dict, Any

class PriceVerifier:
    """
    Independent Agent for verifying order prices against the store guide.
    Uses a dedicated LLM call to ensure accuracy.
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.PRICE_MODEL_NAME
        self.model = GenerativeModel(model_name=self.model_name)

    def verify_price(self, store_guide: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates the exact price for the given items based on the store guide.
        Returns a dictionary with detailed pricing breakdown.
        """
        if not items:
            return {
                "total_price": 0,
                "item_total": 0,
                "shipping": 0,
                "breakdown": [],
                "reasoning": "No items provided."
            }

        prompt = (
            "You are a Strict Price Verification Auditor. Your goal is to calculate the EXACT total price for an order based on the provided Store Guide.\n"
            "Do not guess. Match product names and units exactly.\n\n"
            f"STORE GUIDE:\n{store_guide}\n\n"
            f"ORDER ITEMS:\n{json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
            "INSTRUCTIONS:\n"
            "1. For each item, find its exact match in the Store Guide. Pay attention to 'Unit' (e.g. 1kg vs 500g) and 'Option'.\n"
            "2. Extract the unit price.\n"
            "3. Calculate Item Subtotal = Unit Price * Quantity.\n"
            "4. Sum all Item Subtotals to get 'Item Total'.\n"
            "5. Apply Shipping Rules from the guide (e.g. 'Free shipping over 50,000 won', else '4,000 won').\n"
            "6. Calculate 'Final Total' = Item Total + Shipping Fee.\n"
            "7. Return the result in JSON format ONLY.\n\n"
            "JSON OUTPUT FORMAT:\n"
            "{\n"
            "  \"items\": [\n"
            "    {\"product_name\": \"...\", \"unit\": \"...\", \"unit_price\": 1000, \"quantity\": 2, \"subtotal\": 2000}\n"
            "  ],\n"
            "  \"item_total\": 2000,\n"
            "  \"shipping_fee\": 0,\n"
            "  \"final_total\": 2000,\n"
            "  \"reasoning\": \"Brief explanation\"\n"
            "}"
        )

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # Clean up code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            result = json.loads(text)
            return result

        except Exception as e:
            print(f"[PriceVerifier] Error: {e}")
            return {
                "total_price": 0,
                "item_total": 0,
                "shipping_fee": 0,
                "error": str(e)
            }
