import streamlit as st
import altair as alt
import pandas as pd

# Funciones que calculan el PorcentajeAcumulado para cada sector
def calcular_porcentaje_inf(año):
    return 0.0065 * año**4 + 0.286 * año**3 - 6.5063 * año**2 + 40.386 * año + 19.582

def calcular_porcentaje_soc(año):
    return 0.0787 * año**4 - 1.2018 * año**3 + 3.7085 * año**2 + 16.575 * año + 22.619

def calcular_porcentaje_pro(año):
    return 0.1935 * año**3 - 4.3676 * año**2 + 33.192 * año + 13.825

# Título de la aplicación en Streamlit
st.title('Pronóstico de Porcentaje Acumulado por Sector')

# Selección del Sector con la opción "Todos" incluida
sector = st.selectbox('Selecciona el sector del proyecto:', ('Todos', 'INF', 'SOC', 'PRO'))

# Campo para que el usuario ingrese el Año
año_usuario = st.number_input('Introduce el Año para calcular el Porcentaje Acumulado:', min_value=0.0, format='%f')

# Botón para realizar el cálculo
if st.button('Calcular Porcentaje Acumulado'):
    # Cálculo del resultado según el sector seleccionado
    if sector == 'INF':
        resultado = calcular_porcentaje_inf(año_usuario)
    elif sector == 'SOC':
        resultado = calcular_porcentaje_soc(año_usuario)
    elif sector == 'PRO':
        resultado = calcular_porcentaje_pro(año_usuario)
    
    # Mostrar resultado
    st.write(f'El Porcentaje Acumulado pronosticado para el sector {sector} en el año {año_usuario} es: {resultado:.2f}%')

# Genera los datos para los gráficos
def generar_datos():
    años = range(9)  # Del año 0 al 8
    datos = {'Año': [], 'PorcentajeAcumulado': [], 'Sector': []}
    
    for año in años:
        datos['Año'].extend([año]*3)
        datos['PorcentajeAcumulado'].extend([
            calcular_porcentaje_inf(año),
            calcular_porcentaje_soc(año),
            calcular_porcentaje_pro(año)
        ])
        datos['Sector'].extend(['INF', 'SOC', 'PRO'])
    
    return pd.DataFrame(datos)

# Crea el gráfico de líneas con Altair
def crear_grafico(dataframe):
    chart = alt.Chart(dataframe).mark_line(point=True).encode(
        x='Año:O',
        y='PorcentajeAcumulado:Q',
        color='Sector:N',
        tooltip=['Año', 'PorcentajeAcumulado', 'Sector']
    ).interactive().properties(
        width=700,
        height=400
    )
    return chart

# Genera los datos para el DataFrame
def generar_datos_df():
    años = range(9)  # Del año 0 al 9
    datos_inf = [calcular_porcentaje_inf(año) for año in años]
    datos_soc = [calcular_porcentaje_soc(año) for año in años]
    datos_pro = [calcular_porcentaje_pro(año) for año in años]
    
    df = pd.DataFrame({
        'Año': años,
        'INF': datos_inf,
        'SOC': datos_soc,
        'PRO': datos_pro
    })
    
    df = df.round(1)

    return df

# Título de la aplicación en Streamlit
st.title('Pronóstico de Porcentaje Acumulado por Sector')

# Genera los datos y crea el gráfico
datos = generar_datos()
grafico = crear_grafico(datos)

# Muestra el gráfico en la aplicación de Streamlit
st.altair_chart(grafico, use_container_width=True)

# Genera el DataFrame y muestra los datos
df_resultados = generar_datos_df()
st.write("Tendencia de Desembolso en Porcentaje Acumulado por Año y Sector:")
st.dataframe(df_resultados)