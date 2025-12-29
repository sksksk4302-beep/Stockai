import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from bigquery_client import BigQueryClient
import config

# 페이지 설정
st.set_page_config(page_title="Stock AI Dashboard", layout="wide")

@st.cache_resource
def get_bq_client():
    return BigQueryClient()

@st.cache_data(ttl=3600)
def load_data(ticker=None):
    bq_client = get_bq_client()
    if ticker:
        query = f"SELECT * FROM `{config.PROJECT_ID}.{config.BQ_DATASET_NAME}.stock_daily_kr` WHERE `종목코드` = '{ticker}' ORDER BY `날짜` ASC"
    else:
        query = f"SELECT DISTINCT `종목코드`, `종목명` FROM `{config.PROJECT_ID}.{config.BQ_DATASET_NAME}.stock_daily_kr` ORDER BY `종목명`"
    
    return pd.read_gbq(query, project_id=config.PROJECT_ID)

def main():
    st.title("📈 Stock AI Bot Dashboard")
    st.markdown("BigQuery 데이터를 활용한 인터랙티브 주식 분석 대시보드입니다.")

    # 사이드바: 종목 선택
    st.sidebar.header("설정")
    with st.spinner("종목 목록 로딩 중..."):
        tickers_df = load_data()
        ticker_options = {f"{row['종목명']} ({row['종목코드']})": row['종목코드'] for _, row in tickers_df.iterrows()}
        selected_label = st.sidebar.selectbox("종목 선택", options=list(ticker_options.keys()))
        selected_ticker = ticker_options[selected_label]

    # 데이터 로딩
    with st.spinner(f"{selected_label} 데이터 불러오는 중..."):
        df = load_data(selected_ticker)
        df['날짜'] = pd.to_datetime(df['날짜'])

    if df.empty:
        st.warning("데이터가 없습니다.")
        return

    # 메인 화면: 지표 요약
    last_row = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"{int(last_row['종가']):,}원", f"{int(last_row['전일대비']):,}원")
    col2.metric("RSI", f"{last_row['RSI']:.2f}")
    col3.metric("거래량", f"{int(last_row['거래량']):,}")
    col4.metric("외인순매수", f"{int(last_row['외국인순매수']):,}만")

    # 차트: 종가 및 볼린저 밴드
    st.subheader("주가 추이 및 기술적 지표")
    
    fig = go.Figure()

    # 종가 라인
    fig.add_trace(go.Scatter(x=df['날짜'], y=df['종가'], name="종가", line=dict(color='royalblue', width=2)))

    # 볼린저 밴드
    if '볼린저상단' in df.columns and not df['볼린저상단'].isnull().all():
        fig.add_trace(go.Scatter(x=df['날짜'], y=df['볼린저상단'], name="BB 상단", line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash')))
        fig.add_trace(go.Scatter(x=df['날짜'], y=df['볼린저하단'], name="BB 하단", line=dict(color='rgba(173, 216, 230, 0.5)', dash='dash'), fill='tonexty'))

    # 이동평균선
    if '이평20일' in df.columns:
        fig.add_trace(go.Scatter(x=df['날짜'], y=df['이평20일'], name="MA20", line=dict(color='orange', width=1)))

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="날짜",
        yaxis_title="가격",
        height=600,
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 하단 데이터 테이블
    with st.expander("상세 데이터 보기"):
        st.dataframe(df.sort_values(by='날짜', ascending=False))

if __name__ == "__main__":
    main()
