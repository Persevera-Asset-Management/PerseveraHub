import tempfile

from pathlib import Path



import streamlit as st

from selenium.common.exceptions import WebDriverException



from persevera_tools.config.settings import Settings

from services.comdinheiro_reports_service import (
    build_reports_zip,
    download_comdinheiro_reports,
    get_report_period_label,
    get_reports_urls,
    validate_comdinheiro_credentials,
)

from utils.auth import check_authentication
from utils.selenium_driver import driver_diagnostics, is_deploy_env, validate_selenium_environment
from utils.ui import display_logo, load_css



st.set_page_config(

    page_title="Relatórios ComDinheiro | Persevera",

    page_icon="🔨",

    layout="wide",

)



display_logo()

load_css()

check_authentication()



st.title("Relatórios ComDinheiro")

st.caption(

    "Baixa os relatórios configurados no Fibery "

    "(`Inv-Asset Allocation/Relatórios Mandatos Exclusivos`) e disponibiliza um arquivo ZIP."

)



with st.sidebar:

    st.header("Parâmetros")

    show_diagnostics = st.toggle("Exibir diagnóstico do Selenium", value=False)



if show_diagnostics:

    with st.expander("Diagnóstico do ambiente Selenium", expanded=True):

        for key, value in driver_diagnostics().items():

            st.write(f"**{key}:** {value or 'não encontrado'}")

        if is_deploy_env():

            st.info(

                "No servidor, o navegador roda em modo visível via Xvfb "

                "(necessário para o ComDinheiro gerar os PDFs)."

            )



try:

    validate_comdinheiro_credentials(Settings())

    credentials_ok = True

except ValueError as exc:

    credentials_ok = False

    credentials_error = str(exc)



try:

    with st.spinner("Carregando relatórios do Fibery..."):

        reports_df = get_reports_urls()

except Exception as exc:

    st.error(f"Não foi possível carregar os relatórios do Fibery: {exc}")

    st.stop()



if not credentials_ok:

    st.error(credentials_error)

    st.stop()



if reports_df.empty:

    st.warning("Nenhum relatório foi encontrado no Fibery.")

    st.stop()



period_label = get_report_period_label(reports_df)

cycle_label = reports_df["Chave Ciclo"].iloc[0]



st.subheader("Relatórios configurados")

st.write(f"Ciclo de referência: **{cycle_label}** (`{period_label}`)")

st.write(f"Quantidade de relatórios: **{len(reports_df)}**")

st.dataframe(

    reports_df,

    use_container_width=True,

    hide_index=True,

)



if st.button("Baixar relatórios", type="primary", use_container_width=True):

    progress_bar = st.progress(0.0, text="Preparando download...")

    status = st.status("Executando download dos relatórios...", expanded=True)



    def on_progress(message: str, fraction: float | None = None) -> None:

        status.write(message)

        if fraction is not None:

            progress_bar.progress(min(max(fraction, 0.0), 1.0), text=message)



    try:

        validate_selenium_environment()



        with tempfile.TemporaryDirectory(prefix="comdinheiro_reports_") as temp_dir:

            save_path, downloaded_files = download_comdinheiro_reports(

                reports_df=reports_df,

                save_path=Path(temp_dir) / period_label,

                callback=on_progress,

            )



            if not downloaded_files:

                status.update(label="Nenhum PDF foi baixado.", state="error")

                st.warning("O processo terminou sem arquivos PDF.")

            else:

                zip_bytes = build_reports_zip(save_path)

                status.update(

                    label=f"Download concluído ({len(downloaded_files)} PDFs).",

                    state="complete",

                )

                progress_bar.progress(1.0, text="Download concluído.")



                st.session_state["comdinheiro_reports_zip"] = zip_bytes

                st.session_state["comdinheiro_reports_zip_name"] = f"Relatorios_ComDinheiro_{period_label}.zip"

                st.session_state["comdinheiro_reports_files"] = [path.name for path in downloaded_files]



                if len(downloaded_files) < len(reports_df):

                    st.warning(

                        f"Foram baixados {len(downloaded_files)} de {len(reports_df)} relatórios configurados."

                    )

    except WebDriverException as exc:

        status.update(label="Falha ao iniciar o navegador.", state="error")

        st.error(

            "Não foi possível iniciar o Chrome/Chromium. "

            "No deploy (Digital Ocean), confira o Aptfile, o build (`bin/post_compile`) "

            "e o Run Command (`. ./setup.sh && streamlit ...`). "

            "No Windows, instale o Google Chrome ou execute "

            "`powershell -ExecutionPolicy Bypass -File scripts/install_chrome_for_testing.ps1`."

        )

        st.exception(exc)

    except Exception as exc:

        status.update(label="Erro durante o download.", state="error")

        st.error(f"Ocorreu um erro ao baixar os relatórios: {exc}")



zip_bytes = st.session_state.get("comdinheiro_reports_zip")

zip_name = st.session_state.get("comdinheiro_reports_zip_name")

downloaded_names = st.session_state.get("comdinheiro_reports_files", [])



if zip_bytes and zip_name:

    st.subheader("Arquivos disponíveis")

    for filename in downloaded_names:

        st.write(f"- {filename}")



    st.download_button(

        label="Baixar ZIP dos relatórios",

        data=zip_bytes,

        file_name=zip_name,

        mime="application/zip",

        type="primary",

        use_container_width=True,

    )

