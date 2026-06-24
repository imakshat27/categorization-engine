# Windows Setup Guide

Follow these steps to set up and run the Categorization Engine on a Windows machine.

## Prerequisites
- **Python**: Ensure Python 3.8 or newer is installed and added to your PATH. You can check by opening Command Prompt or PowerShell and running `python --version`.

## 1. Open the Project
Open Command Prompt or PowerShell and navigate to the folder where you cloned the repository:
```cmd
cd path\to\categorization-engine
```

## 2. Create a Virtual Environment
Create a local virtual environment to isolate the project dependencies:
```cmd
python -m venv venv
```

## 3. Activate the Virtual Environment
Activate the virtual environment. This tells your terminal to use the project's isolated Python environment.
```cmd
venv\Scripts\activate
```
*(Note: If you encounter an execution policy error in PowerShell, you can temporarily allow scripts by running: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

## 4. Install Dependencies
Install all the required Python libraries using pip:
```cmd
pip install -r requirements.txt
```

## 5. Run the Application
Start the Streamlit web application:
```cmd
streamlit run app.py
```

This command will automatically open your default web browser to the Streamlit app interface (usually `http://localhost:8501`). From there, you can upload an Excel file containing your transactions and proceed with the categorization.
