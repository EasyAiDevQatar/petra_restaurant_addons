// Copyright (c) 2025, itsyosefali and contributors
// For license information, please see license.txt

// Get default currency from system
function getDefaultCurrency() {
	// Try to get currency from the report data or use a fallback
	let currency = "QAR"; // Default fallback
	
	// Try to get from company settings
	if (frappe.defaults.get_user_default("Company")) {
		try {
			currency = frappe.get_cached_value("Company", frappe.defaults.get_user_default("Company"), "default_currency") || "USD";
		} catch (e) {
			console.log("Could not get currency from company:", e);
		}
	}
	
	return currency;
}

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
		
		// Get currency dynamically
		const currency = getDefaultCurrency();
		
		// Style grand total row
		if (data.pos_opening_shift === "GRAND TOTAL") {
			if (column.fieldname === "pos_opening_shift") {
				value = `<strong style="color: #2c3e50; font-size: 1.1em; background-color: #f8f9fa; padding: 5px;">${value}</strong>`;
			} else if (column.fieldname.includes('total') || column.fieldname.includes('cost_center')) {
				value = `<strong style="color: #2c3e50; background-color: #e9ecef;">${value}</strong>`;
			}
		}
		
		// Style shift rows with better visual hierarchy
		if (data.pos_opening_shift && data.pos_opening_shift !== "GRAND TOTAL") {
			// Highlight POS Opening Shift column
			if (column.fieldname === "pos_opening_shift") {
				value = `<span style="color: #007bff; font-weight: 500;">${value}</span>`;
			}
			
			// Style cashier with icon
			if (column.fieldname === "cashier") {
				value = `<span style="color: #6c757d;">👤 ${value}</span>`;
			}
			
			// Style date column
			if (column.fieldname === "posting_date") {
				value = `<span style="color: #28a745; font-weight: 500;">📅 ${value}</span>`;
			}
			
			// Style POS Profile with badge
			if (column.fieldname === "pos_profile") {
				value = `<span class="badge badge-info">${value}</span>`;
			}
		}
		
		// Format currency values with better styling
		if (column.fieldname.includes('total') && typeof value === 'number' && value > 0) {
			value = `<span style="color: #28a745; font-weight: 500;">${new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: currency,
				minimumFractionDigits: 2
			}).format(value)}</span>`;
		}
		
		// Style cost center columns
		if (column.fieldname.includes('cost_center') && typeof value === 'number' && value > 0) {
			value = `<span style="color: #17a2b8; font-weight: 500;">${new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: currency,
				minimumFractionDigits: 2
			}).format(value)}</span>`;
		}
		
		// Style quantity column
		if (column.fieldname === "total_quantity" && typeof value === 'number' && value > 0) {
			value = `<span style="color: #fd7e14; font-weight: 500;">${value}</span>`;
		}
		
		return value;
	},
	
	
	"after_datatable_render": function(report) {
		// Auto-show charts when report loads with data - with better error handling
		setTimeout(function() {
			try {
				// Check if we have data before showing charts
				let data = report.data;
				
				// Try alternative data access methods if report.data is not available
				if (!data && report.datatable && report.datatable.datamanager) {
					data = report.datatable.datamanager.data;
				}
				if (!data && report.datatable && report.datatable.data) {
					data = report.datatable.data;
				}
				
				if (data && data.length > 0) {
					show_charts(report);
				}
			} catch (error) {
				console.log("Error in after_datatable_render:", error);
				// Don't show charts if there's an error
			}
		}, 2000);
	},
	
	"onload": function(report) {
		// Add CSS styles for better visual hierarchy
		const style = document.createElement('style');
		style.textContent = `
			/* Enhanced report styling */
			.report-table {
				border-radius: 8px !important;
				overflow: hidden !important;
				box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
			}
			
			/* Header styling */
			.report-table th {
				background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
				color: white !important;
				font-weight: 600 !important;
				text-transform: uppercase !important;
				font-size: 12px !important;
				letter-spacing: 0.5px !important;
				padding: 12px 8px !important;
				border: none !important;
			}
			
			/* Cost center columns header styling */
			.report-table th[data-fieldname*="cost_center_"] {
				background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
				color: white !important;
			}
			
			/* Total columns header styling */
			.report-table th[data-fieldname*="total_"] {
				background: linear-gradient(135deg, #fd7e14 0%, #e83e8c 100%) !important;
				color: white !important;
			}
			
			/* Body styling */
			.report-table td {
				padding: 10px 8px !important;
				border-bottom: 1px solid #e9ecef !important;
				vertical-align: middle !important;
			}
			
			/* Alternating row colors with hover effect */
			.report-table tbody tr:nth-child(even) {
				background-color: #f8f9fa !important;
			}
			
			.report-table tbody tr:hover {
				background-color: #e3f2fd !important;
				transform: scale(1.01) !important;
				transition: all 0.2s ease !important;
			}
			
			/* Grand total row styling */
			.report-table tbody tr:last-child {
				background: linear-gradient(135deg, #343a40 0%, #495057 100%) !important;
				color: white !important;
				font-weight: bold !important;
				border-top: 3px solid #007bff !important;
				font-size: 14px !important;
			}
			
			.report-table tbody tr:last-child td {
				border-bottom: none !important;
				padding: 12px 8px !important;
			}
			
			/* Badge styling */
			.badge {
				padding: 4px 8px !important;
				border-radius: 12px !important;
				font-size: 11px !important;
				font-weight: 500 !important;
			}
			
			.badge-info {
				background-color: #17a2b8 !important;
				color: white !important;
			}
			
			/* Link styling */
			.report-table a {
				text-decoration: none !important;
				color: inherit !important;
			}
			
			.report-table a:hover {
				text-decoration: underline !important;
			}
			
			/* Currency formatting */
			.report-table .currency {
				font-family: 'Courier New', monospace !important;
				font-weight: 500 !important;
			}
			
			/* Responsive design */
			@media (max-width: 768px) {
				.report-table {
					font-size: 12px !important;
				}
				.report-table th,
				.report-table td {
					padding: 6px 4px !important;
				}
			}
		`;
		document.head.appendChild(style);
		
		// Add interactive buttons
		report.page.add_inner_button(__("📊 Show Charts"), function() {
			show_charts(report);
		}, __("Charts"));
		
		report.page.add_inner_button(__("📋 Export Summary"), function() {
			export_summary(report);
		}, __("Export"));
		
		// Store the report reference globally for easier access
		window.pos_shift_report = report;
	}
};

// Chart functions
function show_charts(report) {
	// Try different ways to access the data with proper null checks
	let data = null;
	
	// Method 1: Try report.data first
	if (report.data && report.data.length > 0) {
		data = report.data;
	}
	
	// Method 2: Try datatable access with proper null checks
	if (!data) {
		try {
			if (report.datatable && report.datatable.datamanager && report.datatable.datamanager.data) {
				data = report.datatable.datamanager.data;
			}
		} catch (e) {
			console.log("Error accessing datatable.datamanager:", e);
		}
	}
	
	if (!data) {
		try {
			if (report.datatable && report.datatable.data) {
				data = report.datatable.data;
			}
		} catch (e) {
			console.log("Error accessing datatable.data:", e);
		}
	}
	
	// Method 3: Try to get data from the report's internal structure
	if (!data && report.report_data) {
		data = report.report_data;
	}
	
	// If still no data, try to refresh the report
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for charts. Please ensure the report has data and try again."));
		return;
	}
	
	// Debug: Log basic data info
	console.log(`Report data: ${data ? data.length : 0} rows`);
	
	// Remove grand total row for charts
	const chart_data = data.filter(row => row && row.pos_opening_shift !== "GRAND TOTAL");
	
	// Prepare cost center data
	const cost_centers = {};
	const cash_vs_card = { cash: 0, card: 0 };
	const shift_totals = [];
	
	// Debug: Log chart data info
	console.log(`Chart data: ${chart_data.length} rows after filtering`);
	
	if (chart_data.length === 0) {
		frappe.msgprint(__("No shift data available for charts. Please ensure you have closed shifts in the selected date range."));
		return;
	}
	
	chart_data.forEach(row => {
		if (!row) return;
		
		// Cost center analysis
		Object.keys(row).forEach(key => {
			if (key.startsWith('cost_center_') && row[key] > 0) {
				const cost_center = key.replace('cost_center_', '').replace(/_/g, ' ');
				if (!cost_centers[cost_center]) {
					cost_centers[cost_center] = 0;
				}
				cost_centers[cost_center] += parseFloat(row[key]) || 0;
			}
		});
		
		// Cash vs Card analysis
		cash_vs_card.cash += parseFloat(row.total_cash_sales) || 0;
		cash_vs_card.card += parseFloat(row.total_card_sales) || 0;
		
		// Shift totals for trend analysis
		shift_totals.push({
			shift: row.pos_opening_shift,
			date: row.posting_date,
			total: parseFloat(row.total_grand_total) || 0
		});
	});
	
	// Debug: Log processed data summary
	console.log(`Cost centers: ${Object.keys(cost_centers).length} found`);
	console.log(`Cash vs Card: Cash=${cash_vs_card.cash}, Card=${cash_vs_card.card}`);
	console.log(`Shift totals: ${shift_totals.length} shifts`);
	
	// Create charts dialog
	const dialog = new frappe.ui.Dialog({
		title: __("Shift Summary Charts"),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'charts_container'
			}
		]
	});
	
	// Prepare chart containers with proper canvas elements
	const charts_html = `
		<div class="row">
			<div class="col-md-6">
				<div class="chart-container">
					<h5>Cost Centers Analysis</h5>
					<canvas id="cost_center_chart" width="400" height="300"></canvas>
				</div>
			</div>
			<div class="col-md-6">
				<div class="chart-container">
					<h5>Cash vs Card Sales</h5>
					<canvas id="payment_chart" width="400" height="300"></canvas>
				</div>
			</div>
		</div>
		<div class="row">
			<div class="col-md-12">
				<div class="chart-container">
					<h5>Shift Performance Trend</h5>
					<canvas id="trend_chart" width="800" height="300"></canvas>
				</div>
			</div>
		</div>
	`;
	
	dialog.fields_dict.charts_container.$wrapper.html(charts_html);
	dialog.show();
	
	// Load Chart.js with proper error handling and fallback
	const loadChartJS = () => {
		// Try to load Chart.js from CDN
		frappe.require('https://cdn.jsdelivr.net/npm/chart.js', () => {
		// Wait for DOM elements to be ready
		setTimeout(() => {
			try {
				// Cost Center Chart (Pie Chart) - only if we have cost center data
				if (Object.keys(cost_centers).length > 0) {
					const costCenterCanvas = document.getElementById('cost_center_chart');
					if (costCenterCanvas && costCenterCanvas.getContext) {
						const costCenterCtx = costCenterCanvas.getContext('2d');
								new Chart(costCenterCtx, {
							type: 'doughnut',
							data: {
								labels: Object.keys(cost_centers),
								datasets: [{
									data: Object.values(cost_centers),
									backgroundColor: [
										'#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
										'#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
									],
									borderWidth: 2,
									borderColor: '#fff'
								}]
							},
							options: {
								responsive: true,
								plugins: {
									legend: {
										position: 'bottom'
									},
									title: {
										display: true,
										text: 'Sales by Cost Center'
									}
								}
							}
						});
					}
				} else {
					// Show basic shift totals if no cost center data
					const basic_totals = {};
					chart_data.forEach(row => {
						if (row.total_grand_total > 0) {
							const profile = row.pos_profile || 'Unknown Profile';
							if (!basic_totals[profile]) {
								basic_totals[profile] = 0;
							}
							basic_totals[profile] += parseFloat(row.total_grand_total) || 0;
						}
					});
					
					if (Object.keys(basic_totals).length > 0) {
						const costCenterCanvas = document.getElementById('cost_center_chart');
						if (costCenterCanvas && costCenterCanvas.getContext) {
							const costCenterCtx = costCenterCanvas.getContext('2d');
							new Chart(costCenterCtx, {
								type: 'doughnut',
								data: {
									labels: Object.keys(basic_totals),
									datasets: [{
										data: Object.values(basic_totals),
										backgroundColor: [
											'#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
											'#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
										],
										borderWidth: 2,
										borderColor: '#fff'
									}]
								},
								options: {
									responsive: true,
									plugins: {
										legend: {
											position: 'bottom'
										},
										title: {
											display: true,
											text: 'Sales by POS Profile'
										}
									}
								}
							});
						}
					} else {
						const costCenterCanvas = document.getElementById('cost_center_chart');
						if (costCenterCanvas) {
							costCenterCanvas.innerHTML = 
								'<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">No sales data available</div>';
						}
					}
				}
		
				// Payment Method Chart (Pie Chart)
				if (cash_vs_card.cash > 0 || cash_vs_card.card > 0) {
					const paymentCanvas = document.getElementById('payment_chart');
					if (paymentCanvas && paymentCanvas.getContext) {
						const paymentCtx = paymentCanvas.getContext('2d');
						new Chart(paymentCtx, {
							type: 'pie',
							data: {
								labels: ['Cash Sales', 'Card Sales'],
								datasets: [{
									data: [cash_vs_card.cash, cash_vs_card.card],
									backgroundColor: ['#28a745', '#007bff'],
									borderWidth: 2,
									borderColor: '#fff'
								}]
							},
							options: {
								responsive: true,
								plugins: {
									legend: {
										position: 'bottom'
									},
									title: {
										display: true,
										text: 'Payment Methods Distribution'
									}
								}
							}
						});
					}
				} else {
					// Show message if no payment data
					const paymentCanvas = document.getElementById('payment_chart');
					if (paymentCanvas) {
						paymentCanvas.innerHTML = 
							'<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">No payment data available</div>';
					}
				}
				
				// Trend Chart (Line Chart)
				if (shift_totals.length > 0) {
					const trendCanvas = document.getElementById('trend_chart');
					if (trendCanvas && trendCanvas.getContext) {
						const trendCtx = trendCanvas.getContext('2d');
						new Chart(trendCtx, {
							type: 'line',
							data: {
								labels: shift_totals.map(item => item.date),
								datasets: [{
									label: `Shift Total (${getDefaultCurrency()})`,
									data: shift_totals.map(item => item.total),
									borderColor: '#007bff',
									backgroundColor: 'rgba(0, 123, 255, 0.1)',
									borderWidth: 2,
									fill: true,
									tension: 0.4
								}]
							},
							options: {
								responsive: true,
									scales: {
										y: {
											beginAtZero: true,
											ticks: {
												callback: function(value) {
													return getDefaultCurrency() + ' ' + value.toLocaleString();
												}
											}
										}
									},
								plugins: {
									title: {
										display: true,
										text: 'Daily Shift Performance'
									}
								}
							}
						});
					}
				} else {
					// Show message if no trend data
					const trendCanvas = document.getElementById('trend_chart');
					if (trendCanvas) {
						trendCanvas.innerHTML = 
							'<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">No trend data available</div>';
					}
				}
			} catch (error) {
				console.log("Error creating charts:", error);
				frappe.msgprint(__("Error creating charts. Please try again."));
			}
		}, 100); // Small delay to ensure DOM is ready
		}, (error) => {
			console.log("Failed to load Chart.js from CDN:", error);
			// Fallback: show message instead of charts
			frappe.msgprint(__("Charts are not available. Please check your internet connection."));
		});
	};
	
	// Load Chart.js
	loadChartJS();
}

// Export summary function
function export_summary(report) {
	let data = null;
	
	// Try different ways to access the data
	if (report.data && report.data.length > 0) {
		data = report.data;
	}
	
	if (!data) {
		try {
			if (report.datatable && report.datatable.datamanager && report.datatable.datamanager.data) {
				data = report.datatable.datamanager.data;
			}
		} catch (e) {
			console.log("Error accessing datatable:", e);
		}
	}
	
	if (!data || data.length === 0) {
		frappe.msgprint(__("No data available for export."));
		return;
	}
	
	// Filter out grand total for export
	const export_data = data.filter(row => row.pos_opening_shift !== "GRAND TOTAL");
	
	if (export_data.length === 0) {
		frappe.msgprint(__("No shift data available for export."));
		return;
	}
	
	// Calculate summary statistics
	const total_shifts = export_data.length;
	const total_sales = export_data.reduce((sum, row) => sum + (row.total_grand_total || 0), 0);
	const total_cash = export_data.reduce((sum, row) => sum + (row.total_cash_sales || 0), 0);
	const total_card = export_data.reduce((sum, row) => sum + (row.total_card_sales || 0), 0);
	const avg_per_shift = total_sales / total_shifts;
	
	// Get currency dynamically
	const currency = getDefaultCurrency();
	
	// Create summary dialog
	const dialog = new frappe.ui.Dialog({
		title: __("📋 Shift Summary Export"),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'summary_content'
			}
		]
	});
	
	const summary_html = `
		<div class="row">
			<div class="col-md-12">
				<div class="alert alert-info">
					<h4>📊 Shift Summary Statistics</h4>
				</div>
			</div>
		</div>
		<div class="row">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header bg-primary text-white">
						<h5>📈 Performance Metrics</h5>
					</div>
					<div class="card-body">
						<p><strong>Total Shifts:</strong> ${total_shifts}</p>
						<p><strong>Total Sales:</strong> ${new Intl.NumberFormat('en-US', {
							style: 'currency',
							currency: currency,
							minimumFractionDigits: 2
						}).format(total_sales)}</p>
						<p><strong>Average per Shift:</strong> ${new Intl.NumberFormat('en-US', {
							style: 'currency',
							currency: currency,
							minimumFractionDigits: 2
						}).format(avg_per_shift)}</p>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header bg-success text-white">
						<h5>💳 Payment Breakdown</h5>
					</div>
					<div class="card-body">
						<p><strong>Cash Sales:</strong> ${new Intl.NumberFormat('en-US', {
							style: 'currency',
							currency: currency,
							minimumFractionDigits: 2
						}).format(total_cash)}</p>
						<p><strong>Card Sales:</strong> ${new Intl.NumberFormat('en-US', {
							style: 'currency',
							currency: currency,
							minimumFractionDigits: 2
						}).format(total_card)}</p>
						<p><strong>Cash %:</strong> ${((total_cash / total_sales) * 100).toFixed(1)}%</p>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-3">
			<div class="col-md-12">
				<button class="btn btn-primary" onclick="copyToClipboard()">📋 Copy Summary</button>
				<button class="btn btn-success" onclick="downloadCSV()">📥 Download CSV</button>
			</div>
		</div>
	`;
	
	dialog.fields_dict.summary_content.$wrapper.html(summary_html);
	dialog.show();
	
	// Add global functions for the buttons
	window.copyToClipboard = function() {
		const summary = `POS Shift Summary Report
Total Shifts: ${total_shifts}
Total Sales: ${new Intl.NumberFormat('en-US', {style: 'currency', currency: currency}).format(total_sales)}
Average per Shift: ${new Intl.NumberFormat('en-US', {style: 'currency', currency: currency}).format(avg_per_shift)}
Cash Sales: ${new Intl.NumberFormat('en-US', {style: 'currency', currency: currency}).format(total_cash)}
Card Sales: ${new Intl.NumberFormat('en-US', {style: 'currency', currency: currency}).format(total_card)}`;
		
		navigator.clipboard.writeText(summary).then(() => {
			frappe.msgprint(__("Summary copied to clipboard!"));
		});
	};
	
	window.downloadCSV = function() {
		// Simple CSV export
		const csvContent = "data:text/csv;charset=utf-8," + 
			"POS Opening Shift,POS Profile,Date,Cashier,Grand Total,Cash Sales,Card Sales\n" +
			export_data.map(row => 
				`${row.pos_opening_shift},${row.pos_profile},${row.posting_date},${row.cashier},${row.total_grand_total},${row.total_cash_sales},${row.total_card_sales}`
			).join("\n");
		
		const encodedUri = encodeURI(csvContent);
		const link = document.createElement("a");
		link.setAttribute("href", encodedUri);
		link.setAttribute("download", `pos_shift_summary_${new Date().toISOString().split('T')[0]}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		
		frappe.msgprint(__("CSV file downloaded successfully!"));
	};
}
