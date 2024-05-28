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
    'CZ': 'czech',  # República Tcheca
    'DE': 'german',  # Alemanha
    'DK': 'danish',  # Dinamarca
    'ES': 'spanish',  # Espanha
    'FI': 'finnish',  # Finlândia
    'FR': 'french',  # França
    'GR': 'greek',  # Grécia
    'IT': 'italian',  # Itália
    'NL': 'dutch',  # Países Baixos
    'NO': 'norwegian',  # Noruega
    'PL': 'polish',  # Polônia
    'PT': 'portuguese',  # Portugal
    'SE': 'swedish',  # Suécia
    'SK': 'slovak',  # Eslováquia
    'UK': 'english',  # Reino Unido
    'ES-MX': 'spanish',  # Espanhol (México)
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
        st.write(f"Debug: Translated '{text}' to '{translation}'")  # Linha de depuração
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
            st.write(f"Debug: Translated word to English: '{word}' -> '{word_en}'")  # Linha de depuração
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
                    st.write(f"Debug: Translated suggestion to {language_code}: '{suggestion}' -> '{suggestion_translated}'")  # Linha de depuração
                    suggestions_translated.add(suggestion_translated)
                except Exception as e:
                    st.write(f"Error translating suggestion '{suggestion}': {e}")
            suggestions = suggestions_translated
    except Exception as e:
        st.write(f"Error processing word '{word}': {e}")
        suggestions = []

    return list(suggestions)

def search_keywords(dataframe, country, creds):
    client = gspread.authorize(creds)
    spreadsheet_id = '1fkzvhb7al-GFajtjRRy3b93vCDdlARBmCTGDrxm0KVY'
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet = spreadsheet.sheet1
    lines = sheet.get_all_records()

    found_keyword_column = []
    translation_column = []
    suggestion2_column = []

    language_code = country_language_mapping.get(country, 'english')  # Determinar o código do idioma
    st.write(f"Using language code: {language_code}")  # Linha de depuração para verificar o código do idioma

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
            st.write(f"Translated '{keyword}' to '{translated_keyword}'")  # Linha de depuração
            suggestions = suggest_words(translated_keyword, language_code)
            st.write(f"Suggestions for '{translated_keyword}': {suggestions}")  # Linha de depuração
            found_keyword_column.append("Keyword not saved in the database yet")
            translation_column.append(translated_keyword)
            suggestion2_column.append(", ".join(suggestions) if suggestions else "N/A")

    dataframe['Found Keyword'] = found_keyword_column
    dataframe['Suggestion1'] = translation_column
    dataframe['Suggestion2'] = suggestion2_column

    return dataframe

def main():
    st.title('Keyword Checker and Suggestion Tool')

    st.write("Upload an Excel file or paste a word, choose the country, and get keyword translations.")

    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    word_input = st.text_input("Or enter a word")
    country = st.selectbox("Select Country", options=list(country_language_mapping.keys()))

    if st.button("Process"):
        creds = get_google_sheets_credentials()
        language_code = country_language_mapping.get(country, 'english')

        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write("File uploaded successfully!")
            updated_df = search_keywords(df, country, creds)
            st.write("Keyword results:")
            st.dataframe(updated_df)

        elif word_input:
            df = pd.DataFrame({'Keyword': [word_input]})
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