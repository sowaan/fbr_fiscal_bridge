import frappe
import requests
from frappe.utils import flt, now_datetime
from datetime import datetime
import json


def get_fiscal_component_api_url():
    """Return local API URL from FBR Fiscal Component Settings using get_single_value."""
    api_url = frappe.db.get_single_value("FBR Fiscal Component Settings", "fiscal_local_component_local_api")
    if not api_url:
        frappe.throw("Please configure Local API URL in FBR Fiscal Component Settings")
    return api_url


def create_fiscal_component_log(docname=None, status="Failed", payload=None, response=None, fiscal_invoice_number=""):
    """Insert a log in FBR Fiscal Component Logs"""
    try:
        log_doc = frappe.new_doc("FBR Fiscal Component Logs")

        # Use docname if provided, otherwise use FBR invoice number or a placeholder
        if docname:
            log_doc.sales_invoice = docname
        elif fiscal_invoice_number:
            log_doc.sales_invoice = f"Offline-{fiscal_invoice_number}"
        else:
            log_doc.sales_invoice = f"Offline-{now_datetime().strftime('%Y%m%d%H%M%S')}"

        log_doc.status = status
        log_doc.fiscal_invoice_number = fiscal_invoice_number
        log_doc.datetime = now_datetime()

        # Ensure payload is stored as JSON string
        if isinstance(payload, (dict, list)):
            log_doc.payload = json.dumps(payload, indent=4, default=str)
        else:
            log_doc.payload = str(payload or "")

        if isinstance(response, (dict, list)):
            log_doc.response = json.dumps(response, indent=4, default=str)
        else:
            log_doc.response = str(response or "")

        log_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            f"Failed to create log for {docname or fiscal_invoice_number}:\n{frappe.get_traceback()}",
            "FBR Fiscal Component Log Error"
        )

def send_invoice_to_fiscal_component(doc):
    """Send Sales Invoice to local Fiscal Component and log the attempt"""
    payload = {}
    res_data = {}
    status = "Failed"

    # Determine if doc is saved in ERP or just offline
    is_offline = False
    try:
        # doc comes as JSON string
        if isinstance(doc, str):
            doc = frappe.get_doc(json.loads(doc))

        # doc comes as dict (POS used offline)
        elif isinstance(doc, dict):
            doc = frappe.get_doc(doc)

        # doc is not saved in ERP yet
        if not getattr(doc, "name", None):
            is_offline = True

    except Exception:
        is_offline = True

    try:
        api_url = get_fiscal_component_api_url()
        pos_id = frappe.db.get_value("POS Profile", doc.pos_profile, "custom_pos_id")
        if not pos_id:
            frappe.throw(f"POSID not set on POS Profile: {doc.pos_profile}")

        tax_rate = round((flt(doc.get("total_taxes_and_charges")) / flt(doc.get("net_total"))) * 100, 0)
        total_qty = 0
        item_list = []

        for item in doc.items:
            rate_after_discount = flt(item.rate) * (1 - (flt(doc.get("additional_discount_percentage") or 0) / 100))
            amount_after_discount = flt(item.qty) * rate_after_discount
            tax_charged = amount_after_discount * tax_rate / 100
            pct_code = frappe.db.get_value("Item", item.item_code, "custom_pct_code") or ""
            buyer_ntn = frappe.db.get_value("Customer", doc.customer, "tax_id") or ""
            date_str = str(doc.posting_date)
            time_str = str(doc.posting_time).split(".")[0] if getattr(doc, "posting_time", None) else "00:00:00"

            item_list.append({
                "ItemCode": item.item_code,
                "ItemName": item.item_name,
                "Quantity": flt(item.qty),
                "PCTCode": pct_code,
                "TaxRate": tax_rate,
                "SaleValue": rate_after_discount,
                "TotalAmount": amount_after_discount,
                "TaxCharged": tax_charged,
                "Discount": "0.0",
                "FurtherTax": 0,
                "InvoiceType": 2,
                "RefUSIN": None
            })
            total_qty += flt(item.qty)

        payload = {
            "InvoiceNumber": "",
            "POSID": pos_id,
            "USIN": "SI-TEST-001",
            "DateTime": f"{date_str} {time_str}",
            "BuyerName": doc.customer,
            "BuyerNTN": buyer_ntn,
            "TotalBillAmount": flt(doc.grand_total),
            "TotalQuantity": total_qty,
            "TotalSaleValue": flt(doc.net_total),
            "TotalTaxCharged": flt(doc.total_taxes_and_charges),
            "Discount": "0",
            "FurtherTax": "0",
            "PaymentMode": 1,
            "RefUSIN": None,
            "InvoiceType": 1,
            "Items": item_list
        }

        try:
            response = requests.post(api_url, json=payload, timeout=(10, 60))
            res_data = response.json()
            status = "Success" if response.status_code == 200 else "Failed"

            # Save FBR invoice number in offline doc for future syncing
            if is_offline and res_data.get("InvoiceNumber"):
                doc.fbr_invoice_number = res_data.get("InvoiceNumber")

        except Exception as e:
            res_data = {"error": str(e)}
            status = "Failed"

    except Exception as e:
        res_data = {"error": str(e)}
        status = "Failed"

    # Pass doc.name if exists, else fallback to FBR invoice number or placeholder
    create_fiscal_component_log(
        docname=getattr(doc, "name", None),
        status=status,
        payload=payload,
        response=res_data,
        fiscal_invoice_number=res_data.get("InvoiceNumber", "")
    )

    return res_data


@frappe.whitelist()
def send_offline_invoice(invoice):
    is_active = frappe.db.get_single_value("FBR Fiscal Component Settings", "is_active")
    if not is_active:
        frappe.throw("FBR Fiscal Component is not active. Please enable it in settings to send invoices.")

    if isinstance(invoice, str):
        invoice = json.loads(invoice)
    
    res = send_invoice_to_fiscal_component(invoice)
    
    # Return only the invoice number (or the full response if you prefer)
    return {"InvoiceNumber": res.get("InvoiceNumber")}


@frappe.whitelist()
def ping():
    return "ok"