import streamlit as st
import streamlit_highcharts as hct
import streamlit.components.v1 as components
import pandas as pd
import json
import markdown
from datetime import datetime, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication
from utils.charts import create_highcharts_options

st.set_page_config(
    page_title="Apresentação Mensal | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Apresentação Mensal")

# ----------------------------------------------------------------------
# Controles do Slideshow na Sidebar
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Parâmetros")

    selected_carteira = st.selectbox("Carteira selecionada", options=CODIGOS_CARTEIRAS_ADM.keys())
    
    slideshow_height = st.slider(
        "Altura do contêiner (pixels)", 
        min_value=300, 
        max_value=1200, 
        value=600, 
        step=50
    )
    
    st.header("Comentário de Mercado")
    markdown_input = st.text_area(
        "Insira o conteúdo em Markdown para o segundo slide:",
        value="### Recados Importantes\n\n- O **relatório mensal** deve ser finalizado até sexta-feira.\n- A reunião de estratégia foi movida para as 10h.",
        height=250
    )

# ----------------------------------------------------------------------
# Exemplo de slideshow usando `streamlit.components.v1 as components`
# ----------------------------------------------------------------------
st.subheader(selected_carteira)

# --- 1. Preparar conteúdo dinâmico em Python ---

# Tabela de exemplo com Pandas
df_table = pd.DataFrame({
    'Mês': ['Janeiro', 'Fevereiro', 'Março'],
    'Vendas (R$)': [1200, 1550, 980]
})
table_html = df_table.to_html(index=False, classes='styled-table', justify='center')

# Gráfico interativo com Highcharts
df_chart = pd.DataFrame({
    'data': pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01']),
    'valor': [10, 40, 25, 60]
}).set_index('data')

highcharts_options = create_highcharts_options(
    data=df_chart,
    y_column='valor',
    chart_type='spline',
    title='Performance Interativa',
    y_axis_title='Valor',
    series_name='Performance'
)
# Converter para uma string JSON segura para HTML
highcharts_options_json = json.dumps(highcharts_options)

# Converter Markdown para HTML
markdown_slide_content = markdown.markdown(markdown_input)


# --- 2. Definir o HTML do slideshow ---

html_code = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://code.highcharts.com/highcharts.js"></script>
<style>
* {{box-sizing: border-box;}}
body {{font-family: Verdana, sans-serif; margin:0;}}
img {{vertical-align: middle;}}

/* Slideshow container */
.slideshow-container {{
  max-width: 1000px;
  height: {slideshow_height}px;
  position: relative;
  margin: auto;
  background-color: #f1f1f1;
  border-radius: 8px;
}}

/* Cada slide individual */
.mySlides {{
    display: none; /* Controlado por JS, que mudará para 'flex' */
    width: 100%;
    height: 100%;
    padding: 20px;
    overflow-y: auto;
    /* Centraliza o conteúdo DENTRO do slide */
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}

/* Estilos da tabela */
.styled-table {{
    width: 80%;
    margin: 20px auto;
    border-collapse: collapse;
    font-size: 18px;
    text-align: left;
    color: #333;
}}
.styled-table th, .styled-table td {{
    padding: 12px 15px;
    border: 1px solid #ddd;
}}
.styled-table thead tr {{
    background-color: #009879;
    color: #ffffff;
    text-align: left;
}}

/* Estilos para o slide de Markdown */
.markdown-slide {{
    text-align: left;
    padding: 20px 50px;
    color: #333;
    justify-content: flex-start; /* Alinha o conteúdo ao topo */
}}
.markdown-slide h3 {{
    color: #005f50;
}}

/* Next & previous buttons */
.prev, .next {{
  cursor: pointer;
  position: absolute;
  top: 50%;
  transform: translateY(-50%); /* Centraliza verticalmente de forma robusta */
  width: auto;
  padding: 16px;
  color: white;
  font-weight: bold;
  font-size: 18px;
  transition: 0.6s ease;
  border-radius: 0 3px 3px 0;
  user-select: none;
  background-color: rgba(0,0,0,0.5);
  z-index: 10;
}}

/* Position the "next button" to the right */
.next {{
  right: 0;
  border-radius: 3px 0 0 3px;
}}

.prev:hover, .next:hover {{
  background-color: rgba(0,0,0,0.8);
}}

/* Caption text */
.text {{
  color: #f2f2f2;
  font-size: 15px;
  padding: 8px 12px;
  position: absolute;
  bottom: 8px;
  width: 100%;
  text-align: center;
  background-color: rgba(0,0,0,0.3);
}}

/* Number text (1/4 etc) */
.numbertext {{
  color: #333;
  font-size: 12px;
  padding: 8px 12px;
  position: absolute;
  top: 0;
  left: 0;
}}

/* The dots/bullets/indicators */
.dot {{
  cursor: pointer;
  height: 15px;
  width: 15px;
  margin: 0 2px;
  background-color: #bbb;
  border-radius: 50%;
  display: inline-block;
  transition: background-color 0.6s ease;
}}

.active, .dot:hover {{
  background-color: #717171;
}}

/* Fading animation */
.fade {{
  animation-name: fade;
  animation-duration: 1.5s;
}}

@keyframes fade {{
  from {{opacity: .4}}
  to {{opacity: 1}}
}}
</style>
</head>
<body>
<div class="slideshow-container">

<div class="mySlides fade">
  <div class="numbertext">1 / 4</div>
  <h2 style="color: #333;">Slide de Título</h2>
  <p style="color: #555;">Este é o primeiro slide da apresentação.</p>
</div>

<div class="mySlides fade markdown-slide" style="background-color: white;">
  <div class="numbertext">2 / 4</div>
  {markdown_slide_content}
</div>

<div class="mySlides fade" style="background-color: white;">
  <div class="numbertext">3 / 4</div>
  <h2 style="color: #333;">Tabela de Dados</h2>
  {table_html}
</div>

<div id="slide-highchart" class="mySlides fade" style="background-color: white;">
  <div class="numbertext">4 / 4</div>
  <h2 style="color: #333;">Gráfico Interativo</h2>
  <div id="highchart-container" style="height: 90%; width: 100%;"></div>
</div>

<a class="prev" onclick="plusSlides(-1)">&#10094;</a>
<a class="next" onclick="plusSlides(1)">&#10095;</a>

</div>
<br>

<div style="text-align:center">
  <span class="dot" onclick="currentSlide(1)"></span>
  <span class="dot" onclick="currentSlide(2)"></span>
  <span class="dot" onclick="currentSlide(3)"></span>
  <span class="dot" onclick="currentSlide(4)"></span>
</div>

<script>
let slideIndex = 1;
const highchartOptions = {highcharts_options_json};

function renderHighchart() {{
    const container = document.getElementById('highchart-container');
    if (container && !container.hasChildNodes()) {{
        Highcharts.chart(container, highchartOptions);
    }}
}}

function showSlides(n) {{
  let i;
  let slides = document.getElementsByClassName("mySlides");
  let dots = document.getElementsByClassName("dot");
  
  if (n > slides.length) {{slideIndex = 1}}
  if (n < 1) {{slideIndex = slides.length}}

  for (i = 0; i < slides.length; i++) {{
    slides[i].style.display = "none";
  }}
  for (i = 0; i < dots.length; i++) {{
    dots[i].className = dots[i].className.replace(" active", "");
  }}
  
  if (slides[slideIndex-1]) {{
      slides[slideIndex-1].style.display = "flex";
  }}
  if (dots[slideIndex-1]) {{
      dots[slideIndex-1].className += " active";
  }}

  if (slides[slideIndex-1] && slides[slideIndex-1].id === "slide-highchart") {{
      renderHighchart();
  }}
}}

function plusSlides(n) {{
  showSlides(slideIndex += n);
}}

function currentSlide(n) {{
  showSlides(slideIndex = n);
}}

showSlides(slideIndex);
</script>

</body>
</html>
"""

# O componente agora usa o body do HTML, a altura é controlada pelo CSS interno
components.html(html_code, height=slideshow_height + 40) # Adiciona espaço para os dots

