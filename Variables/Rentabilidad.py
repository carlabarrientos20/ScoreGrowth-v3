"""
Variable 4: Rentabilidad para el marketplace.

Tabla final:
  seller_id | name | en_excel (si/no) | rentable (si/no/sin dato) | margen_pct | margen_nominal_3m

"""

import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from db import run_query

SHEET_ID = "14xfITGKzs0lmpEAroLXzdEtYsYARLKarPZF4DgV0_VU"
GID = "0"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

MESES = {"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,
         "jul":7,"ago":8,"sep":9,"oct":10,"nov":11,"dic":12}

QUERY_SELLERS_VALIDOS = """
SELECT s.id AS seller_id, s.name
FROM eiffel_seller.seller s
LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON s.id = c.id_seller
WHERE s.created_at <= DATEADD(day, -90, CURRENT_DATE)
  AND c.tier = 'Mid-Market' AND s.publish = 1
"""


def meses_horizonte():
    hoy = date.today()
    primer_dia = hoy.replace(day=1)
    return [(primer_dia - relativedelta(months=i)).month for i in range(3, 0, -1)]


def leer_rentabilidad():
    """Lee el Sheet una vez y devuelve dos cosas:
      - resumen: venta_facturada y margen_nominal sumados por seller en el horizonte.
      - ids_en_excel: set con TODOS los seller_id que aparecen en el Excel
                      (sin importar mes), para saber quien esta cargado.
    """
    df = pd.read_csv(SHEET_URL)

    ids_en_excel = set(df["seller_id"].dropna().astype(str))

    cols = df.columns.drop("seller_id")
    for c in cols:
        df[c] = (df[c].astype(str)
                 .str.replace("$", "", regex=False)
                 .str.replace(".", "", regex=False)
                 .str.strip())
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # ancho -> largo, separar metrica y mes, filtrar horizonte
    largo = df.melt(id_vars="seller_id", var_name="columna", value_name="valor")
    largo[["metrica", "mes_texto"]] = largo["columna"].str.rsplit("_", n=1, expand=True)
    largo["mes"] = largo["mes_texto"].map(MESES)
    largo = largo[largo["mes"].isin(meses_horizonte())]

    # chequeo piloto: cuantos datos no-nulos hay por mes (para ver si falta julio)
    print("Datos no-nulos por mes en el horizonte:")
    print(largo.groupby("mes")["valor"].apply(lambda x: x.notna().sum()))

    resumen = largo.pivot_table(index="seller_id", columns="metrica",
                                values="valor", aggfunc="sum").reset_index()
    return resumen, ids_en_excel


def calcular() -> pd.DataFrame:
    sellers = run_query(QUERY_SELLERS_VALIDOS)
    rent, ids_en_excel = leer_rentabilidad()

    df = sellers.merge(rent, on="seller_id", how="left")

    # columna en_excel: el seller_id aparece en el Sheet (en cualquier mes)?
    df["en_excel"] = df["seller_id"].astype(str).isin(ids_en_excel).map({True: "si", False: "no"})

    # margen %
    vf = df["venta_facturada"].replace(0, pd.NA)
    df["margen_pct"] = df["margen_nominal"] / vf

    def clasificar(row):
        if pd.isna(row["venta_facturada"]) or pd.isna(row["margen_pct"]):
            return "sin dato"
        return "si" if row["margen_pct"] > 0 else "no"

    df["rentable"] = df.apply(clasificar, axis=1)
    df = df.rename(columns={"margen_nominal": "margen_nominal_3m"})

    return df[["seller_id", "name", "en_excel", "rentable", "margen_pct", "margen_nominal_3m"]]


if __name__ == "__main__":
    df = calcular()
    print(f"\nSellers validos (MM + 90 dias): {len(df)}")
    print(f"  rentables:     {(df['rentable'] == 'si').sum()}")
    print(f"  no rentables:  {(df['rentable'] == 'no').sum()}")
    print(f"  sin dato:      {(df['rentable'] == 'sin dato').sum()}")
    print("\nDesglose de los 'sin dato':")
    sin_dato = df[df["rentable"] == "sin dato"]
    print(f"  estan en excel pero sin datos en el horizonte: {(sin_dato['en_excel'] == 'si').sum()}")
    no_en_excel = df[df["en_excel"] == "no"]
    print(f"Sellers que NO están en el Excel: {len(no_en_excel)}")
    no_en_excel.to_csv("sellers_sin_rentabilidad.csv", index=False)
    print("Guardados en sellers_sin_rentabilidad.csv")