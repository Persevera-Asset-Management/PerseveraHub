import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


@st.cache_resource
def get_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )


st.title("Streamlit and Selenium Integration")
url = st.text_input("Enter a URL to scrape:", "http://example.com")
if st.button("Scrape"):
    driver = get_driver()
    driver.get(url)
    st.write("Page Title:", driver.title)
    st.code(driver.page_source)
