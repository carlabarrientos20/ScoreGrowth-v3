"""
Variable 2: Conversion (CVR)

Calcula la tasa de conversion de cada seller en los ultimos HORIZONTE_DIARIO dias
(sin contar hoy),
clasificada por division (duros/blandos), y su percentil DENTRO de su division.

CVR_seller = SUM(transacciones del seller) / SUM(visitas del seller)
(se suma arriba y abajo y se divide al final; NO se promedian los CVR por producto)

Los sellers SIN visitas quedan fuera (no tienen CVR calculable). Asi no reciben
un percentil falso de 100 ni distorsionan el percentil de los demas. Al cruzar
en el score, esos sellers tendran percentil_cvr en NaN -> se tratan como neutral.
"""

import pandas as pd
from db import run_query
from config import (HORIZONTE_DIARIO, DUROS, BLANDOS,
                    DIAS_ONBOARDING)

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_CVR = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name, c.tier
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
total_transacciones AS (
    SELECT t.seller_id, s.name,
        COUNT(oc) AS transacciones,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db
    FROM cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
    INNER JOIN sellers_validos s
        ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('day', DATEADD(day, -{HORIZONTE_DIARIO}, CURRENT_DATE))
      AND t.fecha_venta <  DATE_TRUNC('day', CURRENT_DATE)
    GROUP BY t.seller_id, division_db, s.name
),
numero_visitas AS (
    SELECT c.seller_id, c.seller_name, SUM(d.pdp_views) AS total_visitas,
        CASE
            WHEN c.division IN ({_duros_sql})   THEN 'duros'
            WHEN c.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db
    FROM source_bi_paristxd_product.product_data_daily d
    LEFT JOIN cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas c
        ON c.sku_marketplace = d.product_id
    WHERE d.date >= DATE_TRUNC('day', DATEADD(day, -{HORIZONTE_DIARIO}, CURRENT_DATE))
      AND d.date <  DATE_TRUNC('day', CURRENT_DATE)
    GROUP BY c.seller_id, c.seller_name, division_db
),
con_cvr AS (
    SELECT
        t.seller_id, t.name, t.division_db,
        t.transacciones, n.total_visitas,
        t.transacciones::decimal / n.total_visitas AS cvr_valor
    FROM total_transacciones t
    INNER JOIN numero_visitas n
        ON n.seller_id = t.seller_id AND n.division_db = t.division_db
    WHERE n.total_visitas > 0
)
SELECT
    seller_id, name, division_db, transacciones, total_visitas,
    ROUND(cvr_valor * 100, 2) || '%' AS cvr_seller,
    ROUND(PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY cvr_valor) * 100, 0) AS percentil_cvr
FROM con_cvr
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, division_db, transacciones, total_visitas,
    cvr_seller (texto con %), percentil_cvr (0-100 dentro de su dureza).

    Solo sellers con visitas > 0. Clave: seller_id + division_db.
    """
    return run_query(QUERY_CVR)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"  en duros:   {df[df['division_db'] == 'duros']['seller_id'].nunique()}")
    print(f"  en blandos: {df[df['division_db'] == 'blandos']['seller_id'].nunique()}")
    print(f"  en otros:   {df[df['division_db'] == 'otros']['seller_id'].nunique()}")
    print(df.head(100))