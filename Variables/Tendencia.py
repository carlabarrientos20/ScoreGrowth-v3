"""
Tendencia de venta (CONTEXTO, no entra al score).

Compara la venta de los ultimos 30 dias contra los 30 dias anteriores, por
seller y dureza. El score mira 90 dias y se mueve lento; esta columna muestra
si el seller viene subiendo o bajando AHORA.

  variacion_venta_30d = (venta_ult_30d - venta_30d_anterior) / venta_30d_anterior

  tendencia_venta:
    Subiendo                   variacion >= +20%
    Estable                    entre -20% y +20%
    Bajando                    variacion <= -20%
    Sin venta ultimos 30 dias  vendio en los 30 anteriores, pero no en los ultimos 30
    Retomo venta               vendio en los ultimos 30, pero no en los 30 anteriores
    Sin venta en 60 dias       no vendio en ninguno de los dos periodos (se asigna en main.py)

Tabla final: seller_id | division_db | venta_ult_30d | venta_30d_anterior |
             variacion_venta_30d | tendencia_venta
"""

import pandas as pd
from db import run_query
from config import DUROS, BLANDOS, DIAS_ONBOARDING, DIAS_TENDENCIA, UMBRAL_TENDENCIA

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_TENDENCIA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
ventas AS (
    SELECT
        t.seller_id,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        SUM(CASE WHEN t.fecha_venta >= DATE_TRUNC('day', DATEADD(day, -{DIAS_TENDENCIA}, CURRENT_DATE))
                 THEN t.precio_venta ELSE 0 END) AS venta_ult_30d,
        SUM(CASE WHEN t.fecha_venta <  DATE_TRUNC('day', DATEADD(day, -{DIAS_TENDENCIA}, CURRENT_DATE))
                 THEN t.precio_venta ELSE 0 END) AS venta_30d_anterior
    FROM cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
    INNER JOIN sellers_validos s ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('day', DATEADD(day, -{2 * DIAS_TENDENCIA}, CURRENT_DATE))
      AND t.fecha_venta <  DATE_TRUNC('day', CURRENT_DATE)
    GROUP BY t.seller_id, division_db
)
SELECT
    seller_id,
    division_db,
    venta_ult_30d,
    venta_30d_anterior,
    CASE WHEN venta_30d_anterior > 0
         THEN ROUND((venta_ult_30d - venta_30d_anterior)::decimal / venta_30d_anterior, 3)
    END AS variacion_venta_30d,
    CASE
        WHEN venta_30d_anterior <= 0 AND venta_ult_30d <= 0 THEN 'Sin venta en 60 dias'
        WHEN venta_30d_anterior <= 0 THEN 'Retomo venta'
        WHEN venta_ult_30d <= 0 THEN 'Sin venta ultimos 30 dias'
        WHEN venta_ult_30d >= venta_30d_anterior * (1 + {UMBRAL_TENDENCIA}) THEN 'Subiendo'
        WHEN venta_ult_30d <= venta_30d_anterior * (1 - {UMBRAL_TENDENCIA}) THEN 'Bajando'
        ELSE 'Estable'
    END AS tendencia_venta
FROM ventas
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, division_db, venta_ult_30d, venta_30d_anterior,
    variacion_venta_30d (ej: 0.25 = +25%), tendencia_venta.

    Clave: seller_id + division_db. Solo sellers con venta en los ultimos 60 dias.
    """
    return run_query(QUERY_TENDENCIA)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division) con venta en los ultimos {2 * DIAS_TENDENCIA} dias: {len(df)}")
    print("\nTendencia de venta:")
    print(df["tendencia_venta"].value_counts())
    print(df.head(30))
