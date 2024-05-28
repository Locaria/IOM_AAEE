import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pytrends.request import TrendReq
import json
import time
from pytrends.exceptions import TooManyRequestsError
import requests

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
    google_credentials = st.secrets['google_credentials']['secret']
    secret = json.loads(google_credentials)
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(secret, scope)
    return credentials

def get_keyword_suggestions(keyword, language_code, country_code):
    pytrends = TrendReq(hl=language_code, tz=360)
    attempts = 0
    max_attempts = 5
    wait_time = 2  # Initial wait time in seconds

    while attempts < max_attempts:
        try:
            pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo=country_code, gprop='')
            data = pytrends.related_queries()
            if data[keyword]['top'] is not None:
                return data[keyword]['top']['query'].tolist()
            else:
                return ["No suggestion available"]
        except TooManyRequestsError:
            attempts += 1
            time.sleep(wait_time)
            wait_time *= 2  # Exponential backoff

    return ["No suggestion available"]

def get_serpapi_suggestions(keyword, language_code, country_code):
    api_key = st.secrets["serpapi"]["api_key"]
    endpoint = "https://serpapi.com/search"
    
    params = {
        "engine": "google",
        "q": keyword,
        "hl": language_code,
        "gl": country_code,
        "api_key": api_key
    }
    
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    
    suggestions = response.json()
    if "related_questions" in suggestions:
        return [item["question"] for item in suggestions["related_questions"]]
    elif "related_searches" in suggestions:
        return [item["query"] for item in suggestions["related_searches"]]
    else:
        return ["No suggestion available"]

def search_keywords(dataframe, country, creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    keyword_column = []
    suggestion_column = []

    language_code = country_language_mapping.get(country, 'en-US')  # Determine language_code
    st.write(f"Using language code: {language_code}")  # Debugging line to check language code

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
            # First try Google Trends for suggestions
            suggestions = get_google_trends_suggestions(keyword, language_code, country)
            if "No suggestion available" in suggestions:
                # If no suggestions from Google Trends, try SerpApi
                suggestions = get_serpapi_suggestions(keyword, language_code, country)
            
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
                spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
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