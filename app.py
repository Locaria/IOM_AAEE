import os
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title('Search in Google Sheets')

# Get the path to the credentials from the environment variable
creds_path = (r"C:/Users/yngrid.figlioli/Desktop/AAEE/IOM/plunetpulls-ca50ccd56cf0.json")

word_search = st.text_input("Keyword")
country_search = st.text_input("Country")

if st.button('Search'):
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    search_result = []

    for line in lines:
        if line["Target Country"] == country_search.upper() and word_search.lower() in line["Translation"].lower():
            search_result.append(line["Keyword"])

    if search_result:
        st.write("Word(s) found corresponding to the search:")
        for word in search_result:
            st.write(word)
    else:
        st.write(f"No match found for '{word_search}' in the country {country_search}.")
