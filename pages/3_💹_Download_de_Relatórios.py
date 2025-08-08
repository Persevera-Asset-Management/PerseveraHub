import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import requests
import gspread
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from persevera_tools.config.settings import Settings
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from time import sleep

st.set_page_config(
    page_title="Download de Relatórios | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Download de Relatórios")

if 'df' not in st.session_state:
    st.session_state.df = None

settings = Settings()

gc = gspread.api_key(settings.GS_API_KEY)
sh = gc.open_by_key("1f77qWQB0mpTbYDvtixm82YLeG9xgFkdets7SeDV68gU")

df = pd.DataFrame(sh.sheet1.get('A2:F200'))
df.columns = df.iloc[0]
df = df.iloc[1:]
df.set_index("code", inplace=True)
df.dropna(inplace=True)

st.dataframe(df['report_url'].rename("URL"))
btn_run = st.button("Baixar Relatórios")

if btn_run:
    with st.spinner("Configurando o navegador..."):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # driver = webdriver.Chrome(
        #     service=ChromeService(ChromeDriverManager().install()), options=options
        # )
        driver = webdriver.Chrome(
            service=Service(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=options
        )

    with st.spinner("Acessando o ComDinheiro..."):
        url = "https://www.comdinheiro.com.br/login"
        driver.get(url)
        driver.find_element(By.ID, "textUser").send_keys("persevera_asset")
        driver.find_element(By.ID, "textSenha").send_keys("ymr0pzr_xwa5wku5NMQ")
        driver.find_element(By.ID, "login").click()
        sleep(2)

    for index, row in df.iterrows():
        with st.spinner(f"Acessando o relatório {index}..."):
            url = row['report_url']
            driver.get(url)
            sleep(5)
        
            try:
                driver.find_element(By.ID, "fa fa-times").click()
            except:
                pass

        with st.spinner(f"Baixando o relatório {index}..."):
            driver.find_element(By.XPATH, '//*[@id="div_pdfV"]/a/button/span').click()

            while len(driver.window_handles) == 1:
                sleep(1)
            
            driver.switch_to.window(driver.window_handles[1])
            report_url = driver.current_url

            response = requests.get(report_url)
            with open(f"Persevera_{index}.pdf", "wb") as f:
                f.write(response.content)
        
        driver.switch_to.window(driver.window_handles[1])
        driver.close()
        driver.switch_to.window(driver.window_handles[0]) 
    
    driver.quit()
    st.success("Relatórios baixados com sucesso!")
    st.session_state.df = "done"

df = st.session_state.df
if df is not None:
    try:
        pass
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
