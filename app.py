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
from tqdm import tqdm

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

def fetch_content(url, retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            st.write(f"HTTP error occurred: {e}")
        st.write(f"Retrying... ({attempt + 1}/{retries})")
    return None

def extract_keywords_from_url(url, language_code):
    try:
        st.write(f"Fetching content from URL: {url}")
        html_content = fetch_content(url)
        if not html_content:
            st.write(f"Failed to fetch content from URL: {url}")
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        st.write("Processing HTML content...")

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()

        st.write("Extracting text from HTML...")
        text = ' '.
