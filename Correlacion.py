"""
Análisis de correlación entre las variables del Score Growth.
Objetivo: detectar qué variables se están "pisando" (miden lo mismo)
para no darles peso doble en el score.

"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

RUTA = "score_growth.xlsx"

df = pd.read_excel(RUTA)   

print("Columnas encontradas:")
print(df.columns.tolist())
print(f"\nFilas (sellers): {len(df)}\n")

columnas = ["venta_percentil",
            "percentil_cvr",
    "percentil_stock", "percentil_volumen_stock",
    "total_invertido", "percentil_recurrencia"
]


columnas = [c for c in columnas if c in df.columns]
df_num = df[columnas].copy()

print("Variables usadas en la correlación:")
print(columnas)


print("\nDatos faltantes por columna:")
faltantes = df_num.isna().sum()
for col, n in faltantes.items():
    pct = n / len(df_num) * 100
    print(f"  {col}: {n} nulos ({pct:.0f}%)")



for col in df_num.columns:
    if df_num[col].dtype == "object":
        df_num[col] = (
            df_num[col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

    df_num[col] = pd.to_numeric(df_num[col], errors="coerce")



# Matriz de correlación
corr = df_num.corr(method="pearson")

print("\n=== Matriz de correlación ===")
print(corr.round(2))


plt.figure(figsize=(11, 9))
sns.heatmap(
    corr,
    annot=True,
    fmt=".2f",
    cmap="RdBu_r",     
    center=0,
    vmin=-1, vmax=1,
    square=True,
    cbar_kws={"label": "Correlación"}
)
plt.title("Correlación entre variables - Score Growth")
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig("heatmap_correlacion.png", dpi=150)
plt.show()

# ----------------------------------------------------------------------
# Pares problemáticos (|corr| > 0.7)
# ----------------------------------------------------------------------
UMBRAL = 0.7
pares = []

for i in range(len(corr.columns)):
    for j in range(i + 1, len(corr.columns)):
        valor = corr.iloc[i, j]
        if pd.notna(valor) and abs(valor) > UMBRAL:
            pares.append((corr.columns[i], corr.columns[j], round(valor, 2)))

print(f"\n=== Pares con correlación fuerte (|r| > {UMBRAL}) ===")
if pares:
    for a, b, v in sorted(pares, key=lambda x: abs(x[2]), reverse=True):
        print(f"  {a}  <->  {b}:  {v}")
else:
    print("  Ninguno. Las variables aportan información bastante independiente.")