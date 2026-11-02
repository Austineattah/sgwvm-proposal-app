import re

def analyze_proposal_with_ai(extracted_text, filename=""):
    """
    Deterministic Rule-Based Proposal Analyzer.
    Parses key structural metadata (Company RC, Budget, Timeline, Contact details)
    without sending data to external LLM APIs.
    """
    if not extracted_text or not extracted_text.strip():
        return {
            "status": "success",
            "company_name": "Unknown Vendor",
            "company_rc": "N/A",
            "budget": "Not Specified",
            "timeline": "Not Specified",
            "feasibility_score": "Low",
            "summary": "Document contained no extractable text content."
        }

    # Normalize whitespace for cleaner regex matching
    clean_text = " ".join(extracted_text.split())

    # 1. CAC RC Number Extraction (5 to 8 digits)
    rc_match = re.search(r'(?:RC|RC\s*NO|RC\s*Number|\bCAC\b)[:\s]*([0-9]{5,8})', clean_text, re.IGNORECASE)
    company_rc = rc_match.group(1) if rc_match else "N/A"

    # 2. Budget / Financial Extraction (Matches ₦, NGN, $, or 'Budget:' numbers)
    budget_match = re.search(r'(?:₦|NGN|\$|Budget[:\s]+|Amount[:\s]+)([\d,]+(?:\.\d{2})?)', clean_text, re.IGNORECASE)
    budget = budget_match.group(0) if budget_match else "Under Review"

    # 3. Project Timeline Extraction
    timeline_match = re.search(r'(\d+\s*(?:months?|weeks?|days?|years?))', clean_text, re.IGNORECASE)
    timeline = timeline_match.group(1) if timeline_match else "Standard Schedule"

    # 4. Feasibility Score (Based on completeness of critical project parameters)
    score_points = 0
    if company_rc != "N/A": score_points += 1
    if budget != "Under Review": score_points += 1
    if timeline != "Standard Schedule": score_points += 1
    
    feasibility_score = "High" if score_points >= 2 else ("Medium" if score_points == 1 else "Low")

    # 5. Executive Brief Summary Preview (First 350 clean characters)
    summary_text = clean_text[:350] + "..." if len(clean_text) > 350 else clean_text

    return {
        "status": "success",
        "company_rc": company_rc,
        "budget": budget,
        "timeline": timeline,
        "feasibility_score": feasibility_score,
        "summary": summary_text
    }
