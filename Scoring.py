"""
Scoring.py - Calculo del score ponderado

Todas las variables entran como un valor de 0 a 100 (percentil dentro de su
dureza, salvo Inversion que es 0 o 100) y se ponderan con los pesos de abajo.
"""

PESO_VENTA = 0.3
PESO_DISPONIBILIDAD_SKU = 0.2
PESO_VOLUMEN_SKU = 0.1
PESO_RECURRENCIA = 0.15
PESO_CVR = 0.15
PESO_INVERSION = 0.1
VALOR_NEUTRO = 50   # ni premio ni castigo: sellers sin CVR calculable y sellers en "Primera venta"


def calcular_score(df):

    print("=== CALCULANDO SCORE ===")

    df["Inversion_binaria"] = df["invirtio"].map({"si": 100, "no": 0})

    # Frecuencia: percentil de dias con venta dentro de su dureza.
    # "Primera venta" no tiene historia suficiente para medir frecuencia -> neutro.
    df["recurrencia_score"] = df["percentil_recurrencia"].fillna(0)
    df.loc[df["estado_seller"] == "Primera venta", "recurrencia_score"] = VALOR_NEUTRO

    df["score"] = (
        df["venta_percentil"].fillna(0) * PESO_VENTA +
        df["percentil_stock"].fillna(0) * PESO_DISPONIBILIDAD_SKU +
        df["percentil_volumen_stock"].fillna(0) * PESO_VOLUMEN_SKU +
        df["recurrencia_score"] * PESO_RECURRENCIA +
        df["percentil_cvr"].fillna(VALOR_NEUTRO) * PESO_CVR +
        df["Inversion_binaria"].fillna(0) * PESO_INVERSION
    )
    print("=== SCORE CALCULADO ===")
    return df
