import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title('📱 재고 현황 대시보드')

DB_URL = os.environ.get('DATABASE_URL')

if DB_URL:
    DB_URL = DB_URL.strip()
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

try:
    if not DB_URL:
        st.error("데이터베이스 URL을 찾을 수 없습니다. Render 환경 변수가 올바르게 설정되었는지 확인하세요.")
        st.stop()
    
    conn = st.connection('db', type='sql', url=DB_URL)
    df = conn.query('SELECT * FROM inventory_data', ttl=600)

except Exception as e:
    st.error(f"데이터베이스 연결에 실패했습니다. 관리자가 데이터를 업로드했는지 확인하세요.")
    st.stop()

st.sidebar.header('필터')

group_options = df['영업그룹'].unique()
# --- <<< 바로 이 부분의 오타를 수정했습니다! >>> ---
selected_groups = st.sidebar.multiselect('영업그룹', group_options, default=group_options)

available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
# --- <<< 이 부분도 함께 수정했습니다! >>> ---
selected_personnel = st.sidebar.multiselect('담당', available_personnel, default=available_personnel)

df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

# --- 이하 코드는 이전과 동일합니다 ---
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
selected_models = st.multiselect("모델명을 선택하세요", all_models, default=default_selection)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    grouping_cols = ['모델명', '단말기색상', '영업그룹'] if show_color else ['모델명', '영업그룹']
    detail_agg = detail_summary.groupby(grouping_cols).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
    total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
    detail_agg['재고회전율'] = (detail_agg['판매수량'] / total_agg).apply(lambda x: f"{x:.2%}")
    st.dataframe(detail_agg.sort_values(by=grouping_cols))

st.header('📄 계층형 상세 데이터 보기')
# ... (계층형 상세 보기 코드는 이전과 동일하게 유지)
  st.header('📄 계층형 상세 데이터 보기')
        for group in sorted(df_filtered['영업그룹'].unique()):
            df_group = df_filtered[df_filtered['영업그룹'] == group]
            group_stock = df_group['재고수량'].sum()
            group_sales = df_group['판매수량'].sum()
            group_total = group_stock + group_sales
            group_turnover = (group_sales / group_total) if group_total > 0 else 0
            
            with st.expander(f"🏢 영업그룹: {group} (재고: {group_stock}, 판매: {group_sales}, 회전율: {group_turnover:.2%})"):
                for person in sorted(df_group['담당'].unique()):
                    df_person = df_group[df_group['담당'] == person]
                    person_stock = df_person['재고수량'].sum()
                    person_sales = df_person['판매수량'].sum()
                    person_total = person_stock + person_sales
                    person_turnover = (person_sales / person_total) if person_total > 0 else 0
                    
                    with st.container():
                        st.markdown(f"**👤 담당: {person}** (재고: {person_stock}, 판매: {person_sales}, 회전율: {person_turnover:.2%})")
                        
                        if st.button(f"{person} 판매점별 상세 보기", key=f"btn_{group}_{person}"):
                            df_store = df_person.groupby('출고처').agg(
                                재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')
                            ).reset_index()
                            store_total = df_store['재고수량'] + df_store['판매수량']
                            df_store['재고회전율'] = np.divide(df_store['판매수량'], store_total, out=np.zeros_like(store_total, dtype=float), where=store_total!=0)
                            df_store['재고회전율'] = df_store['재고회전율'].apply(lambda x: f"{x:.2%}")
                            st.dataframe(df_store)

else:
    st.info('사이드바에서 재고 및 판매 리스트 CSV 파일을 업로드해주세요.')
