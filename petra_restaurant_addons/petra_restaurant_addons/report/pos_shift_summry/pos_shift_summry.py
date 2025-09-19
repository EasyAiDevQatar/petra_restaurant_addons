# Copyright (c) 2025, itsyosefali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def format_currency(amount, company=None):
	"""Format currency for display using system default currency"""
	currency = frappe.get_cached_value("Company", company or frappe.defaults.get_user_default("Company"), "default_currency")
	return f"{currency} {flt(amount):.2f}"


def execute(filters=None):
	columns, cost_centers = get_columns(filters)
	data = get_data(filters, cost_centers)
	return columns, data


def get_columns(filters=None):
	# Get all unique cost centers from the data
	cost_centers = get_cost_centers(filters)
	
	# Get default currency from company
	company = filters.get("company") or frappe.defaults.get_user_default("Company")
	default_currency = frappe.get_cached_value("Company", company, "default_currency")
	# Base columns - basic information with enhanced styling
	columns = [
		{
			"fieldname": "pos_opening_shift",
			"label": _("POS Opening Shift"),
			"fieldtype": "Link",
			"options": "POS Opening Shift",
			"width": 200,
			"align": "left"
		},
		{
			"fieldname": "pos_profile",
			"label": _("POS Profile"),
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 120,
			"align": "center"
		},
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100,
			"align": "center"
		},
		{
			"fieldname": "cashier",
			"label": _("Cashier"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120,
			"align": "left"
		},
		{
			"fieldname": "total_shifts",
			"label": _("Shifts"),
			"fieldtype": "Int",
			"width": 80,
			"align": "center"
		}
	]
	
	# Add dynamic cost center columns with enhanced styling
	for cost_center in cost_centers:
		columns.append({
			"fieldname": f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}",
			"label": cost_center,
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
			"options": default_currency
		})
	
	# Add totals columns at the end with enhanced styling
	totals_columns = [
		{
			"fieldname": "total_cash_sales",
			"label": _("Cash Sales"),
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
			"options": default_currency
		},
		{
			"fieldname": "total_card_sales",
			"label": _("Card Sales"),
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
			"options": default_currency
		},
		{
			"fieldname": "total_grand_total",
			"label": _("Grand Total"),
			"fieldtype": "Currency",
			"width": 120,
			"align": "right",
			"options": default_currency
		},
		{
			"fieldname": "total_net_total",
			"label": _("Net Total"),
			"fieldtype": "Currency",
			"width": 120,
			"align": "right",
			"options": default_currency
		},
		{
			"fieldname": "total_quantity",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 80,
			"align": "right"
		},
		{
			"fieldname": "average_per_shift",
			"label": _("Avg/Shift"),
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
			"options": default_currency
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
				'total_shifts': 1,
				'total_cash_sales': 0,
				'total_card_sales': 0,
				'total_grand_total': flt(shift.grand_total),
				'total_net_total': flt(shift.net_total),
				'total_quantity': flt(shift.total_quantity),
				'average_per_shift': flt(shift.grand_total),
				'posting_date': shift.posting_date,
				'cashier': shift.cashier
			}
			
			# Get payment breakdown for this shift
			payment_data = get_payment_breakdown(shift.pos_opening_shift)
			shift_data[opening_shift]['total_cash_sales'] = payment_data.get('cash', 0)
			shift_data[opening_shift]['total_card_sales'] = payment_data.get('card', 0)
			
			# Initialize cost center columns
			for cost_center in cost_centers:
				field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
				shift_data[opening_shift][field_name] = 0
			
			# Set the value for this shift's cost center
			if shift.cost_center:
				field_name = f"cost_center_{shift.cost_center.replace(' ', '_').replace('-', '_')}"
				shift_data[opening_shift][field_name] = flt(shift.grand_total)
	
	# Convert to list
	data = []
	for shift_key, shift_info in shift_data.items():
		data.append(shift_info)
	
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
			'average_per_shift': 0,
			'posting_date': '',
			'cashier': ''
		}
		
		# Add cost center totals
		for cost_center in cost_centers:
			field_name = f"cost_center_{cost_center.replace(' ', '_').replace('-', '_')}"
			grand_totals[field_name] = sum(row.get(field_name, 0) for row in data)
		
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
