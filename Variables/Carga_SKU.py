"""
Variable 3 y 6: Catalogo (disponibilidad + volumen).

"""

import pandas as pd
from db import run_query
from config import TABLA_SELLERS, DUROS, BLANDOS, DIAS_ONBOARDING

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

TABLA_CATALOGO = "cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas"

QUERY_PRODUCTOS = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
cant_sku_creados AS (
    SELECT
        sv.seller_id,
        CASE
            WHEN cat.division IN ({_duros_sql})   THEN 'duros'
            WHEN cat.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT cat.sku_marketplace) AS sku_creados
    FROM sellers_validos sv
    LEFT JOIN cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas cat ON cat.seller_id = sv.seller_id
    GROUP BY sv.seller_id, division_db
),
sku_con_stock AS (
    SELECT
        cat.seller_id,
        CASE
            WHEN cat.division IN ({_duros_sql})   THEN 'duros'
            WHEN cat.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT cat.sku_marketplace) AS sku_stock
    FROM cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas cat
    INNER JOIN sellers_validos s ON cat.seller_id = s.seller_id
    WHERE cat.stock > 0 AND cat.approval_status = 'approved'
    GROUP BY cat.seller_id, division_db
),
base AS (
    SELECT
        c.seller_id,
        s.name,
        c.division_db,
        c.sku_creados,
        COALESCE(st.sku_stock, 0) AS sku_stock,
        COALESCE(st.sku_stock, 0)::decimal / NULLIF(c.sku_creados, 0) AS pct_con_stock
    FROM cant_sku_creados c
    LEFT JOIN sku_con_stock st
        ON c.seller_id = st.seller_id
       AND c.division_db = st.division_db
    INNER JOIN sellers_validos s ON c.seller_id = s.seller_id
)
SELECT
    seller_id,
    name,
    division_db,
    sku_creados,
    sku_stock,
    COALESCE(ROUND(pct_con_stock * 100, 2) || '%', '0%') AS pct_con_stock,
    ROUND(
        PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY pct_con_stock) * 100, 0
    ) AS percentil_stock,
    ROUND(
        PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY sku_stock) * 100, 0
    ) AS percentil_volumen_stock
FROM base
ORDER BY division_db, sku_stock DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, division_db, sku_creados, sku_stock,
    pct_con_stock (texto %), percentil_stock (% disponibilidad, 0-100),
    percentil_volumen_stock (volumen de SKU con stock, 0-100).

    Clave: seller_id + division_db.
    """
    return run_query(QUERY_PRODUCTOS)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"  en duros:   {df[df['division_db'] == 'duros']['seller_id'].nunique()}")
    print(f"  en blandos: {df[df['division_db'] == 'blandos']['seller_id'].nunique()}")
    print(df.head(100))