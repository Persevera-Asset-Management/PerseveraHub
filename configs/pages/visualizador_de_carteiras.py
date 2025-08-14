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

CODIGOS_CARTEIRAS = get_carteiras()

df = read_fibery(
    table_name="Ops-InstFin-XP/Snapshot Posição na XP",
    include_fibery_fields=False
)