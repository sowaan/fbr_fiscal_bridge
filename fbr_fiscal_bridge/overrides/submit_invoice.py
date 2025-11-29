import json
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc

# Import original helper functions from POSAwesome
from posawesome.posawesome.api.invoices import (
    update_invoice,
    redeeming_customer_credit,
    _apply_item_name_overrides,
    _auto_set_return_batches,
    ensure_child_doctype,
    set_batch_nos_for_bundels,
    _validate_stock_on_invoice,
)

from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from frappe.utils.background_jobs import enqueue

# Import your custom FBR logic
from fbr_fiscal_bridge.events.sales_invoice import send_pos_invoice_fbr


@frappe.whitelist()
def submit_invoice(invoice, data):
    """Custom override version of POSAwesome submit_invoice with:
       ✔ FBR API logic BEFORE submission (to ensure FBR number before submitting)
       ✔ Original POSAwesome functionality
       ✔ Full validation & helper functions preserved
       ✔ Prevents submission if FBR fails, avoiding duplicates and compliance issues
    """

    # Convert raw JSON into Python dictionaries
    data = json.loads(data)
    invoice = json.loads(invoice)

    pos_profile = invoice.get("pos_profile")
    doctype = "Sales Invoice"

    # Determine actual doctype (Sales Invoice or POS Invoice)
    if pos_profile and frappe.db.get_value(
        "POS Profile", pos_profile, "create_pos_invoice_instead_of_sales_invoice"
    ):
        doctype = "POS Invoice"

    invoice_name = invoice.get("name")

    # Create or update invoice
    if not invoice_name or not frappe.db.exists(doctype, invoice_name):
        created = update_invoice(json.dumps(invoice))
        invoice_name = created.get("name")
        invoice_doc = frappe.get_doc(doctype, invoice_name)
    else:
        invoice_doc = frappe.get_doc(doctype, invoice_name)
        invoice_doc.update(invoice)

    # Apply item name overrides
    _apply_item_name_overrides(invoice_doc)

    # If delivery date exists, do not update stock
    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0

    # Determine cash account
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]

    if mop_cash_list:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {"account": frappe.db.get_value("Company", invoice_doc.company, "default_cash_account")}

    # Update Remarks - Include item level details & grand total
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    items.append(f"\nGrand Total: {invoice_doc.grand_total}")
    invoice_doc.remarks = "\n".join(items)

    # Create advance payment if credit change exists
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc({
            "doctype": "Payment Entry",
            "mode_of_payment": "Cash",
            "paid_to": cash_account["account"],
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": invoice_doc.customer,
            "paid_amount": invoice_doc.credit_change,
            "received_amount": invoice_doc.credit_change,
            "company": invoice_doc.company,
        })
        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # Customer credit redemption logic
    total_cash = 0
    is_payment_entry = 0

    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                advance_row = invoice_doc.append("advances", {})
                advance_row.update({
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                })

                child_dt = "POS Invoice Advance" if invoice_doc.doctype == "POS Invoice" else "Sales Invoice Advance"
                ensure_child_doctype(invoice_doc, "advances", child_dt)
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    # Stock validation
    _auto_set_return_batches(invoice_doc)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)
    _validate_stock_on_invoice(invoice_doc)

    # Save before FBR and submit (as draft)
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    invoice_doc.save()  # Save as draft (docstatus=0)

    # ------------------------------------------------------------------
    # ✔ YOUR FBR LOGIC — RUN BEFORE SUBMISSION
    # ------------------------------------------------------------------
    fbr_success = False
    try:
        fbr_response = send_pos_invoice_fbr(invoice_doc)
        if fbr_response and fbr_response.get("invoice_number"):
            frappe.db.set_value(
                invoice_doc.doctype,
                invoice_doc.name,
                "fbr_invoice_no",
                fbr_response.get("invoice_number"),
            )
            frappe.db.commit()
            fbr_success = True
        else:
            frappe.log_error("FBR API did not return a valid invoice_number", "FBR Submit Error")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "FBR Submit Error")
        # Optionally, you can raise an exception here to stop further processing
        # raise frappe.ValidationError("FBR submission failed. Invoice not submitted.")

    # Only proceed with submission if FBR succeeded
    if not fbr_success:
        # Return without submitting — invoice remains as draft
        return {"name": invoice_doc.name, "status": invoice_doc.docstatus, "fbr_error": True}

    # Set due date (only if FBR succeeded)
    if data.get("due_date"):
        frappe.db.set_value(doctype, invoice_doc.name, "due_date", data.get("due_date"), update_modified=False)

    # Background job submission (only if FBR succeeded)
    allow_bg = frappe.db.get_value("POS Profile", invoice_doc.pos_profile, "posa_allow_submissions_in_background_job")

    if allow_bg and fbr_success:
        invoices_list = frappe.get_all(
            doctype,
            filters={"posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift, "docstatus": 0, "posa_is_printed": 1},
        )

        for inv in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": inv.name,
                    "doctype": doctype,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        invoice_doc.submit()
        redeeming_customer_credit(invoice_doc, data, is_payment_entry, total_cash, cash_account, payments)

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}


def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    doctype = kwargs.get("doctype") or "Sales Invoice"
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc(doctype, invoice)

    # Update remarks with items details for background job
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    # Add the grand total at the end of remarks
    grand_total = f"\nGrand Total: {invoice_doc.grand_total}"
    items.append(grand_total)

    invoice_doc.remarks = "\n".join(items)
    invoice_doc.save()

    invoice_doc.submit()
    redeeming_customer_credit(invoice_doc, data, is_payment_entry, total_cash, cash_account, payments)
