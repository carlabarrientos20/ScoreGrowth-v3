"""
Variable 1: Venta.

Calcula la venta total de cada seller en los ultimos HORIZONTE_DIARIO dias (sin contar hoy),
clasificada por division (duros/blandos), y su percentil DENTRO de su dureza.
"""

import pandas as pd
from db import run_query
from config import DUROS, BLANDOS, DIAS_ONBOARDING, HORIZONTE_DIARIO

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_VENTA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name, admin_email, c.tier
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
ventas_seller AS (
    SELECT
        s.seller_id,
        s.name,
        s.admin_email,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COALESCE(SUM(t.precio_venta), 0) AS venta
    FROM sellers_validos s
    LEFT JOIN cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
        ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('day', DATEADD(day, -{HORIZONTE_DIARIO}, CURRENT_DATE))
            AND t.fecha_venta <  DATE_TRUNC('day', CURRENT_DATE)
    GROUP BY s.seller_id, s.name, s.admin_email, division_db
)
SELECT
    seller_id,
    name,
    admin_email,
    division_db,
    venta,
    AVG(venta) OVER (PARTITION BY division_db) AS promedio_division,
    ROUND(PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY venta) * 100, 0) AS venta_percentil
FROM ventas_seller
ORDER BY division_db, venta DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, admin_email, division_db, venta, promedio_division, venta_percentil.

    Clave: seller_id + division_db (un seller mixto aparece en dos filas).
    """
    return run_query(QUERY_VENTA)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"  en duros:   {df[df['division_db'] == 'duros']['seller_id'].nunique()}")
    print(f"  en blandos: {df[df['division_db'] == 'blandos']['seller_id'].nunique()}")
    print(f"  en otros:   {df[df['division_db'] == 'otros']['seller_id'].nunique()}")
    print(df.head(100))