import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from translate import Translator as Translate
import nltk
from nltk.corpus import wordnet
import requests
from bs4 import BeautifulSoup

# Baixar os dados necessários do NLTK de forma silenciosa
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords

# Mapeamento dos códigos de país para seus respectivos códigos de idioma
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
    translator = Translate(to_lang=target_language)
    translation = translator.translate(text)
    return translation

def suggest_words(word, language_code):
    suggestions = set()

    try:
        # Se a língua não for inglês, traduzir para inglês
        if language_code != 'english':
            translator = Translate(to_lang='en')
            word_en = translator.translate(word)
        else:
            word_en = word

        synsets = wordnet.synsets(word_en)
        for synset in synsets:
            for lemma in synset.lemmas():
                suggestions.add(lemma.name())

        # Traduzir de volta para o idioma original, se necessário
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

def extract_keywords_from_url(url, language_code):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = ' '.join(soup.stripped_strings)
        words = text.split()
        
        # Carregar as stop words com base no código do idioma
        if language_code in stopwords.fileids():
            stop_words = set(stopwords.words(language_code))
        else:
            stop_words = set(stopwords.words('english'))  # Usar inglês como padrão se o idioma não for encontrado

        keywords = [word for word in words if word.lower() not in stop_words and word.isalpha()]
        return keywords
    except Exception as e:
        st.write(f"Error extracting keywords from URL '{url}': {e}")
        return []

def main():
    st.title('Keyword Checker and Translation Tool')

    st.write("Upload an Excel file, paste a word or a URL, choose the country, and get keyword translations.")

    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    word_input = st.text_input("Or enter a word")
    url_input = st.text_input("Or enter a URL")
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

        elif url_input:
            keywords = extract_keywords_from_url(url_input, language_code)
            df = pd.DataFrame({'Keyword': keywords})
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