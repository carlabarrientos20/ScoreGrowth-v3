"""
Variable: Recurrencia de venta.

Mide en cuantos dias del horizonte el seller efectivamente vendio.

  recurrencia           = dias_vendidos / dias_ventana   (0.0 a 1.0, informativo)
  percentil_recurrencia = percentil de dias_vendidos dentro de su dureza (0 a 100).
                          Es lo que entra al score, igual que las demas variables.

Ademas entrega tramos_con_venta: el horizonte se divide en 3 tramos iguales
(con 90 dias, de 30 dias cada uno) y se cuenta en cuantos vendio al menos
una vez (0 a 3). No entra al score: lo usan la bandera de frecuencia
(Perfil.py) y las reglas de Regalo SP (Tratamiento.py).
"""

import pandas as pd
from db import run_query
from config import (
    HORIZONTE_DIARIO,
    DUROS,
    BLANDOS,
    DIAS_ONBOARDING,
    TRAMOS_TOTALES
)

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_RECURRENCIA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name, c.tier
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
meses_con_venta AS (
    SELECT
        t.seller_id,
        s.name,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT DATE_TRUNC('day', t.fecha_venta)) AS dias_vendidos,
        -- El horizonte se parte en {TRAMOS_TOTALES} tramos iguales hacia atras desde ayer (division entera).
        -- Con 90 dias: tramo 0 = ultimos 30 dias, tramo 1 = dias 31-60, tramo 2 = dias 61-90.
        COUNT(DISTINCT (DATEDIFF(day, t.fecha_venta, CURRENT_DATE) - 1) * {TRAMOS_TOTALES} / {HORIZONTE_DIARIO}) AS tramos_con_venta
    FROM cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
    INNER JOIN sellers_validos s
        ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('day', DATEADD(day, -{HORIZONTE_DIARIO}, CURRENT_DATE))
      AND t.fecha_venta <  DATE_TRUNC('day', CURRENT_DATE)
    GROUP BY t.seller_id, division_db, name
)
SELECT
    seller_id,
    name,
    division_db,
    dias_vendidos,
    {HORIZONTE_DIARIO} AS dias_ventana,
    tramos_con_venta,
    ROUND(dias_vendidos::numeric / {HORIZONTE_DIARIO}, 3) AS recurrencia,
    ROUND(PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY dias_vendidos) * 100, 0) AS percentil_recurrencia
FROM meses_con_venta
ORDER BY division_db, recurrencia DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, division_db, dias_vendidos, dias_ventana,
    tramos_con_venta, recurrencia, percentil_recurrencia.

    recurrencia va de 0.0 (nunca vendio) a 1.0 (vendio todos los dias).
    Para el score: aporte = percentil_recurrencia * PESO_RECURRENCIA
    """
    return run_query(QUERY_RECURRENCIA)


if __name__ == "__main__":
    df = calcular()
    print(f"Ventana: {HORIZONTE_DIARIO} días")
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print("\nDistribucion de recurrencia:")
    print(df["recurrencia"].describe())
    print("\nPercentil de recurrencia (mediana por dureza):")
    print(df.groupby("division_db")["percentil_recurrencia"].median())
    print(f"\nSellers por tramos con venta ({TRAMOS_TOTALES} tramos de ~{HORIZONTE_DIARIO / TRAMOS_TOTALES:.0f} dias):")
    print(df["tramos_con_venta"].value_counts().sort_index())
    print("\n", df.head(50))