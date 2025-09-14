# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"fieldname": "pos_opening_shift",
			"label": _("POS Opening Shift"),
			"fieldtype": "Link",
			"options": "POS Opening Shift",
			"width": 180
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
			"width": 180
		},
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
			"fieldname": "return_sales_total",
			"label": _("Return Sales Total"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "return_sales_count",
			"label": _("Return Sales Count"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "average_per_shift",
			"label": _("Average per Shift"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "cashier",
			"label": _("Cashier"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		}
	]
	return columns


def get_data(filters):
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
			cs.return_sales_total,
			cs.return_sales_count,
			cs.posting_date,
			os.period_start_date,
			os.period_end_date,
			os.user as cashier,
			cs.company
		FROM `tabPOS Closing Shift` cs
		INNER JOIN `tabPOS Opening Shift` os ON cs.pos_opening_shift = os.name
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
				'return_sales_total': flt(shift.return_sales_total),
				'return_sales_count': flt(shift.return_sales_count),
				'average_per_shift': flt(shift.grand_total),  # Same as grand total for individual shift
				'posting_date': shift.posting_date,
				'cashier': shift.cashier
			}
			
			# Get payment breakdown for this shift
			payment_data = get_payment_breakdown(shift.pos_opening_shift)
			shift_data[opening_shift]['total_cash_sales'] = payment_data.get('cash', 0)
			shift_data[opening_shift]['total_card_sales'] = payment_data.get('card', 0)
	
	# Convert to list
	data = list(shift_data.values())
	
	# Add grand total row
	if data:
		grand_totals = {
			'pos_opening_shift': _("GRAND TOTAL"),
			'pos_profile': '',
			'pos_closing_shift': '',
			'total_shifts': sum(row['total_shifts'] for row in data),
			'total_cash_sales': sum(row['total_cash_sales'] for row in data),
			'total_card_sales': sum(row['total_card_sales'] for row in data),
			'total_grand_total': sum(row['total_grand_total'] for row in data),
			'total_net_total': sum(row['total_net_total'] for row in data),
			'total_quantity': sum(row['total_quantity'] for row in data),
			'return_sales_total': sum(row['return_sales_total'] for row in data),
			'return_sales_count': sum(row['return_sales_count'] for row in data),
			'average_per_shift': 0,  # Will be calculated separately
			'posting_date': '',
			'cashier': ''
		}
		# Calculate overall average per shift
		if grand_totals['total_shifts'] > 0:
			grand_totals['average_per_shift'] = flt(grand_totals['total_grand_total']) / grand_totals['total_shifts']
		data.append(grand_totals)
	
	return data


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
