import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="SMART MONEY DASHBOARD - COT API", layout="wide")
st.title("🏆 SMART MONEY DASHBOARD - Atualização Automática via API CFTC")

# 🗺️ Lista de ativos disponíveis
ativos_disponiveis = {
    "GOLD": "GOLD",
    "EURO (EUR/USD)": "EURO FX",
    "SP500": "E-MINI S&P 500",
    "DOW JONES (US30)": "DJIA",
    "NASDAQ (USTEC)": "E-MINI NASDAQ 100",
    "PETRÓLEO (WTI)": "CRUDE OIL",
    "BTC (Bitcoin)": "BITCOIN",
    "YEN": "JAPANESE YEN",
    "BRL (Dólar x Real)": "BRAZILIAN REAL",
    "HK50 (Hang Seng)": None  # ✅ Adiciona HK50 como placeholder
}

# 🎯 Seleção de ativo e período
col1, col2 = st.columns(2)
ativo_selecionado = col1.selectbox("🪙 Escolha o ativo:", list(ativos_disponiveis.keys()), index=0)
num_semanas = col2.slider("📅 Quantidade de semanas:", min_value=4, max_value=52, value=30, step=2)

# 🚀 Função para buscar dados
@st.cache_data(ttl=3600*24)
def buscar_dados_cot(ativo_nome):
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$order=report_date_as_yyyy_mm_dd DESC&$limit=1000"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Erro na requisição da API: {e}")
        return None

    dados = pd.DataFrame(response.json())

    # 🔍 Filtrar ativo
    df = dados[dados['market_and_exchange_names'].str.contains(ativo_nome, case=False, na=False)]

    if df.empty:
        st.error(f"❌ Nenhum dado encontrado para {ativo_nome}.")
        return None

    df['Data'] = pd.to_datetime(df['report_date_as_yyyy_mm_dd'])
    df['Longs'] = df['noncomm_positions_long_all'].astype(int)
    df['Shorts'] = df['noncomm_positions_short_all'].astype(int)
    df['Open Interest'] = df['open_interest_all'].astype(int)

    # 🔥 Agrupar por data
    df = df.groupby('Data').agg({
        'Longs': 'sum',
        'Shorts': 'sum',
        'Open Interest': 'sum'
    }).reset_index()

    # 📈 Cálculos
    df['Líquida'] = df['Longs'] - df['Shorts']
    df = df.sort_values('Data', ascending=False).head(num_semanas)
    df['Mudança'] = df['Líquida'].diff().fillna(0).astype(int)

    return df.sort_values('Data')

# 🚦 Verificar HK50
if ativos_disponiveis[ativo_selecionado] is None:
    st.warning("⚠️ O índice **HK50 (Hang Seng)** não está disponível no relatório COT da CFTC, pois é um mercado asiático. Dados não encontrados.")
else:
    # 🔄 Carregar dados
    df = buscar_dados_cot(ativos_disponiveis[ativo_selecionado])

    if df is not None:
        st.subheader(f"📊 Últimos {num_semanas} Relatórios COT - {ativo_selecionado}")

        # 🧠 Interpretação automática
        ultima_liquida = df['Líquida'].iloc[-1]
        mudanca = df['Mudança'].iloc[-1]

        interpretacao = ""
        if ultima_liquida > 0:
            interpretacao += "🟢 **Os Não Comerciais estão NET COMPRADOS.** "
        elif ultima_liquida < 0:
            interpretacao += "🔴 **Os Não Comerciais estão NET VENDIDOS.** "
        else:
            interpretacao += "⚪ **Posição líquida neutra.** "

        if mudanca > 0:
            interpretacao += f"✅ Nesta semana, **aumentaram {mudanca:,} contratos líquidos na direção COMPRADA.**"
        elif mudanca < 0:
            interpretacao += f"⚠️ Nesta semana, **reduziram {abs(mudanca):,} contratos líquidos, favorecendo a VENDA.**"
        else:
            interpretacao += "➖ **Nenhuma variação significativa nesta semana.**"

        st.info(interpretacao)

        # 🚦 Métricas rápidas
        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 Posição Líquida Atual", f"{ultima_liquida:,}")
        col2.metric("📈 Mudança na Semana", f"{mudanca:,}")
        col3.metric("📅 Última Data", df['Data'].iloc[-1].strftime('%d/%m/%Y'))

        # 🎨 Formatação da tabela
        def formatar(x):
            return f"{x/1000:.1f}k"

        df_exibir = df.copy()
        df_exibir['Longs'] = df_exibir['Longs'].apply(formatar)
        df_exibir['Shorts'] = df_exibir['Shorts'].apply(formatar)
        df_exibir['Open Interest'] = df_exibir['Open Interest'].apply(formatar)
        df_exibir['Líquida'] = df_exibir['Líquida'].apply(lambda x: f"🟢 +{formatar(x)}" if x > 0 else f"🔴 {formatar(x)}")
        df_exibir['Mudança'] = df_exibir['Mudança'].apply(lambda x: f"📈 +{formatar(x)}" if x > 0 else (f"📉 {formatar(x)}" if x < 0 else "0"))

        st.dataframe(
            df_exibir.style
            .set_table_styles(
                [{'selector': 'thead th', 'props': [('background-color', '#002b36'), ('color', 'white')]}]
            )
            .applymap(lambda v: 'color: green' if isinstance(v, str) and ('+' in v or '📈' in v) else
                      ('color: red' if isinstance(v, str) and ('-' in v or '📉' in v) else '')),
            use_container_width=True
        )

        # 📈 Gráfico de Posição Líquida
        st.subheader(f"📈 Evolução da Posição Líquida dos Não Comerciais - {ativo_selecionado}")
        fig = px.line(
            df,
            x='Data',
            y='Líquida',
            markers=True,
            title=f'Evolução da Posição Líquida (Últimas {num_semanas} Semanas)',
            labels={'Líquida': 'Posição Líquida', 'Data': 'Data'}
        )
        fig.update_traces(line_color='#FFD700')
        fig.update_layout(title_x=0.1)
        st.plotly_chart(fig, use_container_width=True)

        # 📥 Download CSV
        st.download_button(
            label="📥 Baixar CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f'cot_{ativo_selecionado.lower().replace(" ", "_")}.csv',
            mime='text/csv',
        )
    else:
        st.warning("❌ Não foi possível carregar os dados da API.")
