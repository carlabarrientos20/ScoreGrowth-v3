"""
Categoria principal del seller (CONTEXTO, no entra al score).

Un seller puede vender en varias categorias (divisiones). Se usa como su
categoria principal la division donde tiene MAS SKUs en el catalogo.
Con esto se asigna cada seller a un account manager de Farming (uno por division).

Desempate (mismo numero de SKUs en dos divisiones):
  1. la division con mas SKUs con stock aprobados
  2. orden alfabetico

Tabla final: seller_id | categoria | skus_categoria | pct_skus_categoria
"""

import pandas as pd
from db import run_query
from config import DIAS_ONBOARDING

QUERY_CATEGORIA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id
    FROM eiffel_seller.seller
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
skus_por_division AS (
    SELECT
        cat.seller_id,
        cat.division,
        COUNT(DISTINCT cat.sku_marketplace) AS skus_division,
        COUNT(DISTINCT CASE WHEN cat.stock > 0 AND cat.approval_status = 'approved'
                            THEN cat.sku_marketplace END) AS skus_stock_division
    FROM cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas cat
    INNER JOIN sellers_validos s ON cat.seller_id = s.seller_id
    WHERE cat.division IS NOT NULL
    GROUP BY cat.seller_id, cat.division
),
ranking AS (
    SELECT
        seller_id,
        division,
        skus_division,
        SUM(skus_division) OVER (PARTITION BY seller_id) AS skus_total,
        ROW_NUMBER() OVER (
            PARTITION BY seller_id
            ORDER BY skus_division DESC, skus_stock_division DESC, division
        ) AS rn
    FROM skus_por_division
)
SELECT
    seller_id,
    division AS categoria,
    skus_division AS skus_categoria,
    ROUND(skus_division::decimal / NULLIF(skus_total, 0), 3) AS pct_skus_categoria
FROM ranking
WHERE rn = 1
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, categoria, skus_categoria, pct_skus_categoria (0 a 1).

    Clave: seller_id (una fila por seller).
    """
    return run_query(QUERY_CATEGORIA)


if __name__ == "__main__":
    df = calcular()
    print(f"Sellers con categoria: {len(df)}")
    print("\nSellers por categoria principal:")
    print(df["categoria"].value_counts())
    print("\n% del catalogo en su categoria principal (mediana):",
          f"{pd.to_numeric(df['pct_skus_categoria']).median():.0%}")
    print(df.head(30))
