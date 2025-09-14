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
	]
};
