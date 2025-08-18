from persevera_tools.db.fibery import read_fibery

def get_carteiras():
    df = read_fibery(
        table_name="Ops-Cadastro/Parte Legal",
        include_fibery_fields=False
    )
    df = df[
        (df["Ops-Cadastro/Is CPF?"] == True) &
        (df["Ops-Cadastro/Código (Acrônimo)"].notna()) &
        (df["Ops-Cadastro/Código (Acrônimo)"].str.len() == 4)
    ]
    return sorted(df["Ops-Cadastro/Código (Acrônimo)"].tolist())

def get_carteiras_adm():
    df = read_fibery(
        table_name="Ops-CartAdm/Carteira Administrada",
        include_fibery_fields=False
    )
    df = df[["Ops-CartAdm/Name", "Ops-CartAdm/Data Início Gestão"]]
    df = df.dropna()
    df = df.rename(columns={"Ops-CartAdm/Name": "Código", "Ops-CartAdm/Data Início Gestão": "Data Início Gestão"})
    df["Código"] = df["Código"].str.split("-").str[0]
    df.set_index("Código", inplace=True)
    return df.to_dict('index')

CODIGOS_CARTEIRAS_ADM = get_carteiras_adm()