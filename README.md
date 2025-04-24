# Persevera Asset Management Dashboard

## Overview
This dashboard provides tools and analytics for financial analysis across different asset classes for Persevera Asset Management. The application uses Streamlit's multi-page app framework to organize functionality into separate pages for better performance and maintainability.

## Features
- **Home**: Overview and key metrics
- **Renda Fixa**: Fixed income analysis tools
  - Yield Curve Analysis
  - Bond Analysis
  - Credit Analysis
  - Stress Testing
- **RVQM (Equities & Quant)**: Equity markets and quantitative tools
  - Market Overview
  - Stock Screener
  - Factor Analysis
  - Portfolio Construction
- **Market Data**: Market data visualization and analysis
  - Market Indices
  - Economic Indicators
  - Rates & FX
  - Commodities
- **Portfolio Analysis**: Portfolio management tools
  - Performance
  - Attribution
  - Risk Analysis
  - Allocation
- **Meetings**: Meeting management and notes
  - Meetings Overview
  - Estratégia Meetings
  - Economia Meetings
  - Timing & Awareness Meetings
- **Settings**: Application configuration
  - User Preferences
  - Data Sources
  - API Keys
  - Database
  - About

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Anaconda (recommended)

### Installation

1. Clone this repository or download the source code
2. Navigate to the project directory
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

### Running the Dashboard

#### Windows
Run the `start_dashboard.bat` file, or use the command:
```
streamlit run app.py
```

#### Mac/Linux
```
streamlit run app.py
```

The dashboard will open in your default web browser at http://localhost:8501

## Project Structure
- `app.py`: Main Streamlit application (home page)
- `pages/`: Directory containing all individual pages
  - `Home.py`: Home page with overview and key metrics
  - `1_Renda_Fixa.py`: Fixed income analysis tools
  - `2_RVQM.py`: Equities and quant tools
  - `3_Market_Data.py`: Market data visualization
  - `4_Portfolio_Analysis.py`: Portfolio management tools
  - `5_Meetings.py`: Meetings overview dashboard
  - `5_Meetings_Estrategia.py`: Estratégia meetings
  - `5_Meetings_Economia.py`: Economia meetings
  - `5_Meetings_Timing.py`: Timing & Awareness meetings
  - `6_Settings.py`: Application settings
- `utils/`: Utility functions
  - `data_loader.py`: Functions for loading and processing data
- `data/`: Data files and databases
- `assets/`: Static assets like images and CSS
- `.streamlit/`: Streamlit configuration files

## Development

### Adding a New Page
To add a new page to the dashboard:
1. Create a new Python file in the `pages/` directory with a numeric prefix to control order (e.g. `7_NewPage.py`)
2. Use the template from existing pages
3. Implement your functionality

### Adding Sub-Pages
To create sub-pages with their own URLs (like the Meetings pages):
1. Create multiple files with the same numeric prefix (e.g., `5_Category_SubPage1.py`, `5_Category_SubPage2.py`)
2. Add navigation links between them with HTML using the st.markdown function
3. They will appear grouped together in the sidebar but have distinct URLs

### Modifying Existing Pages
Each page is a self-contained Streamlit application. You can modify any page without affecting other pages.

## Data Sources
This dashboard can connect to various data sources:
- Local CSV/Excel files
- APIs (Bloomberg, Yahoo Finance, etc.)
- Databases

Configure data sources in the Settings page.

## Troubleshooting

**Dashboard fails to start:**
- Ensure all required packages are installed: `pip install -r requirements.txt`
- Check the Python version: `python --version` (should be 3.9+)
- Verify the Anaconda path in `start_dashboard.bat` is correct for your system

**Pages not showing up:**
- Ensure page files are in the `pages/` directory
- Verify page filenames start with a number to control order
- Check that each page has the correct import statements

**Sub-page navigation not working:**
- Make sure the URLs in the navigation links match exactly with the page filenames
- Check that the pages are using the same numeric prefix to group them together

## License
© 2025 Persevera Asset Management 