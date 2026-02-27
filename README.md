# 🚀 AutoSales - Sales Automation Dashboard

A modern, Flask-based sales automation dashboard for analyzing and visualizing sales data with interactive charts and automated report generation.

## Features

- **CSV Data Upload & Processing** - Upload sales data in CSV format with automatic column detection
- **Interactive Sales Charts** - Visualize sales data with Chart.js powered charts
- **Multiple Time Modes** - Analyze data by date, year/month, year only, or month only
- **Automated Report Generation** - Generate Excel (.xlsx) and PDF reports
- **Chart History** - Save and load previous chart configurations
- **Analytics Dashboard** - View KPIs and insights from generated reports
- **Configurable Storage** - Customize upload and output folder locations
- **Admin Panel** - Manage system settings and user information

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, Tailwind CSS, Chart.js
- **Data Processing**: Pandas
- **Report Generation**: ReportLab (PDF), OpenPyXL (Excel)

## Project Structure

```
sales-automation-dashboard/
├── app.py                 # Main Flask application
├── chart_history.json     # Saved chart configurations
├── sales_data_sample.csv  # Sample data file
├── output/                # Generated reports directory
├── static/
│   ├── interactive-bg.js  # Interactive background effects
│   └── style.css          # Custom styles
├── templates/
│   ├── index.html         # Main dashboard
│   ├── reports.html       # Reports listing
│   ├── analytics.html     # Analytics page
│   ├── settings.html      # Settings configuration
│   └── admin.html         # Admin panel
└── uploads/               # Uploaded CSV files
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/sales-automation-dashboard.git
   cd sales-automation-dashboard
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install flask pandas reportlab openpyxl
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   Navigate to `http://localhost:5000`

## Usage

### Uploading Sales Data

1. Click on the Dashboard page
2. Upload a CSV file containing your sales data
3. Map the columns (Product, Total/Revenue, Quantity, Price, Date)
4. Select the time mode for analysis
5. Click "Process Data" to generate charts

### CSV Column Requirements

Your CSV file should contain columns for:
- **Product** - Product name or identifier
- **Total/Revenue** - Sales amount (or Quantity + Price)
- **Date** - Transaction date (optional, depends on time mode)
- **Year/Month** - For year/month based analysis

### Generating Reports

Reports are automatically generated when processing data:
- **Excel Reports** - Full data export with calculations
- **PDF Reports** - Summary reports for printing

### Viewing Analytics

The Analytics page displays:
- Total reports generated
- Report breakdown by type (Excel/PDF)
- Latest report KPIs
- Storage usage statistics

## Configuration

Storage paths can be configured via the Settings page:
- **Upload Folder** - Where uploaded CSV files are stored
- **Output Folder** - Where generated reports are saved

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
