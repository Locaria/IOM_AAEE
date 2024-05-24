import pandas as pd
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def upload_excel():
    filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
    if not filepath:
        return None
    return pd.read_excel(filepath)

def download_excel(data):
    filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if not filepath:
        return
    data.to_excel(filepath, index=False)

def get_google_sheets_credentials():
    creds_file_path = os.getenv('GOOGLE_SHEETS_CREDS')
    if not creds_file_path:
        raise EnvironmentError("Google Sheets credentials file path not set in environment variable 'GOOGLE_SHEETS_CREDS'.")
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)
    return creds

def search_keywords(dataframe, country, creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    keyword_column = []

    for keyword in dataframe['Keyword']:
        found = False
        for line in lines:
            if line["Target Country"].upper() == country.upper() and keyword.lower() in line["Translation"].lower():
                keyword_column.append(line["Keyword"])
                found = True
                break
        if not found:
            keyword_column.append("Keyword not saved in the database yet")

    dataframe['Found Keyword'] = keyword_column
    return dataframe

def main():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    country = simpledialog.askstring("Input", "Please enter the country:", parent=root)
    if not country:
        root.destroy()
        return

    try:
        creds = get_google_sheets_credentials()
    except EnvironmentError as e:
        messagebox.showerror("Error", str(e))
        root.destroy()
        return

    df = upload_excel()
    if df is None:
        messagebox.showerror("Error", "No file selected.")
        root.destroy()
        return

    try:
        updated_df = search_keywords(df, country, creds)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        root.destroy()
        return

    download_excel(updated_df)
    messagebox.showinfo("Done", "The operation was completed successfully.", parent=root)
    root.destroy()

if __name__ == "__main__":
    main()
