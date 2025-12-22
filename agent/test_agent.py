


import pandas as pd
import os
import json
import ast
from datetime import datetime
import sys
import time
import re
from unittest.mock import MagicMock

# Mock OCRManager to prevents its initialization
sys.modules["ocr_manager"] = MagicMock()

from agent_engine import TextOrderAgent
from config import settings

def normalize_string(s: str) -> str:
    """Removes spaces, punctuation, mixed case for looses comparison."""
    if pd.isna(s) or s is None:
        return ""
    # Remove special chars but keep alphanum and Korean
    s = str(s).lower()
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', s)

def is_loose_match(pred: str, label: str) -> bool:
    """Checks if normalized strings match or are contained in each other."""
    n_pred = normalize_string(pred)
    n_label = normalize_string(label)
    if not n_pred or not n_label:
        return n_pred == n_label
    return n_pred == n_label or n_pred in n_label or n_label in n_pred

def calculate_correctness(predict_str: str, label_str: str) -> float:
    """
    Compares prediction info with label info to calculate correctness score (0.0 to 1.0).
    Uses loose matching (normalization/substring) for better robustness without LLM.
    """
    try:
        # 1. Parse JSON / Dict String
        if not label_str or pd.isna(label_str):
            return 0.0
            
        try:
            pred = json.loads(predict_str)
        except:
             pred = {} 
             
        # Try to clean label_str for eval
        clean_label = re.sub(r':\s*(\([^)]+\)),', r': "\1",', label_str)
        
        eval_ctx = {
            "null": None, 
            "true": True, 
            "false": False,
            "nan": None
        }
        
        try:
            label = eval(clean_label, {}, eval_ctx)
        except Exception as e:
            try:
                clean_json = clean_label.replace("null", "null").replace("True", "true").replace("False", "false")
                label = json.loads(clean_json)
            except:
                return 0.0
            
        # Fields to compare
        core_fields = [
            "customer_name", 
            "contact_number", 
            "delivery_address", 
            "desired_delivery_date",
            "expected_amount"
        ]
        
        matches = 0
        total_checks = len(core_fields) + 1 # +1 for Items
        
        # 2. Compare Core Fields
        for field in core_fields:
            p_val = pred.get(field)
            l_val = label.get(field)
            
            # Special handling for Amount
            if field == "expected_amount":
                try:
                    p_num = int(str(p_val).replace(',', '').replace('원', ''))
                    l_num = int(str(l_val).replace(',', '').replace('원', ''))
                    if p_num == l_num:
                        matches += 1
                        continue
                except:
                    pass 
            
            # Loose String Matching
            if is_loose_match(p_val, l_val):
                matches += 1
            else:
                pass
                
        # 3. Compare Items
        pred_items = pred.get("items", [])
        label_items = label.get("items", [])
        
        items_score = 0
        if not label_items:
            # If label has no items, but prediction implies items, it's mismatch?
            # Or if label is empty and pred is empty -> 1.0
            if not pred_items:
                items_score = 1.0
            else:
                items_score = 0.0
        else:
            # For each label item, find a match in prediction
            matched_count = 0
            # Create a mutable copy of prediction items to avoid double counting if needed
            # But simple existence check is usually enough
            
            for l_item in label_items:
                l_name = l_item.get("product_name", "")
                l_qty = str(l_item.get("quantity", ""))
                
                found = False
                for p_item in pred_items:
                    p_name = p_item.get("product_name", "")
                    p_qty = str(p_item.get("quantity", ""))
                    
                    # Quantity Match (Strict/Normalized) + Name Match (Loose)
                    if normalize_string(p_qty) == normalize_string(l_qty):
                        if is_loose_match(p_name, l_name):
                            found = True
                            break
                            
                if found:
                    matched_count += 1
            
            items_score = matched_count / len(label_items)
            
        matches += items_score
        
        final_score = matches / total_checks
        return round(final_score, 2)

    except Exception as e:
        print(f"Error calculating score: {e}")
        return 0.0
    except Exception as e:
        print(f"Error calculating score: {e}")
        return 0.0

        return 0.0

class ImprovedTextOrderAgent(TextOrderAgent):
    """
    Subclass of TextOrderAgent with Enhanced System Prompt and Debuggingcapabilities.
    Used for testing without modifying the core agent_engine.py.
    """
    def __init__(self, project_id: str = None, location: str = None, model_name: str = None, guide_path: str = None):
        # Call super init to setup basic state and tools
        super().__init__(project_id, location, model_name, guide_path)
        
        # Override the Model with Enhanced System Prompt
        # We need to reconstruct the system prompt text because it's local in super().__init__
        # But we can read the guide again or access self.guide_path
        
        store_guide_text = "Store information unavailable."
        address_guide_text = "Address validation guide unavailable."
        try:
            with open(self.guide_path, "r", encoding="utf-8") as f:
                store_guide_text = f.read()
            with open(f"{settings.GUIDES_DIR}/address_guide.txt", "r", encoding="utf-8") as f:
                address_guide_text = f.read()
        except Exception:
            pass
            
        from vertexai.generative_models import GenerativeModel
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Enhanced Instructions (Synced with agent_engine.py + Test Fixes)
        # 1. Base Prompt from agent_engine.py (Excluding OCR/Payment verification)
        enhanced_instructions = [
            f"CURRENT DATE/TIME: {current_time}",
            "You are an expert Order Processing Agent for the store defined in the STORE GUIDE.",
            f"STORE GUIDE:\n{store_guide_text}",
            f"ADDRESS GUIDE:\n{address_guide_text}",
            "CRITICAL: You ALREADY KNOW the store products from the guide. Do not check store info again.",
            
            "PROCESS FLOW:",
            "1. **ANALYZE FIRST MENTION**: Check the very first user message. If it contains Product/Quantity/Date, call `update_order_state` IMMEDIATELY.",
            "2. **QUESTION ONLY**: If user asks regarding product/price WITHOUT ordering info (e.g. 'How much?'), Answer the question AND explicitly ask: 'Would you like to place an order?'.",
            "3. **MIXED INTENT**: If the user asks a question AND provides order info (e.g. 'How much is apple? I want one'), FIRST answer the question, THEN record the order using `update_order_state`, and FINALLY ask for missing details.",
            "4. **GATHER**: Listen to the user. Save EVERY piece of info (Name, Phone, Address, Items, etc.) into your internal dictionary as soon as it is mentioned.",
            "5. **CHECK & CLARIFY**: If info is missing OR ambiguous (e.g. 'Apple' without size/type), ask for specific clarification. Do not guess.",
            "6. **VALIDATE ADDRESS**: Before confirming, strictly check the address against the ADDRESS GUIDE. If incomplete (e.g. only 'Seoul'), ask for details.",
            "7. **COMPLETENESS CHECK**: Do NOT ask 'Is this order correct?' or show the summary until you have ALL 5 required fields: Items, Name, Contact, Full Address, Delivery Date.",
            "8. **CONFIRM**: Once you have ALL info, naturally summarize the order and ask if it is correct. Do NOT instruct the user on exactly what words to say (e.g. avoid 'Say Yes to confirm').",
            "9. **FINALIZE**: ONLY after the user confirms, call `finalize_order`.",
            # "10. **PAYMENT GUIDE**: ..." (Removed for Test - No OCR)
            
            "RULES:",
            "- **LANGUAGE**: Always respond in polite Korean (존댓말), roughly matching the user's tone. NEVER switch to English unless the user speaks English.",
            "- **EXACT NAMES**: When recording items, use the EXACT product name from the STORE GUIDE. Do NOT use generic names or names not in the guide.",
            "- **PARENT PRODUCT MAPPING**: If the user orders a specific option (e.g. 'Small Set', '3kg'), find the PARENT Product Name in the guide (e.g. '[Apple] Busa') and record the Full Name (Parent + Option). Example: User says 'Small Set', Guide has '[LocknLock]... - Small Set', you record '[LocknLock]... (Small Set)'.",
            "- **QUANTITY VS UNIT**: Carefully distinguish between Item Count and Unit Size. Example: 'Apple 5kg' means Quantity=1, Unit='5kg'. 'Two 5kg Apples' means Quantity=2, Unit='5kg'. Do NOT put the size (5) in quantity.",
            "- **NO REPEATS**: Do NOT ask for information that the user has already provided. Check your state dictionary before asking.",
            
            # ENHANCED RULES FOR UNSTRUCTURED GUIDES (From agent_engine.py)
            "- **NUMBERED ITEMS**: If the guide has numbers (e.g. '1. Kim', '2. Bagel'), and user orders 'Number 1', YOU MUST record the full Product Name associated with that number.",
            "- **UNSTRUCTURED GUIDES**: If the guide lists items in sentences (e.g. 'Selling Kohlrabi for 900 won each'), identify 'Kohlrabi' as the Product and '900 won' as the price.",
            "- **CRITICAL**: If the user says 'Apple 5kg please' in the first turn, your FIRST action must be `update_order_state` with that item.",
            "- **ADDRESS VALIDATION**: Reject incomplete addresses like 'Gangnam', 'Seoul', 'My House'. Ask for specific details (City/Road/Number) in Korean.",
            "- **AMBIGUITY**: If user says 'Give me apples', ASK 'Which type? Home or Gift? 5kg or 10kg?'. Do not default.",
            "- NEVER call `finalize_order` without explicit user confirmation.",
            "- Keep the conversation going until you have all 5 required fields: Items, Name, Contact, Address, Delivery Date.",
            "- DATE FORMATTING: If the user says 'tomorrow' or 'next week', you MUST calculate the actual YYYY-MM-DD date based on 'CURRENT DATE/TIME' and store the specific date string.",
            # OCR Rules removed
            "- Always be polite and helpful.",
            
            # 2. TEST-SPECIFIC ENHANCEMENTS (To solve current failures)
            "CRITICAL RULES FOR STATE UPDATES:",
            "1. **INSTANT CAPTURE**: As soon as the user mentions ANY order detail (Product, Quantity, Name, etc.), you MUST call `update_order_state` IMMEDIATELY.",
            "2. **DO NOT JUST TALK**: Never simply repeat the order in text ('Order confirmed'). You MUST record it in the system using the tool.",
            "3. **NUMBERED ITEMS**: If user says '1번' or 'No. 1', look up the product name in the STORE GUIDE and record the FULL Product Name.",
            "4. **ACCUMULATE**: If the user adds items (e.g. 'Also add 1 item X'), call `update_order_state` with the NEW items. The system will merge them.",
            "5. **SPECIAL REQUESTS**: Capture comments like 'Leave at door' in `special_requests` field."
            "6. **UNIT REQUIRED**: Always include the 'unit' field in items (e.g. 'box', 'ea', 'kg'). If not specified, infer it from the guide or default to '개'.",
        ]
        
        self.model = GenerativeModel(
            self.model_name,
            system_instruction=enhanced_instructions,
            tools=[self.order_guide_tool]
        )
        
    def update_order_state(self, **kwargs):
        # Debug Override
        print(f"  [DEBUG] Tool Call detected: update_order_state({kwargs})")
        return super().update_order_state(**kwargs)

def run_tests():
    input_file = "test_data/validation_data_temp.CSV"

    if not os.path.exists(input_file):
        if os.path.exists("validation_data_temp.CSV"):
            input_file = "validation_data_temp.CSV"
        else:
            print(f"Error: {input_file} not found.")
            return

    print(f"Loading test data from {input_file}...")
    try:
        df = pd.read_csv(input_file, encoding='utf-8')
    except UnicodeDecodeError:
        print("UTF-8 decode failed, trying CP949...")
        df = pd.read_csv(input_file, encoding='cp949')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if 'no' in df.columns:
        df = df.dropna(subset=['no'])
    
    results = []
    print("Starting Test Loop...")
    
    os.makedirs("guides", exist_ok=True)
    os.makedirs("test_result", exist_ok=True)
    
    import glob
    existing_temps = glob.glob("guides/temp_guide_*.txt")
    for f in existing_temps:
        try: os.remove(f)
        except: pass
        
    for index, row in df.iterrows():
        temp_guide_path = None
        try:
            case_no = row.get('no', index)
            print(f"Processing Test Case #{case_no}...")
            
            # Rate Limit Protection
            time.sleep(20) 
            
            # 1. Setup Guide
            guide_content = row.get('guide', '')
            if pd.isna(guide_content): guide_content = ""
            
            # Fix unicode line endings if any
            guide_content = str(guide_content).replace('\r\n', '\n')
            
            temp_guide_path = f"guides/temp_guide_{index}.txt"
            with open(temp_guide_path, "w", encoding="utf-8") as f:
                f.write(guide_content)
                
            # 2. Initialize Agent
            agent = ImprovedTextOrderAgent(guide_path=temp_guide_path)
            
            # 3. Simulate
            raw_order = str(row['order'])
            turns = raw_order.split('\n')
            transcript = ""
            turn_count = 0
            
            for t in turns:
                t = t.strip()
                if not t: continue
                
                # Small delay between turns
                time.sleep(2)
                
                transcript += f"User: {t}\n"
                resp = agent.query(t)
                transcript += f"Agent: {resp}\n"
                turn_count += 1
                
            # 4. Evaluate
            final_state = agent.get_current_order()
            label = row.get('label', '{}')
            score = calculate_correctness(final_state, label)
            
            print(f"  -> Score: {score}")
            
            results.append({
                "no": case_no,
                "order": transcript.strip(),
                "turn": turn_count,
                "predict": final_state,
                "label": label,
                "correct_score": score
            })
            
        except Exception as e:
            print(f"Error on Case #{index}: {e}")
            results.append({
                "no": row.get('no', index),
                "order": "ERROR",
                "turn": 0,
                "predict": str(e),
                "label": row.get('label', ''),
                "correct_score": 0.0
            })
        finally:
            # Cleanup
            if temp_guide_path and os.path.exists(temp_guide_path):
                try:
                    os.remove(temp_guide_path)
                except Exception as e:
                    print(f"Warning: Failed to cleanup {temp_guide_path}: {e}")
            
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"test_result/test_result_{timestamp}.csv"
    
    res_df = pd.DataFrame(results)
    
    cols = ["no", "order", "turn", "predict", "label", "correct_score"]
    for c in cols:
        if c not in res_df.columns: res_df[c] = ""
    res_df = res_df[cols]
    
    res_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Test Completed. Results saved to {out_path}")

if __name__ == "__main__":
    run_tests()

