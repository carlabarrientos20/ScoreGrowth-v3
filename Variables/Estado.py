"""
Estado del seller (CONTEXTO, no entra al score).

Un estado unico por seller MID-MARKET, respecto al ULTIMO MES CERRADO
(en agosto -> julio), alineado con el horizonte del resto de variables.

Sellers que NUNCA vendieron:
  - Ghost:      nunca creo productos (0 SKUs en catalogo).
  - Sin venta:  tiene SKUs creados pero nunca ha vendido.

Sellers que SI vendieron en el mes de referencia:
  - Primera venta:    su primera venta fue justo ese mes.
  - Activo:           venia vendiendo seguido (tambien vendio el mes anterior).
  - Reactivado:       vendio ese mes pero venia de un hueco (no vendio el mes anterior).

Sellers que NO vendieron en el mes de referencia, pero SI en el mes en curso:
  - Primera venta:    su primera venta es del mes en curso.
  - Reactivado:       volvio a vender este mes despues de un hueco.
  (Si el score se corre el dia 1 del mes, el mes en curso casi no tiene ventas
   y este caso practicamente no aparece.)

Sellers que NO vendieron ni en el mes de referencia ni en el mes en curso
(apagados, por antiguedad de su ultima venta):
  - Dormant:  ultima venta hace 1-2 meses (no vendio el ultimo mes o dos).
  - Fugado:   ultima venta hace 3-6 meses.
  - Out <12:  ultima venta hace 6-12 meses.
  - Out >12:  ultima venta hace +12 meses.
"""

import pandas as pd
from db import run_query

QUERY_ESTADO = """
WITH mm AS (
    SELECT DISTINCT id_seller
    FROM cencosud_chile_txd_reporter.cluster_seller
    WHERE tier = 'Mid-Market'
),
params AS (
    -- mes_sel = ultimo mes cerrado; mes_ant = el anterior a ese; mes_act = mes en curso
    SELECT
        DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AS mes_sel,
        DATEADD(month, -2, DATE_TRUNC('month', CURRENT_DATE)) AS mes_ant,
        DATE_TRUNC('month', CURRENT_DATE) AS mes_act
),
ventas_por_mes AS (
    SELECT
        t.seller_id,
        DATE_TRUNC('month', (t.año::text || '-' || LPAD(t.mes::text, 2, '0') || '-01')::date) AS mes_venta
    FROM cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
    INNER JOIN mm ON t.seller_id = mm.id_seller
    GROUP BY t.seller_id, mes_venta
),
resumen AS (
    SELECT
        vpm.seller_id,
        MIN(vpm.mes_venta) AS primera_venta,
        MAX(vpm.mes_venta) AS ultima_venta,
        MAX(CASE WHEN vpm.mes_venta = p.mes_sel THEN 1 ELSE 0 END) AS vendio_sel,
        MAX(CASE WHEN vpm.mes_venta = p.mes_ant THEN 1 ELSE 0 END) AS vendio_ant,
        MAX(CASE WHEN vpm.mes_venta = p.mes_act THEN 1 ELSE 0 END) AS vendio_act
    FROM ventas_por_mes vpm
    CROSS JOIN params p
    GROUP BY vpm.seller_id
),
skus AS (
    -- SKUs creados por seller (cualquier estado de publicacion)
    SELECT
        c.seller_id,
        COUNT(DISTINCT c.sku_marketplace) AS n_skus
    FROM cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas c
    INNER JOIN mm ON c.seller_id = mm.id_seller
    GROUP BY c.seller_id
)
SELECT
    mm.id_seller AS seller_id,
    CASE
        -- --- nunca vendieron ---
        WHEN r.seller_id IS NULL AND COALESCE(s.n_skus, 0) = 0 THEN 'Ghost'
        WHEN r.seller_id IS NULL THEN 'Sin venta'
        -- --- vendieron en el mes de referencia ---
        WHEN r.vendio_sel = 1 AND r.primera_venta = p.mes_sel THEN 'Primera venta'
        WHEN r.vendio_sel = 1 AND r.vendio_ant = 1 THEN 'Activo'
        WHEN r.vendio_sel = 1 AND r.vendio_ant = 0 THEN 'Reactivado'
        -- --- no vendieron en el mes de referencia, pero SI en el mes en curso ---
        WHEN r.vendio_act = 1 AND r.primera_venta = p.mes_act THEN 'Primera venta'
        WHEN r.vendio_act = 1 THEN 'Reactivado'
        -- --- NO vendieron ni en el mes de referencia ni en el mes en curso (apagados) ---
        WHEN r.ultima_venta >= DATEADD(month, -2, p.mes_sel)  THEN 'Dormant'
        WHEN r.ultima_venta >= DATEADD(month, -6, p.mes_sel)  THEN 'Fugado'
        WHEN r.ultima_venta >= DATEADD(month, -12, p.mes_sel) THEN 'Out <12'
        WHEN r.ultima_venta <  DATEADD(month, -12, p.mes_sel) THEN 'Out >12'
        ELSE 'Otro'
    END AS estado_seller,
    COALESCE(s.n_skus, 0) AS n_skus_chequeo
FROM mm
LEFT JOIN resumen r ON r.seller_id = mm.id_seller
LEFT JOIN skus    s ON s.seller_id = mm.id_seller
CROSS JOIN params p
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, estado_seller (una fila por seller MM)."""
    df = run_query(QUERY_ESTADO)
    return df[["seller_id", "estado_seller"]]


if __name__ == "__main__":
    df_full = run_query(QUERY_ESTADO)
    print(f"Sellers MM clasificados: {len(df_full)}")
    print("\nDistribucion de estados:")
    print(df_full["estado_seller"].value_counts())

    # Sanity check: sellers con ventas pero 0 SKUs en catalogo.
    # Si salen muchos, la tabla de replicas no guarda historico
    # y el Ghost podria estar inflado.
    raros = df_full[
        (~df_full["estado_seller"].isin(["Ghost", "Sin venta"]))
        & (df_full["n_skus_chequeo"] == 0)
    ]
    print(f"\nSellers con venta pero 0 SKUs en catalogo: {len(raros)}")
    print(raros.head(20))