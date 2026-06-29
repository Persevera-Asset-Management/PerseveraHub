from services.position_service import FILTER_OUT_CARTEIRA_STATES, load_active_carteiras_adm

FILTER_OUT_STATES = FILTER_OUT_CARTEIRA_STATES


def get_carteiras_adm():
    return load_active_carteiras_adm()


CODIGOS_CARTEIRAS_ADM = get_carteiras_adm()
