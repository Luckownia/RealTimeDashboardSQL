import mysql.connector
from mysql.connector import Error
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objs as go
from streamlit_autorefresh import st_autorefresh
import requests

# Konfiguracja bazy danych MySQL
DATABASE_CONFIG = {
    'host': 'sql7.freemysqlhosting.net',
    'user': 'sql7754888',
    'password': 'iUEct2Tcu8',
    'database': 'sql7754888'
}

# Coinbase API Endpoint
COINBASE_URL = "https://api.coinbase.com/v2/exchange-rates"
MAX_POINTS = 20

# Funkcja do nawiązywania połączenia z bazą danych
def connect_to_database():
    try:
        connection = mysql.connector.connect(**DATABASE_CONFIG)
        return connection
    except Error as e:
        st.error(f"Błąd podczas łączenia z bazą danych: {e}")
        return None

# Funkcja do generowania losowych danych
def generate_random_data():
    current_time = datetime.datetime.now()
    return pd.DataFrame({
        'Time': [current_time],
        'Value': [round(np.random.uniform(0, 100), 2)]
    })

# Funkcja do pobierania danych z bazy SQL
def fetch_data_from_sql(query):
    connection = connect_to_database()
    if connection is None:
        return pd.DataFrame()  # Pusta DataFrame w razie błędu
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        connection.close()
        return pd.DataFrame(rows)
    except Error as e:
        st.error(f"Błąd podczas wykonywania zapytania: {e}")
        return pd.DataFrame()

# Funkcja do zapisu danych do bazy SQL
def save_data_to_sql(data, table_name):
    connection = connect_to_database()
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        for _, row in data.iterrows():
            query = f"INSERT INTO {table_name} (Time, Value) VALUES (%s, %s)"
            cursor.execute(query, (row['Time'], row['Value']))
        connection.commit()
        connection.close()
    except Error as e:
        st.error(f"Błąd podczas zapisywania danych: {e}")

# Funkcja do pobierania ceny Bitcoina w euro
def get_bitcoin_price_in_euro():
    params = {"currency": "BTC"}
    response = requests.get(COINBASE_URL, params=params)
    data = response.json()
    return float(data["data"]["rates"].get("EUR", None))  # Zwraca cenę w EUR lub None, jeśli brak danych

# Funkcja do inicjalizacji danych w `st.session_state`
def initialize_session_state():
    if "data_generated" not in st.session_state:
        st.session_state["data_generated"] = pd.DataFrame(columns=['Time', 'Value'])
    if "data_stock" not in st.session_state:
        st.session_state["data_stock"] = pd.DataFrame(columns=['Time', 'Value'])


# Inicjalizacja danych
initialize_session_state()

# Streamlit interfejs
st.title("Real-Time Data Dashboard")

# Generowanie i wizualizacja losowych danych
generated_container = st.container()
with generated_container:
    st.header("Generated Data")
    new_generated_row = generate_random_data()
    st.session_state["data_generated"] = pd.concat(
        [st.session_state["data_generated"], new_generated_row], ignore_index=True
    )
    if len(st.session_state["data_generated"]) > MAX_POINTS:
        st.session_state["data_generated"] = st.session_state["data_generated"].tail(MAX_POINTS)

    # Zapis do bazy danych
    save_data_to_sql(new_generated_row, 'real_time_data')

    # Wizualizacja danych
    fig_generated = go.Figure()
    fig_generated.add_trace(go.Scatter(
        x=st.session_state["data_generated"]['Time'],
        y=st.session_state["data_generated"]['Value'],
        mode='lines+markers',
        name='Generated Data'
    ))
    fig_generated.update_layout(
        title="Generated Data Visualization",
        xaxis_title="Time",
        yaxis_title="Value"
    )
    st.plotly_chart(fig_generated)

# Pobieranie i wizualizacja danych z bazy
database_container = st.container()
with database_container:
    st.header("Database Data")
    data_db = fetch_data_from_sql("SELECT * FROM real_time_data")
    if len(data_db) > MAX_POINTS:
        data_db = data_db.tail(MAX_POINTS)

    fig_db = go.Figure()
    fig_db.add_trace(go.Scatter(
        x=data_db['Time'],
        y=data_db['Value'],
        mode='lines+markers',
        name='Database Data'
    ))
    fig_db.update_layout(
        title="Database Data Visualization",
        xaxis_title="Time",
        yaxis_title="Value"
    )
    st.plotly_chart(fig_db)

# Sekcja: Stock Data (Bitcoin in EUR)
stock_container = st.container()
with stock_container:
    st.header("Bitcoin Price in EUR")

    # Pobierz bieżący czas
    current_time = datetime.datetime.now()

    # Pobranie ceny Bitcoina z API
    price_in_euro = get_bitcoin_price_in_euro()

    # Jeśli API nie zwróciło danych, użyj ostatniej znanej wartości
    if price_in_euro is None:
        if len(st.session_state["data_stock"]) > 0:
            price_in_euro = st.session_state["data_stock"]["Value"].iloc[-1]
        else:
            price_in_euro = 0  # Domyślna wartość, jeśli nie ma historii

    # Dodanie nowego rekordu do danych w sesji
    new_stock_row = pd.DataFrame({
        'Time': [current_time],
        'Value': [price_in_euro]
    })

    # Aktualizacja danych w sesji
    st.session_state["data_stock"] = pd.concat(
        [st.session_state["data_stock"], new_stock_row],
        ignore_index=True
    )

    # Utrzymanie maksymalnej liczby punktów na wykresie
    if len(st.session_state["data_stock"]) > MAX_POINTS:
        st.session_state["data_stock"] = st.session_state["data_stock"].tail(MAX_POINTS)

    # Rysowanie wykresu
    fig_stock = go.Figure()
    fig_stock.add_trace(go.Scatter(
        x=st.session_state["data_stock"]['Time'],
        y=st.session_state["data_stock"]['Value'],
        mode='lines+markers',
        name='Bitcoin Price in EUR'
    ))
    fig_stock.update_layout(
        title="Bitcoin Price Visualization",
        xaxis_title="Time",
        yaxis_title="Price (EUR)"
    )
    st.plotly_chart(fig_stock, use_container_width=True)

# Wymuszenie odświeżania co 1 sekundę
st_autorefresh(interval=1000, limit=None, key="btc_refresh")

