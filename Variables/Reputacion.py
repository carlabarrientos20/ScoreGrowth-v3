"""
Información a cruzar para ver quién puede invertir, y quién no, en el proyecto de Growth Score.
Variables: Reputación del seller, esta debe ser Medio y destacado para que pueda invertir 
"""

import pandas as pd
from db import run_query
from config import DIAS_ONBOARDING

QUERY_REPUTACION = f"""

WITH sellers_validos AS (
    SELECT id AS seller_id, name, c.tier
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),

Reputacion AS (
    SELECT
        r.seller_id,
        r.name,
        r.categoria_reputacion
    FROM cencosud_chile_txd_reporter.reputation_seller_kpis_mkp r
    INNER JOIN sellers_validos s
        ON r.seller_id = s.seller_id
    GROUP BY r.seller_id, r.name, r.categoria_reputacion
)

Select rep.seller_id, rep.name, rep.categoria_reputacion
from Reputacion rep

"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, categoria_reputacion.

    Clave: seller_id (un seller aparece en una fila).
    """
    return run_query(QUERY_REPUTACION)


if __name__ == "__main__":
    df = calcular()
    df.to_csv("reputacion_seller.csv", index=False)
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"Cantidad de sellers con reputación Destacado: {len(df[df['categoria_reputacion'].isin(['Destacado'])])}")
    print(f"Cantidad de sellers con reputación Buena: {len(df[df['categoria_reputacion'].isin(['Bueno'])])}")
    print(f"Cantidad de sellers con reputación Medio: {len(df[df['categoria_reputacion'].isin(['Medio'])])}")
    print(f"Cantidad de sellers con reputación Bajo: {len(df[df['categoria_reputacion'].isin(['Bajo'])])}")
    print(f"Cantidad de sellers con reputación Plan Growth: {len(df[df['categoria_reputacion'].isin(['Plan Growth'])])}")
    print(df.head(100))