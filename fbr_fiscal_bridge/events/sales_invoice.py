#!/home/vatsky/frappe-bench/env/bin/python
#####/Users/saqibrupani/Documents/pythoncode/SkylinesVAT/frappe-bench/env/bin/python
from six import BytesIO

import frappe
from frappe import _
import json
import requests
from frappe.utils import flt
from pyqrcode import create as qrcreate



@frappe.whitelist()
def send_pos_invoice_fbr(doc, method=None, is_admin=False):
    try:
        # If doc received as a JSON string
        if isinstance(doc, str):
            doc = json.loads(doc)

        # These should NEVER go to FBR
        if doc.get("return_against") and not doc.get("is_pos"):
            frappe.log_error(f"Skipped FBR API call for auto credit note: {doc.get('name')}",
                             "FBR Auto Credit Note Skipped")
            return

        # FBR user check
        if frappe.db.get_value("POS Profile User",
                               {'parent': doc.get('pos_profile'),
                                'user': frappe.session.user},
                               "fbr_user") == 1 or is_admin:

            # Get POS settings
            pos_id, ntn_number, pos_token = frappe.db.get_value(
                'POS Profile',
                doc.get('pos_profile'),
                ['pos_id', 'ntn_no', 'pos_token']
            )

            if pos_id and pos_token:

                item_list = []
                total_qty = 0
                is_return = doc.get("is_return")

                # Tax rate
                if doc.get("net_total"):
                    tax_rate = round(
                        (doc.get("total_taxes_and_charges") / doc.get("net_total")) * 100,
                        2
                    )
                else:
                    tax_rate = 0

                for item in doc.get("items"):

                    sign = -1 if is_return else 1

                    qty = sign * item.get("qty")
                    rate = item.get("rate")
                    sale_value = sign * rate * item.get("qty")
                    total_amount = sale_value * (1 + tax_rate / 100)
                    tax_charged = (sale_value * tax_rate) / 100

                    # Add item row
                    item_list.append({
                        "ItemCode": item.get('item_code'),
                        "ItemName": item.get('item_name'),
                        "Quantity": qty,
                        "PCTCode": "11001010",
                        "TaxRate": tax_rate,
                        "SaleValue": sale_value,
                        "TotalAmount": total_amount,
                        "TaxCharged": tax_charged,
                        "Discount": "0.0",
                        "FurtherTax": 0,
                        "InvoiceType": 2 if not is_return else 3,
                        "RefUSIN": None
                    })

                    total_qty += qty

                sign = -1 if is_return else 1

                data = {
                    "InvoiceNumber": "",
                    "POSID": pos_id,
                    "USIN": doc.get("name"),
                    "DateTime": str(doc.get('posting_date')),
                    "BuyerNTN": None,
                    "BuyerCNIC": None,
                    "BuyerName": None,
                    "BuyerPhoneNumber": None,
                    "TotalBillAmount": sign * doc.get('grand_total'),
                    "TotalQuantity": total_qty,
                    "TotalSaleValue": sign * doc.get('net_total'),
                    "TotalTaxCharged": sign * doc.get('total_taxes_and_charges'),
                    "Discount": "0",
                    "FurtherTax": "0",
                    "PaymentMode": 1,
                    "RefUSIN": None,
                    "InvoiceType": 2 if not is_return else 3,
                    "Items": item_list
                }

                headers = {
                    "Authorization": "Bearer " + pos_token
                }

                url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"

                response = requests.post(url=url, json=data, headers=headers, timeout=10)
                res_data = response.json()
                invoice_number = res_data.get("InvoiceNumber")

                frappe.log_error(
                    f"Payload: {data}\nStatus: {response.status_code}\nResponse: {json.dumps(res_data)}",
                    "FBR eInvoice Msg"
                )

                # Save the invoice number
                set_invoice_number('Sales Invoice', doc.get('name'), invoice_number)

                if invoice_number:
                    return {"invoice_number": invoice_number, "name": doc.get("name")}

        else:
            frappe.log_error("User must be FBR User to call FBR API.", "FBR User Error")

    except Exception as e:
        frappe.log_error(f"FBR eInvoicing Error:\n{frappe.get_traceback()}",
                         "FBR eInvoicing Error")




@frappe.whitelist()
def set_invoice_number(doctype, name, inv):
	frappe.db.set_value(doctype, name, "fbr_invoice_no", inv)
	generate_fbr_barcode(inv, name)
	frappe.db.commit()

@frappe.whitelist()
def generate_fbr_barcode(code=None, docname=None):
	from pathlib import Path
	import os
	import qrcode

	try:
		name_tobe = docname + ".png"
		# Get the current working directory
		cwd = os.getcwd()
		print(cwd)
		f = open(cwd+"/currentsite.txt", "r")
		currentsitename = f.readline()
		check_file = Path(cwd + "/" + currentsitename + "/public/files/qrcodes/" + name_tobe)
		if not check_file.is_file():
			img = qrcode.make(code)
			img.save(cwd + "/" + currentsitename + '/public/files/qrcodes/' + name_tobe)
	except Exception as ex:
		print(ex)

@frappe.whitelist()
def update_fbr_invoice(doctype=None, docname=None):
	if doctype and docname:
		doc = frappe.get_doc(doctype, docname)
		resp = send_pos_invoice_fbr(doc)
		invoice_number = resp.get("invoice_number")
		if invoice_number:
			set_invoice_number(doctype, docname, invoice_number)
		return invoice_number
	return 'No invoice sent to FBR, check error logs'

def update_fbr_invoice_in_background(doctype=None, docname=None):
	if doctype and docname:
		doc = frappe.get_doc(doctype, docname)
		resp = send_pos_invoice_fbr(doc, is_admin=True)
		invoice_number = resp.get("invoice_number")
		if invoice_number:
			set_invoice_number(doctype, docname, invoice_number)
		return invoice_number
	return 'No invoice sent to FBR, check error logs'

# run a queue job for reposting to fbr for failed ones
def repost_invoices_to_fbr():
	invoices = frappe.db.sql("""
		SELECT si.name
		FROM `tabSales Invoice` si
		JOIN `tabPOS Profile` pp ON si.pos_profile = pp.name
		WHERE si.docstatus = 1
			AND (si.fbr_invoice_no IS NULL OR si.fbr_invoice_no = '' OR si.fbr_invoice_no = 'Not Available')
			AND si.pos_profile IS NOT NULL AND si.pos_profile != ''
			AND pp.pos_id IS NOT NULL AND pp.pos_id != ''
			AND pp.ntn_no IS NOT NULL AND pp.ntn_no != ''
			AND pp.pos_token IS NOT NULL AND pp.pos_token != ''
			AND pp.fbr_integration_date IS NOT NULL AND si.posting_date >= pp.fbr_integration_date
		LIMIT 20
	""", as_dict=True)

	invoices_to_fbr = []
	for inv in invoices:
		frappe.enqueue(update_fbr_invoice_in_background, queue='short', doctype="Sales Invoice", docname=inv.name)
		# frappe.enqueue(update_fbr_invoice_in_background, queue='long', doctype="Sales Invoice", docname=inv.name)
		invoices_to_fbr.append(inv.name)

	invoices_str = ", ".join(invoices_to_fbr)
	if invoices_to_fbr:
		info_msg = f"<h2>Queued background job for reposting to FBR:</h2>\n{invoices_str}"
		frappe.log_error(info_msg, "FBR Reposting Log")
