"""
main.py - Score Growth: union de todas las variables + score + perfilado.

"""

import pandas as pd

from Scoring import calcular_score
import Variables.Venta_percentil as venta_percentil
import Variables.CVR as CVR
import Variables.Inversion as Inversion
import Variables.Estado as Estado
import Variables.Carga_SKU as Carga_SKU
import Variables.Recurrencia_venta as Recurrencia
import Variables.Reputacion as Reputacion
import Variables.Categoria as Categoria
import Variables.Tendencia as Tendencia
from Tratamiento import escribir_hojas_tratamiento
from Farming import escribir_hoja_farming


from export_excel import exportar
from Perfil import perfilar, escribir_hoja_resumen, resumen_consola


def tabla_larga() -> pd.DataFrame:
    """Una fila por seller-dureza, con todas las variables. Base del score."""

    print("=== CALCULANDO TABLA LARGA ===")
    print("=== VENTA ===")
    venta = venta_percentil.calcular()
    print("=== CVR ===")
    cvr = CVR.calcular()
    print("=== RECURRENCIA ===")
    rec = Recurrencia.calcular()

    venta_cols = venta[["seller_id", "name", "admin_email", "division_db", "venta", "venta_percentil"]]
    cvr_cols = cvr[["seller_id", "division_db", "cvr_seller", "percentil_cvr"]]
    rec_cols = rec[["seller_id", "division_db", "dias_vendidos", "tramos_con_venta",
                    "recurrencia", "percentil_recurrencia"]]

    print("=== MERGE VENTA + CVR + RECURRENCIA ===")
    df = venta_cols.merge(cvr_cols, on=["seller_id", "division_db"], how="outer")
    df = df.merge(rec_cols, on=["seller_id", "division_db"], how="outer")

    print("=== INVERSION ===")
    inv = Inversion.calcular()
    print("=== CARGA SKU ===")
    sku = Carga_SKU.calcular()

    print("=== MERGE + INVERSION + CARGA SKU ===")
    inv_cols = inv[["seller_id", "invirtio", "total_invertido"]]
    sku_cols = sku[["seller_id", "division_db", "sku_creados", "sku_stock",
                "pct_con_stock", "percentil_stock", "percentil_volumen_stock"]]

    df = df.merge(inv_cols, on="seller_id", how="left")
    df = df.merge(sku_cols, on=["seller_id", "division_db"], how="left")

    # --- estado del seller (contexto) ---
    print("=== ESTADO DEL SELLER ===")
    est = Estado.calcular()
    df = df.merge(est, on="seller_id", how="left")
    df["estado_seller"] = df["estado_seller"].fillna("No clasificado")

    print("=== REPUTACIÓN DEL SELLER ===")
    rep = Reputacion.calcular()
    rep = rep.drop(columns=["name"], errors="ignore")   # evita colision con name de venta
    df = df.merge(rep, on="seller_id", how="left")

    print("=== CATEGORÍA PRINCIPAL DEL SELLER ===")
    cat = Categoria.calcular()
    df = df.merge(cat[["seller_id", "categoria", "pct_skus_categoria"]], on="seller_id", how="left")

    print("=== TENDENCIA DE VENTA (30 vs 30 DÍAS) ===")
    ten = Tendencia.calcular()
    df = df.merge(ten[["seller_id", "division_db", "venta_ult_30d", "venta_30d_anterior",
                       "variacion_venta_30d", "tendencia_venta"]],
                  on=["seller_id", "division_db"], how="left")
    df["tendencia_venta"] = df["tendencia_venta"].fillna("Sin venta en 60 dias")
    df[["venta_ult_30d", "venta_30d_anterior"]] = df[["venta_ult_30d", "venta_30d_anterior"]].fillna(0)

    print("=== TABLA LARGA CALCULADA ===")
    df = df.sort_values(["seller_id", "division_db"]).reset_index(drop=True)

    orden = ["seller_id", "name", "admin_email", "categoria", "pct_skus_categoria",
             "estado_seller", "categoria_reputacion",
             "division_db", "score",
         "venta", "venta_percentil",
         "tendencia_venta", "variacion_venta_30d", "venta_ult_30d", "venta_30d_anterior",
         "dias_vendidos", "tramos_con_venta", "recurrencia", "percentil_recurrencia",
         "cvr_seller", "percentil_cvr",
         "sku_creados", "sku_stock", "pct_con_stock", "percentil_stock", "percentil_volumen_stock",
         "invirtio", "total_invertido"]
    df = df[[c for c in orden if c in df.columns]]

    return df


if __name__ == "__main__":
    largo = tabla_larga()
    largo = calcular_score(largo)

    # --- perfilado: segmento + banderas de brecha ---
    print("=== PERFILANDO (segmento + banderas) ===")
    largo = perfilar(largo)

    print("=== TABLA LARGA (base del score) ===")
    print(f"Filas (seller-dureza): {len(largo)}")
    print(f"Sellers unicos: {largo['seller_id'].nunique()}")
    print("\nDistribucion de estados:")
    print(largo.drop_duplicates("seller_id")["estado_seller"].value_counts())

    resumen_consola(largo)

    orden = ["seller_id", "name", "admin_email", "categoria", "estado_seller", "categoria_reputacion",
              "division_db", "score", "segmento",
         "venta", "venta_percentil",
         "tendencia_venta", "variacion_venta_30d", "venta_ult_30d", "venta_30d_anterior",
         "dias_vendidos", "tramos_con_venta", "recurrencia", "percentil_recurrencia",
         "cvr_seller", "percentil_cvr",
         "sku_creados", "sku_stock", "pct_con_stock", "percentil_stock", "percentil_volumen_stock",
         "invirtio", "total_invertido"]
    largo_export = largo[[c for c in orden if c in largo.columns]]


    print("=== GUARDANDO ARCHIVOS ===")
    largo.to_csv("score_largo.csv", index=False)      
    exportar(largo_export, "score_growth.xlsx")      

    print("=== AGREGANDO HOJA RESUMEN ===")
    escribir_hoja_resumen(largo, "score_growth.xlsx")
    print("=== AGREGANDO HOJAS DE TRATAMIENTO ===")
    escribir_hojas_tratamiento(largo, "score_growth.xlsx")
    print("=== AGREGANDO HOJA DE PRIORIZACIÓN DE FARMING ===")
    escribir_hoja_farming(largo, "score_growth.xlsx")

    print("\nListo: score_largo.csv y score_growth.xlsx "
          "(hojas: Score Growth, Resumen, Regalo SP, Personalizado BD, "
          "Priorización de farming, Resumen farming)")