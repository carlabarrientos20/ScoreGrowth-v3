"""
distribucion_score.py - Explora como se reparten los scores antes de segmentar,
SEPARADO por dureza (duros / blandos).

"""

import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# 1. Cargar los datos
# ----------------------------------------------------------------------
RUTA = "score_growth.xlsx"
df = pd.read_excel(RUTA)

df["score"] = pd.to_numeric(df["score"], errors="coerce")


def analizar_dureza(sub: pd.DataFrame, dureza: str):
    """Corre estadisticas + histograma para una sola dureza."""
    scores = sub["score"].dropna()

    print("\n" + "=" * 55)
    print(f"  DUREZA: {dureza.upper()}")
    print("=" * 55)

    if len(scores) == 0:
        print("  Sin datos para esta dureza.")
        return

    print(f"Filas seller con score: {len(scores)}")
    print(f"Sellers unicos: {sub['seller_id'].nunique()}\n")

    # --- estadisticas ---
    print("=== ESTADISTICAS DEL SCORE ===")
    print(f"  Minimo:        {scores.min():.1f}")
    print(f"  Maximo:        {scores.max():.1f}")
    print(f"  Promedio:      {scores.mean():.1f}")
    print(f"  Mediana:       {scores.median():.1f}")
    print(f"  Desv. estand.: {scores.std():.1f}")

    print("\n=== PERCENTILES (cortes 'naturales' si segmentas por percentil) ===")
    for p in [10, 20, 25, 50, 75, 80, 90]:
        print(f"  P{p}: {scores.quantile(p/100):.1f}")

    # --- conteo por tramos fijos ---
    print("\n=== CONTEO POR TRAMOS FIJOS (de 20 en 20) ===")
    tramos = [0, 20, 40, 60, 80, 100]
    etiquetas = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    conteo = pd.cut(scores, bins=tramos, labels=etiquetas, include_lowest=True)
    tabla = conteo.value_counts().sort_index()
    for tramo, n in tabla.items():
        pct = n / len(scores) * 100
        barra = "#" * int(pct / 2)
        print(f"  {tramo:>7}: {n:>4} sellers ({pct:>5.1f}%)  {barra}")

    # --- histograma ---
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=20, range=(0, 100), color="#4C78A8", edgecolor="white")
    plt.axvline(scores.mean(), color="red", linestyle="--", linewidth=1.5,
                label=f"Promedio ({scores.mean():.0f})")
    plt.axvline(scores.median(), color="green", linestyle="--", linewidth=1.5,
                label=f"Mediana ({scores.median():.0f})")
    plt.title(f"Distribucion del Score Growth - {dureza}")
    plt.xlabel("Score (0-100)")
    plt.ylabel("Cantidad de sellers")
    plt.legend()
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    nombre = f"score_distribucion_{dureza}.png"
    plt.savefig(nombre, dpi=150)
    plt.close()
    print(f"\nHistograma guardado en: {nombre}")


# ----------------------------------------------------------------------
# 2. Correr el analisis para cada dureza por separado
# ----------------------------------------------------------------------
for dureza in ["duros", "blandos"]:
    sub = df[df["division_db"] == dureza]
    analizar_dureza(sub, dureza)

otros = df[~df["division_db"].isin(["duros", "blandos"])]
if len(otros) > 0:
    print(f"\n(Nota: {len(otros)} filas con division_db distinto de duros/blandos "
          f"quedaron fuera del analisis.)")