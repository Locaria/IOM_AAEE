import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pytrends.request import TrendReq
import os

# Mapping of provided country codes to their respective language codes
country_language_mapping = {
    'CZ': 'cs-CZ',  # Czech Republic
    'DE': 'de-DE',  # Germany
    'DK': 'da-DK',  # Denmark
    'ES': 'es-ES',  # Spain
    'FI': 'fi-FI',  # Finland
    'FR': 'fr-FR',  # France
    'GR': 'el-GR',  # Greece
    'IT': 'it-IT',  # Italy
    'NL': 'nl-NL',  # Netherlands
    'NO': 'no-NO',  # Norway
    'PL': 'pl-PL',  # Poland
    'PT': 'pt-PT',  # Portugal
    'SE': 'sv-SE',  # Sweden
    'SK': 'sk-SK',  # Slovakia
    'UK': 'en-GB',  # United Kingdom
    'ES-MX': 'es-MX',  # Spanish (Mexico)
}

def get_google_sheets_credentials():
    creds_file_path = 'credentials.json'
    if not os.path.exists(creds_file_path):
        raise EnvironmentError("Google Sheets credentials file not found.")
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)
    return creds

def get_keyword_suggestions(keyword, language_code):
    pytrends = TrendReq(hl=language_code, tz=360)
    pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
    data = pytrends.related_queries()
    if data[keyword]['top'] is not None:
        return data[keyword]['top']['query'].tolist()
    else:
        return ["No suggestion available"]

def search_keywords(dataframe, country, creds):
    client = gspread.authorize(creds)
    spreadsheet_id = 'YOUR_SPREADSHEET_ID'  # Replace with your actual spreadsheet ID
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    keyword_column = []
    suggestion_column = []

    language_code = country_language_mapping.get(country, 'en-US')

    new_suggestions = []

    for keyword in dataframe['Keyword']:
        found = False
        for line in lines:
            if line["Target Country"].upper() == country.upper() and keyword.lower() in line["Translation"].lower():
                keyword_column.append(line["Keyword"])
                suggestion_column.append("N/A")
                found = True
                break
        if not found:
            suggestions = get_keyword_suggestions(keyword, language_code)
            keyword_column.append("Keyword not saved in the database yet")
            suggestion_column.append(", ".join(suggestions))
            if "No suggestion available" not in suggestions:
                new_suggestions.append({"Keyword": keyword, "Suggested Keywords": suggestions})

    dataframe['Found Keyword'] = keyword_column
    dataframe['Suggested Keywords'] = suggestion_column

    return dataframe, new_suggestions

def main():
    st.title('Keyword Checker and Suggestion Tool')

    st.write("Upload an Excel file, choose the country, and get keyword suggestions.")

    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("File uploaded successfully!")

        country = st.selectbox("Select Country", options=list(country_language_mapping.keys()))

        if st.button("Process"):
            creds = get_google_sheets_credentials()
            updated_df, new_suggestions = search_keywords(df, country, creds)

            st.write("Keyword results:")
            st.dataframe(updated_df)

            if st.button("Confirm and Download"):
                # Update Google Sheet with new suggestions
                client = gspread.authorize(creds)
                spreadsheet_id = 'YOUR_SPREADSHEET_ID'  # Replace with your actual spreadsheet ID
                spreadsheet = client.open_by_key(spreadsheet_id)
                sheet = spreadsheet.sheet1

                for suggestion in new_suggestions:
                    sheet.append_row([suggestion['Keyword'], ', '.join(suggestion['Suggested Keywords']), country])

                # Convert DataFrame to Excel and download
                output_filepath = 'updated_keywords.xlsx'
                updated_df.to_excel(output_filepath, index=False)

                st.success("Updated keywords have been added to the Google Sheet and the Excel file is ready for download.")
                with open(output_filepath, "rb") as file:
                    st.download_button(label="Download updated Excel file", data=file, file_name=output_filepath)

if __name__ == '__main__':
    main()
    
