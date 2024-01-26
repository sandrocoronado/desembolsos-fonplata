import streamlit as st
import pandas as pd
import numpy as np
import threading
import io
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt

def dataframe_to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sheet1')
    excel_bytes = output.getvalue()
    return excel_bytes

# Configuración inicial
LOGGER = st.logger.get_logger(__name__)
_lock = threading.Lock()

# URLs de las hojas de Google Sheets
sheet_url_proyectos = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHedheaRLyqnjwtsRvlBFFOnzhfarkFMoJ04chQbKZCBRZXh_2REE3cmsRC69GwsUK0PoOVv95xptX/pub?gid=2084477941&single=true&output=csv"
sheet_url_operaciones = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHedheaRLyqnjwtsRvlBFFOnzhfarkFMoJ04chQbKZCBRZXh_2REE3cmsRC69GwsUK0PoOVv95xptX/pub?gid=1468153763&single=true&output=csv"
sheet_url_desembolsos = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHedheaRLyqnjwtsRvlBFFOnzhfarkFMoJ04chQbKZCBRZXh_2REE3cmsRC69GwsUK0PoOVv95xptX/pub?gid=1657640798&single=true&output=csv"

st.title("Análisis de Desembolsos por Proyecto")

def load_data(url):
    with _lock:
        return pd.read_csv(url)
    
def clean_and_convert_to_float(monto_str):
    if pd.isna(monto_str):
        return np.nan
    try:
        # Asumiendo que 'monto_str' es una cadena, remover puntos de los miles y cambiar comas por puntos para decimales
        cleaned_monto = monto_str.replace('.', '').replace(',', '.')
        return float(cleaned_monto)
    except ValueError:
        # Si hay un error en la conversión, retorna NaN
        return np.nan


def process_data(df_proyectos, df_operaciones, df_operaciones_desembolsos):

    # Aplicar la función de limpieza a la columna 'Monto'
    df_operaciones_desembolsos['Monto'] = df_operaciones_desembolsos['Monto'].apply(clean_and_convert_to_float)
    df_operaciones['AporteFONPLATAVigente'] = df_operaciones['AporteFONPLATAVigente'].apply(clean_and_convert_to_float)

    df_proyectos = df_proyectos[['NoProyecto', 'IDAreaPrioritaria','AreaPrioritaria','IDAreaIntervencion','AreaIntervencion']]
    df_operaciones = df_operaciones[['NoProyecto', 'NoOperacion', 'IDEtapa', 'Alias', 'Pais', 'FechaVigencia', 'Estado', 'AporteFONPLATAVigente']]
    df_operaciones_desembolsos = df_operaciones_desembolsos[['IDDesembolso', 'IDOperacion', 'Monto', 'FechaEfectiva']]

    merged_df = pd.merge(df_operaciones_desembolsos, df_operaciones, left_on='IDOperacion', right_on='IDEtapa', how='left')
    merged_df = pd.merge(merged_df, df_proyectos, on='NoProyecto', how='left')

    merged_df['FechaEfectiva'] = pd.to_datetime(merged_df['FechaEfectiva'], dayfirst=True, errors='coerce')
    merged_df['FechaVigencia'] = pd.to_datetime(merged_df['FechaVigencia'], dayfirst=True, errors='coerce')
    merged_df['Ano'] = ((merged_df['FechaEfectiva'] - merged_df['FechaVigencia']).dt.days / 366).fillna(-1)
    merged_df['Ano'] = merged_df['Ano'].astype(int)
    
    # Convierte las columnas 'Monto' y 'AporteFONPLATAVigente' a numéricas
    merged_df['Monto'] = pd.to_numeric(merged_df['Monto'], errors='coerce')
    merged_df['AporteFONPLATAVigente'] = pd.to_numeric(merged_df['AporteFONPLATAVigente'], errors='coerce')
    
    merged_df['Porcentaje'] = ((merged_df['Monto'] / merged_df['AporteFONPLATAVigente']) * 100).round(2)
    merged_df['Monto'] = (merged_df['Monto']/1000).round(0)

    return merged_df[merged_df['Ano'] >= 0]

def create_pivot_table(filtered_df, value_column):
    pivot_table = pd.pivot_table(filtered_df, values=value_column, index='IDEtapa', columns='Ano', aggfunc='sum', fill_value=0)
    
    pivot_table['Total'] = pivot_table.sum(axis=1).round(0)
    
    return pivot_table

exclude_IDEtapa = [
    "AR030_1", "UR018_1", "UR021_1", "UR022_1", "UR023_1", 
    "AR031_1", "AR031_2", "AR033_1", "AR044_1", "AR044_2", 
    "AR046_1", "BO030_1", "BO032_1", "UR019_1", "AR038_1", 
    "AR043_1", "AR043_2"
]

# Función para excluir IDEtapa específicos del DataFrame
def exclude_IDEtapa_from_df(df, exclude_list):
    return df[~df['IDEtapa'].isin(exclude_list)]

# Función para realizar la regresión polinómica de grado 3
def perform_regression(df):
    X = df[['Año']].values
    y = df['PorcentajeAcumulado'].values
    poly_features = PolynomialFeatures(degree=3)
    X_poly = poly_features.fit_transform(X)
    poly_model = LinearRegression()
    poly_model.fit(X_poly, y)
    r2_poly = r2_score(y, poly_model.predict(X_poly))
    return poly_model, r2_poly, X, y

def plot_regression_results(X, y, poly_model):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(X, y, color='blue', label='Datos Reales')
    ax.plot(X, poly_model.predict(PolynomialFeatures(degree=3).fit_transform(X)), color='green', label='Línea de Regresión Polinómica')
    ax.set_xlabel('Año')
    ax.set_ylabel('Porcentaje Acumulado')
    ax.legend()
    return fig


def run():
    df_proyectos = load_data(sheet_url_proyectos)
    df_operaciones = load_data(sheet_url_operaciones)
    df_operaciones_desembolsos = load_data(sheet_url_desembolsos)

    processed_data = process_data(df_proyectos, df_operaciones, df_operaciones_desembolsos)

    # Agregar un filtro multiselect para los países con la opción "Todos"
    paises_disponibles = processed_data['Pais'].unique()  # Obtiene una lista de todos los países únicos
    paises_disponibles = np.insert(paises_disponibles, 0, "Todos")  # Agrega "Todos" al inicio de la lista
    paises_seleccionados = st.multiselect('Seleccionar Países', paises_disponibles, default="Todos")

    # Si se selecciona "Todos", se seleccionan todos los países
    if "Todos" in paises_seleccionados:
        filtered_data = processed_data
    else:
        filtered_data = processed_data[processed_data['Pais'].isin(paises_seleccionados)]

    # Crear y mostrar la tabla pivote de Monto
    pivot_table_monto = create_pivot_table(filtered_data, 'Monto')
    st.write("Tabla Pivote de Monto de Desembolsos por Proyecto y Año")
    st.dataframe(pivot_table_monto)

    # Convertir el DataFrame a bytes y agregar botón de descarga para ambas tablas
    excel_bytes_monto = dataframe_to_excel_bytes(pivot_table_monto)
    st.download_button(
        label="Descargar DataFrame en Excel (Monto)",
        data=excel_bytes_monto,
        file_name="matriz_monto_desembolsos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Crear y mostrar la tabla pivote de Porcentaje
    pivot_table_porcentaje = create_pivot_table(filtered_data, 'Porcentaje')
    st.write("Tabla Pivote de Porcentaje de Desembolsos por Proyecto y Año")
    st.dataframe(pivot_table_porcentaje)

    excel_bytes_porcentaje = dataframe_to_excel_bytes(pivot_table_porcentaje)
    st.download_button(
        label="Descargar DataFrame en Excel (Porcentaje)",
        data=excel_bytes_porcentaje,
        file_name="matriz_porcentaje_desembolsos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    porcentaje_pivot = pivot_table_porcentaje

    # Eliminar la columna 'Total' si existe
    if 'Total' in pivot_table_porcentaje.columns:
        pivot_table_porcentaje = pivot_table_porcentaje.drop(columns=['Total'])

    # Calcular los porcentajes acumulados por proyecto.
    cumulative_percentages = pivot_table_porcentaje.cumsum(axis=1)

    # Transformar la tabla de porcentajes acumulados en formato largo.
    df_long_format = cumulative_percentages.reset_index().melt(id_vars='IDEtapa', var_name='Año', value_name='PorcentajeAcumulado')

    # Filtrar filas donde el porcentaje acumulado es mayor a 0.
    df_long_format = df_long_format[df_long_format['PorcentajeAcumulado'] > 0]

    # Primero, filtrar para incluir solo los IDEtapa deseados
    include_IDEtapa = [
        "AR030_1", "AR031_2", "AR033_1", "AR038_1", "AR043_1", "AR043_2", "AR044_1",
        "UR018_1", "UR021_1", "UR022_1", "UR023_1", "AR031_1", "AR044_2", "AR046_1",
        "AR048_1", "BO024_1", "BO030_1", "BO032_1", "PY016_2", "UR019_1", "AR020_1",
        "AR026_1", "AR040_1", "BO020_1", "BO023_1", "BO029_1", "BR025_1", "PY021_1",
        "PY026_1", "UR016_1", "UR017_1", "UR020_1", "AR019_1", "AR022_1", "AR027_1",
        "BO025_1", "BO032_2", "PY020_2", "AR021_1", "AR024_1", "AR037_1", "PY020_1",
        "AR025_1", "AR028_1", "BO028_1", "BR016_1", "BO021_1", "BO022_1", "UR014_1"
    ]
    filtered_df = df_long_format[df_long_format['IDEtapa'].isin(include_IDEtapa)]

    # Luego, excluir los IDEtapa específicos del conjunto ya filtrado
    exclude_IDEtapa = [
        "AR030_1", "UR018_1", "UR021_1", "UR022_1", "UR023_1", "AR031_1", "AR031_2",
        "AR033_1", "AR044_1", "AR044_2", "AR046_1", "BO030_1", "BO032_1", "UR019_1",
        "AR038_1", "AR043_1", "AR043_2"
    ]
    final_df = exclude_IDEtapa_from_df(filtered_df, exclude_IDEtapa)

    # Realizar regresión polinómica de grado 3 con el DataFrame final
    poly_model, r2_poly, X, y = perform_regression(final_df)

    # Mostrar R^2 y gráfico de regresión
    st.write("Coeficiente de Determinación (R^2) para la Regresión Polinómica: ", r2_poly)
    fig = plot_regression_results(X, y, poly_model)
    st.pyplot(fig)

    # Botón para descargar los datos de regresión en Excel
    excel_bytes = dataframe_to_excel_bytes(final_df)
    st.download_button(
        label="Descargar datos de regresión en Excel",
        data=excel_bytes,
        file_name="datos_regresion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    run()