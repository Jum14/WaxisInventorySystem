import os
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Gemini prompt template for PO email
PO_EMAIL_PROMPT = """You are a professional procurement assistant for Waxi's (SND Foods International Inc.).
Generate a concise, formal Purchase Order email to a supplier.

Context:
- Supplier: {supplier_name} ({supplier_email}) - Contact: {contact_person}
- Ingredient: {ingredient_name} ({category}) - Stock: {current_stock} {unit} (min {min_stock}, max {max_stock})
- Requested Quantity: {qty} {unit}
- Priority: {priority}
- Reason: {reason}
- Requested by: {requested_by}

Requirements:
- Subject line starting with "Purchase Order Request - "
- Polite greeting, state quantity/unit, delivery expectation (lead time {lead_time} days)
- Mention Waxi's standard delivery address placeholder and contact for confirmation
- Professional closing with Waxi's Procurement Team signature
- Keep under 180 words, no markdown, plain text email body.

Return ONLY the email body with subject as first line 'Subject: ...'."""


def _get_genai():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None, None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        return genai, model
    except Exception as e:
        logger.warning("Gemini init failed: %s", e)
        return None, None


def generate_po_email(procurement_request):
    """
    Generate PO email body via Gemini. Falls back to deterministic template if no API key.
    Returns (subject, body)
    """
    ing = procurement_request.ingredient
    supplier = procurement_request.supplier
    # Fallback to legacy text if no FK
    supplier_name = getattr(supplier, "company_name", None) or getattr(ing, "supplier", "") or "Supplier"
    supplier_email = getattr(supplier, "email", "") or "supplier@example.com"
    contact_person = getattr(supplier, "contact_person", "") or "Procurement Contact"
    lead_time = getattr(supplier, "lead_time_days", 3)

    qty = procurement_request.requested_quantity
    prompt = PO_EMAIL_PROMPT.format(
        supplier_name=supplier_name,
        supplier_email=supplier_email,
        contact_person=contact_person,
        ingredient_name=ing.name,
        category=ing.get_category_display(),
        current_stock=ing.quantity,
        unit=ing.unit,
        min_stock=ing.minimum_stock,
        max_stock=ing.maximum_stock,
        qty=qty,
        priority=procurement_request.get_priority_display(),
        reason=procurement_request.reason or "Restocking - low inventory",
        requested_by=getattr(procurement_request.requested_by, "username", "Waxi's System"),
        lead_time=lead_time,
    )

    _, model = _get_genai()
    if model is None:
        # Deterministic fallback - no API key
        subject = f"Purchase Order Request - {ing.name} ({qty} {ing.unit})"
        body = (
            f"Dear {contact_person} at {supplier_name},\n\n"
            f"We would like to place a purchase order for {qty} {ing.unit} of {ing.name} "
            f"({ing.get_category_display()}). Current stock is {ing.quantity} {ing.unit} (minimum {ing.minimum_stock}).\n"
            f"Priority: {procurement_request.get_priority_display()}. Reason: {procurement_request.reason or 'Restocking'}.\n"
            f"Please confirm availability and expected delivery within {lead_time} days to Waxi's main kitchen.\n\n"
            f"Thank you for your prompt assistance.\n\n"
            f"Best regards,\nWaxi's Procurement Team\nSND Foods International Inc.\n"
            f"Contact: procurement@waxis.local"
        )
        return subject, body

    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty Gemini response")
        lines = text.splitlines()
        subject = lines[0].replace("Subject:", "").strip() if lines[0].lower().startswith("subject:") else f"Purchase Order Request - {ing.name}"
        body = "\n".join(lines[1:]).strip() if lines[0].lower().startswith("subject:") else text
        if not body:
            body = text
        return subject, body
    except Exception as e:
        logger.error("Gemini generate failed: %s", e)
        subject = f"Purchase Order Request - {ing.name} ({qty} {ing.unit})"
        body = f"Dear {contact_person},\n\nRequesting {qty} {ing.unit} of {ing.name}. Please confirm delivery within {lead_time} days.\n\nWaxi's Procurement Team"
        return subject, body


def generate_executive_summary(context_dict):
    """
    AI Executive Summary for dashboard.
    context_dict: {total, low, critical, pending, distribution, recent_transactions}
    """
    _, model = _get_genai()
    prompt = (
        "You are Waxi's Inventory AI analyst. Given this operational snapshot, write a 3-4 sentence executive summary "
        "with health assessment and 1 actionable recommendation. Be concise, data-driven, no markdown.\n\n"
        f"Snapshot: {context_dict}\n\nSummary:"
    )
    if model is None:
        # Fallback heuristic
        total = context_dict.get("total", 0)
        low = context_dict.get("low", 0)
        critical = context_dict.get("critical", 0)
        pending = context_dict.get("pending", 0)
        if critical > 0:
            return f"Operational attention needed: {critical} ingredient(s) critical/out, {low} low. {pending} procurement(s) pending. Prioritize restocking critical items and approving pending orders."
        if low > 0:
            return f"Inventory stable with {low} low-stock items out of {total}. {pending} procurement pending. Review low items for reorder."
        return f"Inventory healthy: {total} ingredients tracked, no critical shortages, {pending} pending procurements. Maintain current monitoring."

    try:
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()[:600]
    except Exception as e:
        logger.error("Executive summary Gemini failed: %s", e)
        return "Inventory overview generated. Review low and critical items for action."
