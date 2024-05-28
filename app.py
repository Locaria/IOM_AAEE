import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from translate import Translator
import spacy

nlp = spacy.load(language_code)  

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
    translator = Translator()
    translation = translator.translate(text, dest=target_language)
    return translation.text

def suggest_words(text):
    # Processar o texto traduzido com spaCy
    doc = nlp(text)

    # Obter palavras semelhantes ou sinônimos
    suggestions = [token.text for token in doc if token.is_alpha and not token.is_stop]
    return suggestions

def search_keywords(dataframe, country, creds):
    language_code = country_language_mapping.get(country, 'en')
    nlp = spacy.load(language_code)

    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    found_keyword_column = []
    translation_column = []
    suggestion2_column = []

    for keyword in dataframe['Keyword']:
        found = False
        for line in lines:
            if line["Target Country"].upper() == country.upper() and keyword.lower() in line["Translation"].lower():
                found_keyword_column.append(line["Keyword"])
                translation_column.append("N/A")
                suggestion2_column.append("N/A")
                found = True
                break
        if not found:
            translated_keyword = translate_text(keyword, language_code)
            suggestions = suggest_words(translated_keyword)
            found_keyword_column.append("Keyword not saved in the database yet")
            translation_column.append(translated_keyword)
            suggestion2_column.append(", ".join(suggestions))

    dataframe['Found Keyword'] = found_keyword_column
    dataframe['Suggestion1'] = translation_column
    dataframe['Suggestion2'] = suggestion2_column

    return dataframe

def main():
    st.title('Keyword Checker and Translation Tool')

    st.write("Upload an Excel file, choose the country, and get keyword translations.")

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