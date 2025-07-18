# 🔐 Privacy Policy Scraper

This Python script scrapes privacy policy links and content from a list of websites and exports the data to a CSV file.

## 📂 Project Structure

```

privacy-scrape/
├── claude/                     # Output folder for CSVs
│   ├── privacy\_policies.csv
│   └── privacy\_policies\_summary.csv
├── main.py                     # Main scraping script
├── websites.py                 # List of websites to scan
├── .gitignore
├── README.md
└── .venv/                      # Local virtual environment (ignored)

````

## 🚀 Features

- Automatically detects privacy policy URLs from given websites
- Extracts up to 10,000 characters of visible text content
- Saves results to a CSV file
- Supports `.venv` Python environments

## 📦 Requirements

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate.bat    # Windows

pip install -r requirements.txt
````

If `requirements.txt` doesn’t exist, install manually:

```bash
pip install requests beautifulsoup4 tldextract
```

## 🧠 How It Works

* `main.py` reads URLs from `websites.py`
* For each site, it:

  1. Finds a link containing the word "privacy"
  2. Visits that link and extracts visible text
  3. Saves the company name, policy URL, and text to CSV

## 🛠️ Usage

```bash
python main.py
```

Output will be saved as:

* `privacy_policies.csv` – Raw text data
* `privacy_policies_summary.csv` – (Optional) Summarized version if implemented

## 📄 License

MIT License
