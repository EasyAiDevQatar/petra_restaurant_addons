// Copyright (c) 2025, itsyosefali and contributors
// For license information, please see license.txt

frappe.query_reports["POS Shift Summry"] = {
	"filters": [
		{
			"fieldname": "pos_opening_shifts",
			"label": __("POS Opening Shifts"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				return frappe.db.get_link_options("POS Opening Shift", txt);
			},
			"reqd": 0
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "pos_profile",
			"label": __("POS Profile"),
			"fieldtype": "Link",
			"options": "POS Profile",
			"reqd": 0
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 0
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Style group rows (shifts) differently
		if (data._is_group === 1 && column.fieldname === "pos_opening_shift") {
			value = `<strong style="color: #2c3e50;">${value}</strong>`;
		}
		
		// Style child rows (invoices) with indentation
		if (data._is_group === 0 && data._indent === 1 && column.fieldname === "pos_opening_shift") {
			value = `<span style="color: #6c757d; font-style: italic;">${value}</span>`;
		}
		
		// Style item rows with deeper indentation
		if (data._is_group === 0 && data._indent === 2 && column.fieldname === "pos_opening_shift") {
			value = `<span style="color: #495057; font-size: 0.9em;">${value}</span>`;
		}
		
		// Format currency values
		if (column.fieldname.includes('total') && typeof value === 'number') {
			value = new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: 'LYD',
				minimumFractionDigits: 2
			}).format(value);
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add CSS styles for better visual hierarchy
		const style = document.createElement('style');
		style.textContent = `
			/* Group row styling (shifts) */
			.report-table tbody tr[data-is-group="1"] {
				background-color: #f8f9fa !important;
				font-weight: bold;
			}
			
			/* Invoice row styling */
			.report-table tbody tr[data-is-group="0"][data-indent="1"] {
				background-color: #ffffff !important;
				border-left: 3px solid #007bff;
			}
			
			/* Item row styling */
			.report-table tbody tr[data-is-group="0"][data-indent="2"] {
				background-color: #f8f9fa !important;
				border-left: 3px solid #28a745;
				font-size: 0.9em;
			}
			
			/* Grand total row styling */
			.report-table tbody tr:last-child {
				background-color: #e9ecef !important;
				font-weight: bold;
				border-top: 2px solid #6c757d;
			}
			
			/* Better spacing and typography */
			.report-table td {
				padding: 6px 12px !important;
			}
			
			.report-table th {
				background-color: #495057 !important;
				color: white !important;
				font-weight: bold !important;
			}
			
			/* Indentation for visual hierarchy */
			.report-table tbody tr[data-indent="1"] td:first-child {
				padding-left: 20px !important;
			}
			
			.report-table tbody tr[data-indent="2"] td:first-child {
				padding-left: 40px !important;
			}
		`;
		document.head.appendChild(style);
	}
};
