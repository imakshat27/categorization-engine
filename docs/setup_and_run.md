# Setup and Run Guide (Windows)

This guide walks you through the exact steps to download the Financial Transaction Intelligence Engine from GitHub, set it up on a Windows machine, and run the application.

## 1. Get the Code from GitHub

Open **Command Prompt** or **PowerShell** and clone the repository using Git:
```cmd
git clone https://github.com/your-username/categorization-engine.git
cd categorization-engine
```
*(Replace the URL with the actual GitHub repository link)*

## 2. Windows Setup Commands

Run the following commands sequentially to set up your Python environment and install the required dependencies:

```cmd
:: Create a local virtual environment
python -m venv venv

:: Activate the virtual environment
venv\Scripts\activate

:: Note: If you get an execution policy error in PowerShell, run this first:
:: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

:: Install all dependencies
pip install -r requirements.txt
```

## 3. Run the Dashboard

With your virtual environment activated and dependencies installed, start the Streamlit web application:

```cmd
streamlit run app.py
```

---

## 4. Dashboard Overview

Once you run the command above, your default web browser will open automatically (usually to `http://localhost:8501`) displaying the simple Streamlit dashboard.

**How to use the dashboard:**

1. **Upload File:**
   You will see a file uploader component. Drag and drop your Excel or CSV transaction file here.

2. **Process:**
   Once uploaded, the engine automatically runs the transactions through the deterministic pipeline (Normalization -> Protocol Detection -> Semantic Parsing -> Entity Intelligence -> Classification).

3. **View Results:**
   The dashboard will render a table showing the original narrations alongside the new predicted categories, confidence scores, and any detected conflicts.

4. **Export/Download:**
   You can download the processed results as a new Excel or CSV file for your reporting or downstream systems.
