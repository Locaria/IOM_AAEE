import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from google.cloud import translate_v2 as translate

# Mapping of provided country codes to their respective language codes
country_language_mapping = {
    'CZ': 'cs',  # Czech Republic
    'DE': 'de',  # Germany
    'DK': 'da',  # Denmark
    'ES': 'es',  # Spain
    'FI': 'fi',  # Finland
    'FR': 'fr',  # France
    'GR': 'el',  # Greece
    'IT': 'it',  # Italy
    'NL': 'nl',  # Netherlands
    'NO': 'no',  # Norway
    'PL': 'pl',  # Poland
    'PT': 'pt',  # Portugal
    'SE': 'sv',  # Sweden
    'SK': 'sk',  # Slovakia
    'UK': 'en',  # United Kingdom
    'ES-MX': 'es',  # Spanish (Mexico)
}

def get_google_sheets_credentials():
    google_credentials = st.secrets['google_credentials']['secret']
    secret = json.loads(google_credentials)
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(secret, scope)
    return credentials

def translate_text(text, target_language):
    translate_client = translate.Client()
    result = translate_client.translate(text, target_language=target_language)
    return result['translatedText']

def search_keywords(dataframe, country, creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    keyword_column = []
    suggestion_column = []

    language_code = country_language_mapping.get(country, 'en')  # Determine language_code
    st.write(f"Using language code: {language_code}")  # Debugging line to check language code

    for keyword in dataframe['Keyword']:
        found = False
        for line in lines:
            if line["Target Country"].upper() == country.upper() and keyword.lower() in line["Translation"].lower():
                keyword_column.append(line["Keyword"])
                suggestion_column.append("N/A")
                found = True
                break
        if not found:
            translated_keyword = translate_text(keyword, language_code)
            keyword_column.append(translated_keyword)
            suggestion_column.append("No suggestion available")

    dataframe['Found Keyword'] = keyword_column
    dataframe['Suggested Keywords'] = suggestion_column

    return dataframe

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
            updated_df = search_keywords(df, country, creds)

            st.write("Keyword results:")
            st.dataframe(updated_df)

            if st.button("Confirm and Download"):
                # Convert DataFrame to Excel and download
                output_filepath = 'updated_keywords.xlsx'
                updated_df.to_excel(output_filepath, index=False)

                st.success("Updated keywords have been added to the Excel file is ready for download.")
                with open(output_filepath, "rb") as file:
                    st.download_button(label="Download updated Excel file", data=file, file_name=output_filepath)

if __name__ == '__main__':
    main()