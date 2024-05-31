import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from translate import Translator as Translate
import nltk
from nltk.corpus import wordnet

nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('stopwords', quiet=True)

country_language_mapping = {
    'CZ': 'czech',  # Czech Republic
    'DE': 'german',  # Germany
    'DK': 'danish',  # Denmark
    'ES': 'spanish',  # Spain
    'FI': 'finnish',  # Finland
    'FR': 'french',  # France
    'GR': 'greek',  # Greece
    'IT': 'italian',  # Italy
    'NL': 'dutch',  # Netherlands
    'NO': 'norwegian',  # Norway
    'PL': 'polish',  # Poland
    'PT': 'portuguese',  # Portugal
    'SE': 'swedish',  # Sweden
    'SK': 'slovak',  # Slovakia
    'UK': 'english',  # United Kingdom
    'ES-MX': 'spanish',  # Spanish (Mexico)
}

def get_google_sheets_credentials():
    google_credentials = st.secrets['google_credentials']['secret']
    secret = json.loads(google_credentials)
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(secret, scope)
    return credentials

def translate_text(text, target_language):
    try:
        translator = Translate(to_lang=target_language)
        translation = translator.translate(text)
        st.write(f"Debug: Translated '{text}' to '{translation}'")  # Debug line
        return translation.strip()
    except Exception as e:
        st.write(f"Error translating text '{text}': {e}")
        return text

def suggest_words(word, language_code):
    suggestions = set()

    try:
        if language_code != 'english':
            translator = Translate(to_lang='en')
            word_en = translator.translate(word)
            st.write(f"Debug: Translated word to English: '{word}' -> '{word_en}'")  # Debug line
        else:
            word_en = word

        synsets = wordnet.synsets(word_en)
        for synset in synsets:
            for lemma in synset.lemmas():
                suggestions.add(lemma.name())

        if language_code != 'english':
            suggestions_translated = set()
            translator = Translate(to_lang=language_code)
            for suggestion in suggestions:
                try:
                    suggestion_translated = translator.translate(suggestion)
                    st.write(f"Debug: Translated suggestion to {language_code}: '{suggestion}' -> '{suggestion_translated}'")  # Debug line
                    suggestions_translated.add(suggestion_translated)
                except Exception as e:
                    st.write(f"Error translating suggestion '{suggestion}': {e}")
            suggestions = suggestions_translated
    except Exception as e:
        st.write(f"Error processing word '{word}': {e}")
        suggestions = []

    return list(suggestions)

def search_keywords(dataframe, country, creds, selected_client):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    found_keyword_column = []
    translation_column = []
    suggestion2_column = []
    client_column = []

    language_code = country_language_mapping.get(country, 'english')  # Determine language code
    st.write(f"Using language code: {language_code}")  # Debug line

    for keyword in dataframe['Keyword']:
        found = False
        clients_found = set()
        for line in lines:
            if selected_client == "All Clients" or line["Client"].lower() == selected_client.lower():
                if line["Target Country"].upper() == country.upper() and keyword.lower() in line["Translation"].lower():
                    found_keyword_column.append(line["Keyword"])
                    translation_column.append("N/A")
                    suggestion2_column.append("N/A")
                    clients_found.add(line["Client"])
                    found = True

        if not found:
            translated_keyword = translate_text(keyword, language_code)
            st.write(f"Translated '{keyword}' to '{translated_keyword}'")  # Debug line
            suggestions = suggest_words(translated_keyword, language_code)
            st.write(f"Suggestions for '{translated_keyword}': {suggestions}")  # Debug line
            found_keyword_column.append("Keyword not saved in the database yet")
            translation_column.append(translated_keyword)
            suggestion2_column.append(", ".join(suggestions) if suggestions else "N/A")

        if clients_found:
            client_column.append(", ".join(clients_found))
        else:
            client_column.append("N/A")

    dataframe['Found Keyword'] = found_keyword_column
    dataframe['Suggestion1'] = translation_column
    dataframe['Suggestion2'] = suggestion2_column
    dataframe['Client'] = client_column

    return dataframe

def get_client_list(creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()
    clients = set()
    for line in lines:
        clients.add(line["Client"])
    st.write(f"Debug: Retrieved clients: {clients}")  # Debug line
    return ["All Clients"] + sorted(clients)

def main():
    st.title('Keyword Checker and Suggestion Tool')

    st.write("Upload an Excel file or paste a word, choose the country, and get keyword translations.")

    creds = get_google_sheets_credentials()
    clients = get_client_list(creds)

    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    word_input = st.text_input("Or enter a word")
    country = st.selectbox("Select Country", options=list(country_language_mapping.keys()))
    selected_client = st.selectbox("Select Client", options=clients)

    if st.button("Process"):
        language_code = country_language_mapping.get(country, 'english')

        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write("File uploaded successfully!")
            updated_df = search_keywords(df, country, creds, selected_client)
            st.write("Keyword results:")
            st.dataframe(updated_df)

        elif word_input:
            df = pd.DataFrame({'Keyword': [word_input]})
            updated_df = search_keywords(df, country, creds, selected_client)
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
