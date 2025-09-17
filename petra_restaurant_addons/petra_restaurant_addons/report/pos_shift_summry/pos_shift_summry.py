# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def format_currency(amount):
	"""Format currency for display"""
	return f"LYD {flt(amount):.2f}"


def execute(filters=None):
	columns, cost_centers = get_columns(filters)
	data = get_data(filters, cost_centers)
	return columns, data


def get_columns(filters=None):
	# Get all unique cost centers from the data
	cost_centers = get_cost_centers(filters)
	
	# Base columns - basic information
	columns = [
		{
			"fieldname": "pos_opening_shift",
			"label": _("POS Opening Shift"),
			"fieldtype": "Link",
			"options": "POS Opening Shift",
			"width": 300
		},
		{
			"fieldname": "pos_profile",
			"label": _("POS Profile"),
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 150
		},
		{
			"fieldname": "pos_closing_shift",
			"label": _("POS Closing Shift"),
			"fieldtype": "Link",
			"options": "POS Closing Shift",
			"width": 250
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 200
		},
		{
			"fieldname": "cashier",
			"label": _("Cashier"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		}
	]
	
	# Add dynamic cost center columns in the middle
	for cost_center in cost_centers:
		columns.append({
			"fieldname": f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}",
			"label": cost_center,
			"fieldtype": "Currency",
			"width": 120
		})
	
	# Add totals columns at the end
	totals_columns = [
		{
			"fieldname": "total_shifts",
			"label": _("Total Shifts"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_cash_sales",
			"label": _("Total Cash Sales"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_card_sales",
			"label": _("Total Card Sales"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_grand_total",
			"label": _("Grand Total"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_net_total",
			"label": _("Net Total"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_quantity",
			"label": _("Total Quantity"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		
		{
			"fieldname": "average_per_shift",
			"label": _("Average per Shift"),
			"fieldtype": "Currency",
			"width": 120
		}
	]
	
	# Combine all columns
	columns.extend(totals_columns)
	
	return columns, cost_centers


def get_cost_centers(filters):
	"""Get all unique cost centers from the data"""
	conditions, params = get_conditions(filters)
	
	cost_centers_query = """
		SELECT DISTINCT pp.cost_center
		FROM `tabPOS Closing Shift` cs
		INNER JOIN `tabPOS Opening Shift` os ON cs.pos_opening_shift = os.name
		LEFT JOIN `tabPOS Profile` pp ON cs.pos_profile = pp.name
		WHERE cs.docstatus = 1
		AND pp.cost_center IS NOT NULL
		AND {conditions}
		ORDER BY pp.cost_center
	""".format(conditions=conditions)
	
	result = frappe.db.sql(cost_centers_query, params, as_dict=True)
	return [row.cost_center for row in result if row.cost_center]


def get_data(filters, cost_centers):
	# Build the query conditions and parameters
	conditions, params = get_conditions(filters)
	
	# Get the base query for closing shifts
	base_query = """
		SELECT 
			cs.name as pos_closing_shift,
			cs.pos_profile,
			cs.pos_opening_shift,
			cs.grand_total,
			cs.net_total,
			cs.total_quantity,
			
			cs.posting_date,
			os.period_start_date,
			os.period_end_date,
			os.user as cashier,
			cs.company,
			pp.cost_center
		FROM `tabPOS Closing Shift` cs
		INNER JOIN `tabPOS Opening Shift` os ON cs.pos_opening_shift = os.name
		LEFT JOIN `tabPOS Profile` pp ON cs.pos_profile = pp.name
		WHERE cs.docstatus = 1
		AND {conditions}
		ORDER BY cs.pos_profile, cs.posting_date
	""".format(conditions=conditions)
	
	closing_shifts = frappe.db.sql(base_query, params, as_dict=True)
	
	# Group data by POS Opening Shift
	shift_data = {}
	for shift in closing_shifts:
		opening_shift = shift.pos_opening_shift
		
		if opening_shift not in shift_data:
			shift_data[opening_shift] = {
				'pos_opening_shift': opening_shift,
				'pos_profile': shift.pos_profile,
				'pos_closing_shift': shift.pos_closing_shift,
				'total_shifts': 1,  # Each opening shift represents one shift
				'total_cash_sales': 0,
				'total_card_sales': 0,
				'total_grand_total': flt(shift.grand_total),
				'total_net_total': flt(shift.net_total),
				'total_quantity': flt(shift.total_quantity),
				'return_sales_count': flt(shift.return_sales_count),
				'average_per_shift': flt(shift.grand_total),  # Same as grand total for individual shift
				'posting_date': shift.posting_date,
				'cashier': shift.cashier,
				'sales_invoices': []  # Add sales invoices list
			}
			
			# Get payment breakdown for this shift
			payment_data = get_payment_breakdown(shift.pos_opening_shift)
			shift_data[opening_shift]['total_cash_sales'] = payment_data.get('cash', 0)
			shift_data[opening_shift]['total_card_sales'] = payment_data.get('card', 0)
			
			# Get sales invoices for this shift
			shift_data[opening_shift]['sales_invoices'] = get_sales_invoices_for_shift(shift.pos_opening_shift)
			
			# Initialize cost center columns
			for cost_center in cost_centers:
				field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
				shift_data[opening_shift][field_name] = 0
			
			# Set the value for this shift's cost center
			if shift.cost_center:
				field_name = f"cost_center_{shift.cost_center.replace(' ', '_').replace('-', '_')}"
				shift_data[opening_shift][field_name] = flt(shift.grand_total)
	
	# Convert to list and create expandable rows
	data = []
	for shift_key, shift_info in shift_data.items():
		# Add main shift row
		shift_row = shift_info.copy()
		shift_row['_is_group'] = 1  # Mark as group row
		shift_row['_indent'] = 0
		data.append(shift_row)
		
		# Add invoice rows as child rows
		for invoice in shift_info['sales_invoices']:
			invoice_row = {
				'pos_opening_shift': f"  └─ {invoice['invoice_name']}",
				'pos_profile': '',
				'pos_closing_shift': '',
				'posting_date': invoice['posting_date'],
				'cashier': f"{invoice['customer'] or 'Walk-in Customer'} | {invoice['posting_time'] or ''}",
				'total_grand_total': flt(invoice['grand_total']),
				'total_net_total': flt(invoice['net_total']),
				'total_quantity': flt(invoice['total_qty']),
				'_is_group': 0,  # Mark as child row
				'_indent': 1,
				'invoice_items': invoice['items'],
				'invoice_payments': invoice['payments']
			}
			
			# Initialize cost center columns for invoice row
			for cost_center in cost_centers:
				field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
				invoice_row[field_name] = 0
			
			# Set other columns to empty or zero
			invoice_row.update({
				'total_shifts': 0,
				'total_cash_sales': 0,
				'total_card_sales': 0,
				'return_sales_count': 0,
				'average_per_shift': 0
			})
			
			data.append(invoice_row)
			
			# Add item rows for this invoice
			for item in invoice['items']:
				item_row = {
					'pos_opening_shift': f"    • {item['item_code']} - {item['item_name']}",
					'pos_profile': '',
					'pos_closing_shift': '',
					'posting_date': '',
					'cashier': f"Qty: {item['qty']} | Rate: {format_currency(item['rate'])} | UOM: {item['uom'] or 'Nos'}",
					'total_grand_total': flt(item['amount']),
					'total_net_total': flt(item['amount']),
					'total_quantity': flt(item['qty']),
					'_is_group': 0,  # Mark as child row
					'_indent': 2,
					'item_code': item['item_code'],
					'item_name': item['item_name'],
					'item_qty': item['qty'],
					'item_rate': item['rate'],
					'item_amount': item['amount'],
					'item_uom': item['uom']
				}
				
				# Initialize cost center columns for item row
				for cost_center in cost_centers:
					field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
					item_row[field_name] = 0
				
				# Set other columns to empty or zero
				item_row.update({
					'total_shifts': 0,
					'total_cash_sales': 0,
					'total_card_sales': 0,
					'return_sales_count': 0,
					'average_per_shift': 0
				})
				
				data.append(item_row)
	
	# Add grand total row
	if data:
		grand_totals = {
			'pos_opening_shift': _("GRAND TOTAL"),
			'pos_profile': '',
			'pos_closing_shift': '',
			'total_shifts': sum(row['total_shifts'] for row in data if row.get('_is_group') == 1),
			'total_cash_sales': sum(row['total_cash_sales'] for row in data if row.get('_is_group') == 1),
			'total_card_sales': sum(row['total_card_sales'] for row in data if row.get('_is_group') == 1),
			'total_grand_total': sum(row['total_grand_total'] for row in data if row.get('_is_group') == 1),
			'total_net_total': sum(row['total_net_total'] for row in data if row.get('_is_group') == 1),
			'total_quantity': sum(row['total_quantity'] for row in data if row.get('_is_group') == 1),
			'return_sales_count': sum(row['return_sales_count'] for row in data if row.get('_is_group') == 1),
			'average_per_shift': 0,  # Will be calculated separately
			'posting_date': '',
			'cashier': '',
			'_is_group': 1,
			'_indent': 0
		}
		
		# Add cost center totals
		for cost_center in cost_centers:
			field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
			grand_totals[field_name] = sum(row.get(field_name, 0) for row in data if row.get('_is_group') == 1)
		
		# Calculate overall average per shift
		if grand_totals['total_shifts'] > 0:
			grand_totals['average_per_shift'] = flt(grand_totals['total_grand_total']) / grand_totals['total_shifts']
		data.append(grand_totals)
	
	return data


def get_sales_invoices_for_shift(pos_opening_shift):
	"""Get sales invoices with items for a specific shift"""
	# Check if POS Profile uses POS Invoice or Sales Invoice
	pos_profile = frappe.db.get_value(
		"POS Opening Shift", pos_opening_shift, "pos_profile"
	)
	
	use_pos_invoice = frappe.db.get_value(
		"POS Profile", pos_profile, "create_pos_invoice_instead_of_sales_invoice"
	)
	
	doctype = "POS Invoice" if use_pos_invoice else "Sales Invoice"
	
	# Get invoices for this shift
	invoices = frappe.get_all(
		doctype,
		filters={
			"posa_pos_opening_shift": pos_opening_shift,
			"docstatus": 1
		},
		fields=[
			"name", "grand_total", "net_total", "total_qty", 
			"posting_date", "customer", "posting_time"
		],
		order_by="posting_date, posting_time"
	)
	
	invoice_details = []
	for invoice in invoices:
		# Get invoice items
		items = frappe.get_all(
			f"{doctype} Item",
			filters={"parent": invoice.name},
			fields=[
				"item_code", "item_name", "qty", "rate", "amount",
				"description", "uom"
			],
			order_by="idx"
		)
		
		# Get payments for this invoice
		payments = frappe.get_all(
			f"{doctype} Payment",
			filters={"parent": invoice.name},
			fields=["mode_of_payment", "amount"],
			order_by="idx"
		)
		
		invoice_details.append({
			"invoice_name": invoice.name,
			"customer": invoice.customer,
			"posting_date": invoice.posting_date,
			"posting_time": invoice.posting_time,
			"grand_total": flt(invoice.grand_total),
			"net_total": flt(invoice.net_total),
			"total_qty": flt(invoice.total_qty),
			"items": items,
			"payments": payments
		})
	
	return invoice_details


def get_payment_breakdown(pos_opening_shift):
	"""Get cash and card sales breakdown from payment reconciliation"""
	payment_data = frappe.db.sql("""
		SELECT 
			mode_of_payment,
			SUM(closing_amount) as amount
		FROM `tabPOS Closing Shift Detail`
		WHERE parenttype = 'POS Closing Shift'
		AND parent IN (
			SELECT name FROM `tabPOS Closing Shift` 
			WHERE pos_opening_shift = %s AND docstatus = 1
		)
		GROUP BY mode_of_payment
	""", (pos_opening_shift,), as_dict=True)
	
	cash_total = 0
	card_total = 0
	
	for payment in payment_data:
		# Check if this is a cash mode of payment
		try:
			mop_doc = frappe.get_doc("Mode of Payment", payment.mode_of_payment)
			if mop_doc.type == "Cash":
				cash_total += flt(payment.amount)
			else:
				card_total += flt(payment.amount)
		except frappe.DoesNotExistError:
			# If mode of payment doesn't exist, treat as non-cash
			card_total += flt(payment.amount)
	
	return {
		'cash': cash_total,
		'card': card_total
	}


def get_conditions(filters):
	conditions = []
	params = {}
	
	# Date range filter
	if filters.get("from_date"):
		conditions.append("cs.posting_date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		conditions.append("cs.posting_date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")
	
	# POS Opening Shift filter
	if filters.get("pos_opening_shifts"):
		opening_shifts = filters.get("pos_opening_shifts")
		if isinstance(opening_shifts, str):
			opening_shifts = [opening_shifts]
		# Use tuple for IN clause
		conditions.append("os.name IN %(pos_opening_shifts)s")
		params["pos_opening_shifts"] = tuple(opening_shifts)
	
	# POS Profile filter
	if filters.get("pos_profile"):
		conditions.append("os.pos_profile = %(pos_profile)s")
		params["pos_profile"] = filters.get("pos_profile")
	
	# Company filter
	if filters.get("company"):
		conditions.append("cs.company = %(company)s")
		params["company"] = filters.get("company")
	
	
	# Default condition if no filters are applied
	if not conditions:
		conditions.append("1=1")
	
	return " AND ".join(conditions), params
