import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title('📱 재고 현황 대시보드')

# Render 환경 변수에서 데이터베이스 URL 가져오기
DB_URL = os.environ.get('DATABASE_URL')

# 데이터베이스 연결
try:
    conn = st.connection('db', type='sql', url=DB_URL)
    df = conn.query('SELECT * FROM inventory_data', ttl=600) # 10분마다 데이터 새로고침
except Exception as e:
    st.error(f"데이터베이스 연결에 실패했습니다. 관리자가 데이터를 업로드했는지 확인하세요. 오류: {e}")
    st.stop() # 데이터가 없으면 앱 실행 중지

# --- 이하 대시보드 UI는 이전과 거의 동일 ---
st.sidebar.header('필터')

group_options = df['영업그룹'].unique()
selected_groups = st.sidebar.multoselect('영업그룹', group_options, default=group_options)

available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
selected_personnel = st.sidebar.multoselect('담당', available_personnel, default=available_personnel)

df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

st.header('📊 모델별 재고/판매 요약')
model_summary = df_filtered.groupby('모델명').agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index().sort_values(by='판매수량', ascending=False)
fig = px.bar(model_summary.head(15), x='모델명', y=['재고수량', '판매수량'], title='모델별 판매 수량 (상위 15개)', barmode='group', text_auto=True)
fig.update_traces(textposition='outside'); st.plotly_chart(fig, use_container_width=True)

st.write("📈 **그래프 모델 바로 조회**")
top_15_models = model_summary.head(15)['모델명'].tolist()
if 'clicked_model' not in st.session_state: st.session_state.clicked_model = None
cols = st.columns(5)
for i, model_name in enumerate(top_15_models):
    if cols[i % 5].button(model_name, key=f"model_btn_{i}"):
        st.session_state.clicked_model = model_name

st.header('🔎 상세 검색')
show_color = st.checkbox("색상별 상세 보기")
default_selection = [st.session_state.clicked_model] if st.session_state.clicked_model else []
all_models = sorted(df['모델명'].unique())
selected_models = st.multoselect("모델명을 선택하세요", all_models, default=default_selection)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    grouping_cols = ['모델명', '단말기색상', '영업그룹'] if show_color else ['모델명', '영업그룹']
    detail_agg = detail_summary.groupby(grouping_cols).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
    total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
    detail_agg['재고회전율'] = (detail_agg['판매수량'] / total_agg).apply(lambda x: f"{x:.2%}")
    st.dataframe(detail_agg.sort_values(by=grouping_cols))

st.header('📄 계층형 상세 데이터 보기')
# ... (계층형 상세 보기 코드는 이전과 동일하게 유지)