from persevera_tools.db.fibery import read_fibery


def get_carteiras_adm():
    df = read_fibery(
        table_name="Estr-CartAdm/Carteira Administrada",
        include_fibery_fields=False
    )
    df = df[["Name", "Data Início Gestão", "Data Fim Gestão"]]
    df = df.dropna(subset=["Data Início Gestão"])
    df = df[df["Data Fim Gestão"].isna()]
    df.drop(columns=["Data Fim Gestão"], inplace=True)
    df = df.rename(columns={"Name": "Código", "Data Início Gestão": "Data Início Gestão"})
    df["Código"] = df["Código"].str.split("-").str[0]
    df.set_index("Código", inplace=True)
    return df.to_dict('index')

CODIGOS_CARTEIRAS_ADM = get_carteiras_adm()