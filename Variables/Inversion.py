"""
Variable 5: Inversion en Sponsored Products.

Tabla final: seller_id | name | invirtio (si/no) | total_invertido

- La inversion (campaignCharge) sale de Postgres (eiffel-ledger).
- Los sellers validos (Mid-Market + 90 dias de onboarding)
  sale de Redshift, igual que venta y CVR.
- Como son bases distintas, el cruce se hace en Python (merge).
"""

import pandas as pd
from db import run_query, run_query_pg
from config import HORIZONTE_DIARIO, DIAS_ONBOARDING

QUERY_SELLERS_VALIDOS = f"""
SELECT s.id AS seller_id, s.name
FROM eiffel_seller.seller s
LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON s.id = c.id_seller
WHERE s.created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
  AND c.tier = 'Mid-Market' AND publish = 1
"""

QUERY_INVERSION = f"""
SELECT
    i.seller_id,
    SUM(id.amount) AS total_invertido
FROM "eiffel-ledger".invoice i
INNER JOIN "eiffel-ledger".invoice_detail id ON i.id = id.invoice_id
WHERE id.type = 'campaignCharge'
  AND (i.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago')::date
      >= CURRENT_DATE - {HORIZONTE_DIARIO}
  AND (i.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago')::date
      <  CURRENT_DATE
GROUP BY i.seller_id
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, invirtio (si/no), total_invertido.

    Solo sellers validos (MM + 90 dias). Los que no invirtieron quedan
    con invirtio='no' y total_invertido=0.
    """

    sellers = run_query(QUERY_SELLERS_VALIDOS)
    inversion = run_query_pg(QUERY_INVERSION)

    df = sellers.merge(inversion, on="seller_id", how="left")

    df["invirtio"] = df["total_invertido"].notna().map({True: "si", False: "no"})
    df["total_invertido"] = df["total_invertido"].fillna(0)

    return df[["seller_id", "name", "invirtio", "total_invertido"]]


if __name__ == "__main__":
    df = calcular()
    print(f"Sellers validos (MM + 90 dias): {len(df)}")
    print(f"  de los cuales invirtieron: {(df['invirtio'] == 'si').sum()}")
    print(f"  no invirtieron: {(df['invirtio'] == 'no').sum()}")
    print(df.head(20))