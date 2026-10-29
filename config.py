"""
Constantes del proyecto 
"""

# --- Tablas en Redshift ---
TABLA_SELLERS = "eiffel_seller.seller"
TABLA_TRANSACCIONES = "cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp"
TABLA_VISTAS = "source_bi_paristxd_product.product_data_daily"

# --- Clasificación de divisiones en dureza ---
DUROS = ["DECO-HOGAR", "TECNOLOGIA", "ELECTRO-HOGAR", "NUEVOS NEGOCIOS"]
BLANDOS = ["ACCESORIOS", "DEPORTES", "HOMBRES", "MUJER", "CALZADO", "INFANTIL"]

# --- Parámetros del score ---
DIAS_ONBOARDING = 90   # un seller entra al análisis tras 90 días de creado
HORIZONTE_MESES = 3    # ventana de 3 meses cerrados -> ya no se usa 
HORIZONTE_DIARIO = 90  #Cambio de granularidad temporal de meses a días para entregar la posibilidad de calcular el score en cualquier horizonte temporal de forma diaria

# --- Tramos dentro del horizonte (miden constancia de venta) ---
# El horizonte SIEMPRE se divide en 3 tramos iguales, contados hacia atrás desde ayer:
#   90 días -> 3 tramos de 30 | 60 días -> 3 de 20 | 30 días -> 3 de 10 | 180 días -> 3 de 60
# Si el horizonte no es divisible por 3, los tramos más recientes quedan con 1 día más.
# Los usan la bandera de frecuencia (Perfil.py: menos de 2 de 3) y Regalo SP (Tratamiento.py).
TRAMOS_TOTALES = 3

# --- Tendencia de venta (contexto, no entra al score) ---
# Compara la venta de los últimos DIAS_TENDENCIA días contra los DIAS_TENDENCIA anteriores.
# Es independiente del horizonte del score.
DIAS_TENDENCIA = 30
UMBRAL_TENDENCIA = 0.2   # +20% o más = "Subiendo" | -20% o menos = "Bajando" | entre medio = "Estable"
