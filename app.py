import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from translate import Translator as Translate
import nltk
from nltk.corpus import wordnet
import tempfile

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
    st.write("Using language code: " + language_code)

    suggestions_found = False

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
                    break

        if not found:
            translated_keyword = translate_text(keyword, language_code)
            suggestions = suggest_words(translated_keyword, language_code)
            found_keyword_column.append("Keyword not saved in the database yet")
            translation_column.append(translated_keyword)
            suggestion2_column.append(", ".join(suggestions) if suggestions else "N/A")
            if translated_keyword != "N/A" or any(suggestion != "N/A" for suggestion in suggestions):
                suggestions_found = True

        client_column.append(", ".join(clients_found) if clients_found else "N/A")

    # Check lengths of the lists
    assert len(found_keyword_column) == len(dataframe), "Mismatch in length of 'Found Keyword' column"
    assert len(translation_column) == len(dataframe), "Mismatch in length of 'Suggestion1' column"
    assert len(suggestion2_column) == len(dataframe), "Mismatch in length of 'Suggestion2' column"
    assert len(client_column) == len(dataframe), "Mismatch in length of 'Client' column"

    dataframe['Found Keyword'] = found_keyword_column
    dataframe['Suggestion1'] = translation_column
    dataframe['Suggestion2'] = suggestion2_column
    dataframe['Client'] = client_column

    return dataframe, suggestions_found

def get_client_list(creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()
    clients = set()
    for line in lines:
        clients.add(line["Client"])
    return ["All Clients"] + sorted(clients)

def update_google_sheet_with_suggestions(creds, updated_df, client_name, country):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1

    st.write("Updating Google Sheet...")  # Debugging statement

    for _, row in updated_df.iterrows():
        if row['Suggestion1'] != 'N/A':
            new_row = [
                country,              # Target Country
                row['Suggestion1'],   # Keyword (Suggestion1)
                row['Keyword'],       # Translation (Original keyword)
                "",                   # Main Topic (Blank)
                client_name           # Client
            ]
            st.write(f"Appending row for Suggestion1: {new_row}")  # Debugging statement
            sheet.append_row(new_row)

        if row['Suggestion2'] != 'N/A':
            new_row = [
                country,              # Target Country
                row['Suggestion2'],   # Keyword (Suggestion2)
                row['Keyword'],       # Translation (Original keyword)
                "",                   # Main Topic (Blank)
                client_name           # Client
            ]
            st.write(f"Appending row for Suggestion2: {new_row}")  # Debugging statement
            sheet.append_row(new_row)

    st.write("Google Sheet update complete.")  # Debugging statement

def main():
    st.title('Keyword Checker and Suggestion Tool')

    st.write("Upload an Excel file or paste a word, choose the country, and get keyword translations.")

    creds = get_google_sheets_credentials()
    clients = get_client_list(creds)

    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    word_input = st.text_input("Or enter a word")
    country = st.selectbox("Select Country", options=list(country_language_mapping.keys()))
    selected_client = st.selectbox("Select Client", options=clients)

    suggestions_found = False
    if st.button("Process"):
        language_code = country_language_mapping.get(country, 'english')

        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write("File uploaded successfully!")
            updated_df, suggestions_found = search_keywords(df, country, creds, selected_client)
            st.write("Keyword results:")
            st.dataframe(updated_df)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                df.to_excel(tmp.name, index=False)
                st.download_button(
                    label="Download updated Excel file",
                    data=tmp.name,
                    file_name='updated_keywords.xlsx'
                )

            st.success("Updated keywords have been added to the Excel file and it is ready for download.")
            st.write(f"Suggestions found: {suggestions_found}")

        elif word_input:
            df = pd.DataFrame({'Keyword': [word_input]})
            updated_df, suggestions_found = search_keywords(df, country, creds, selected_client)
            st.write("Keyword results:")
            st.dataframe(updated_df)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                df.to_excel(tmp.name, index=False)
                st.download_button(
                    label="Download updated Excel file",
                    data=tmp.name,
                    file_name='updated_keywords.xlsx'
                )

            st.success("Updated keywords have been added to the Excel file and it is ready for download.")
            st.write(f"Suggestions found: {suggestions_found}")

        if suggestions_found:
            if selected_client == "All Clients":
                client_name = st.text_input("Enter Client Name to update G-Sheet:")
            else:
                client_name = selected_client

            if st.button("Confirm and Add Keyword Suggestions to G-Sheet"):
                if selected_client == "All Clients" and not client_name:
                    st.error("Please enter the client name.")
                else:
                    update_google_sheet_with_suggestions(creds, updated_df, client_name, country)
                    st.success("Keyword suggestions have been added to the Google Sheet.")

if __name__ == '__main__':
    main()