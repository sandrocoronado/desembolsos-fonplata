import streamlit as st
import pandas as pd
import numpy as np
import threading
import io

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
    st.write(merged_df)

    # Convertir la columna 'FechaEfectiva' al formato de fecha y hora
    merged_df['FechaEfectiva'] = pd.to_datetime(merged_df['FechaEfectiva'])

    # Extraer el año y el mes de la columna 'FechaEfectiva'
    merged_df['Año'] = merged_df['FechaEfectiva'].dt.year
    merged_df['Mes'] = merged_df['FechaEfectiva'].dt.month

    # Crear un selector para filtrar por año
    año_seleccionado = st.selectbox(
        'Selecciona un año', 
        options=np.sort(merged_df['Año'].unique())
    )

    # Filtrar el DataFrame por el año seleccionado
    df_filtrado_por_año = merged_df[merged_df['Año'] == año_seleccionado]

    # Crear un slider para seleccionar el mes
    mes_seleccionado = st.slider(
        'Selecciona un mes', 
        min_value=1, 
        max_value=12, 
        value=1
    )

    # Filtrar el DataFrame por el mes seleccionado
    df_filtrado = df_filtrado_por_año[df_filtrado_por_año['Mes'] == mes_seleccionado]


    resumen_df = merged_df.groupby('IDAreaPrioritaria').agg(
    Proyectos=('IDEtapa', 'nunique'),  # Cuenta el número único de IDEtapa
    Suma_Monto=('Monto', 'sum')        # Suma de Monto
).reset_index()

    # Agregar fila de Totales a resumen_df
    total_proyectos = resumen_df['Proyectos'].sum()
    total_suma_monto = resumen_df['Suma_Monto'].sum()
    total_resumen_df = pd.DataFrame({'IDAreaPrioritaria': ['Total'], 'Proyectos': [total_proyectos], 'Suma_Monto': [total_suma_monto]})
    resumen_df = pd.concat([resumen_df, total_resumen_df], ignore_index=True)
    st.write(resumen_df)
    
    # Creación del resumen por área de intervención
    resumen_intervencion_total_df = merged_df.groupby('IDAreaIntervencion').agg(
        Proyectos_Unicos=('IDEtapa', 'nunique'),
        Suma_Monto=('Monto', 'sum')
    ).reset_index()

    # Agregar fila de Totales a resumen_intervencion_total_df
    total_proyectos_unicos = resumen_intervencion_total_df['Proyectos_Unicos'].sum()
    total_suma_monto_intervencion = resumen_intervencion_total_df['Suma_Monto'].sum()
    total_resumen_intervencion_df = pd.DataFrame({'IDAreaIntervencion': ['Total'], 'Proyectos_Unicos': [total_proyectos_unicos], 'Suma_Monto': [total_suma_monto_intervencion]})
    resumen_intervencion_total_df = pd.concat([resumen_intervencion_total_df, total_resumen_intervencion_df], ignore_index=True)
    st.write(resumen_intervencion_total_df)

    return merged_df[merged_df['Ano'] >= 0]

df_proyectos = load_data(sheet_url_proyectos)
df_operaciones = load_data(sheet_url_operaciones)
df_operaciones_desembolsos = load_data(sheet_url_desembolsos)

processed_data = process_data(df_proyectos, df_operaciones, df_operaciones_desembolsos)