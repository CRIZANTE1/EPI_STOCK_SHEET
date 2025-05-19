from dotenv import load_dotenv
import os
import google.generativeai as genai
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_api():
    try:
        api_key = None
        try:
            api_key = st.secrets["general"]["GOOGLE_API_KEY"]
            logging.info("API key loaded from Streamlit secrets.")
        except (KeyError, TypeError, AttributeError):
            logging.info("API key not found in Streamlit secrets, trying environment variables.")
        if not api_key:
            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                logging.info("API key loaded from .env file.")
        if not api_key:
            error_msg = "Google API key not found. Please set the GOOGLE_API_KEY environment variable or in Streamlit secrets."
            logging.error(error_msg)
            st.error(error_msg)
            return None
        genai.configure(api_key=api_key)
        logging.info("API loaded successfully.")
        return genai

    except Exception as e:
        error_msg = f"Error loading API: {str(e)}"
        logging.exception(error_msg)
        st.error(error_msg)
        return None
