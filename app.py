import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(layout="wide")

st.markdown("""
<style>
    .stDataFrame { font-size: 0.8rem; }
    .stDataFrame th, .stDataFrame td { padding: 4px 5px; }
    .streamlit-expander .stDataFrame { font-size: 0.8rem; }
    .streamlit-expander .stDataFrame th, .streamlit-expander .stDataFrame td { padding: 4px 5px; }
</style>
""", unsafe_allow_html=True)

st.title('📱 재고 현황')

DB_URL = os.environ.get('DATABASE_URL')

if DB_URL:
    DB_URL = DB_URL.strip()
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

@st.cache_data(ttl=600)
def load_data_from_db():
    if not DB_URL:
        st.error("데이터베이스 URL을 찾을 수 없습니다. Render 환경 변수가 올바르게 설정되었는지 확인하세요.")
        return None
    try:
        conn = st.connection('db', type='sql', url=DB_URL)
        df = conn.query('SELECT * FROM inventory_data')
        
        all_groups = df['영업그룹'].unique()
        custom_order = ['부산', '울산', '경남', '대구', '경주포항', '구미']
        remaining_groups = sorted([g for g in all_groups if g not in custom_order])
        final_order = custom_order + remaining_groups
        df['영업그룹'] = pd.Categorical(df['영업그룹'], categories=final_order, ordered=True)
        return df
    except Exception as e:
        st.error(f"데이터베이스 연결에 실패했습니다: {e}")
        return None

df = load_data_from_db()

if df is None:
    st.stop()

st.sidebar.header('필터')

group_options = df['영업그룹'].cat.categories.tolist()
selected_groups = st.sidebar.multiselect('영업그룹', group_options, default=group_options)

available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
selected_personnel = st.sidebar.multiselect('담당', available_personnel, default=available_personnel)

df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

st.header('📊 모델별(상위 20개)')
# groupby에 observed=True 추가
model_summary = df_filtered.groupby('모델명', observed=True).agg(
    재고수량=('재고수량', 'sum'),
    판매수량=('판매수량', 'sum')
).sort_values(by='판매수량', ascending=False)

total_volume_summary = model_summary['재고수량'] + model_summary['판매수량']
model_summary['재고회전율'] = np.divide(model_summary['판매수량'], total_volume_summary, out=np.zeros_like(total_volume_summary, dtype=float), where=total_volume_summary!=0).apply(lambda x: f"{x:.2%}")

top_20_summary = model_summary.head(20).reset_index()

if 'clicked_model' not in st.session_state: st.session_state.clicked_model = None

header_cols = st.columns((3, 1, 1, 1, 1.5))
headers = ['모델명', '재고', '판매', '회전율', '상세보기']
for col, header in zip(header_cols, headers):
    col.markdown(f'**{header}**')

for idx, row in top_20_summary.iterrows():
    row_cols = st.columns((3, 1, 1, 1, 1.5))
    row_cols[0].write(row['모델명'])
    row_cols[1].write(row['재고수량'])
    row_cols[2].write(row['판매수량'])
    row_cols[3].write(row['재고회전율'])
    if row_cols[4].button('상세보기', key=f"detail_btn_{idx}"):
        st.session_state.clicked_model = row['모델명']
        st.rerun()

st.header('🔎 상세 검색')
show_color = st.checkbox("색상별 상세 보기")

default_selection = [st.session_state.clicked_model] if st.session_state.clicked_model else []
# groupby에 observed=True 추가
inventory_sorted_models = df.groupby('모델명', observed=True)['재고수량'].sum().sort_values(ascending=False).index.tolist()
selected_models = st.multiselect("모델명을 선택하세요", inventory_sorted_models, default=default_selection)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    grouping_cols = ['모델명', '단말기색상', '영업그룹'] if show_color else ['모델명', '영업그룹']
    # groupby에 observed=True 추가
    detail_agg = detail_summary.groupby(grouping_cols, observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
    total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
    detail_agg['재고회전율'] = (detail_agg['판매수량'] / total_agg).apply(lambda x: f"{x:.2%}")
    
    detail_agg['영업그룹'] = pd.Categorical(detail_agg['영업그룹'], categories=df['영업그룹'].cat.categories, ordered=True)
    
    if show_color:
        sorted_detail_agg = detail_agg.sort_values(by=['모델명', '단말기색상', '영업그룹'])
    else:
        sorted_detail_agg = detail_agg.sort_values(by=['영업그룹', '판매수량'], ascending=[True, False])
        
    st.markdown(sorted_detail_agg.to_html(index=False), unsafe_allow_html=True)

st.header('📄 그룹,담당,판매점별')

for group in [g for g in group_options if g in df_filtered['영업그룹'].unique()]:
    df_group = df_filtered[df_filtered['영업그룹'] == group]
    group_stock = df_group['재고수량'].sum(); group_sales = df_group['판매수량'].sum()
    group_turnover = (group_sales / (group_stock + group_sales)) if (group_stock + group_sales) > 0 else 0
    
    with st.expander(f"🏢 **영업그룹: {group}** (재고: {group_stock}, 판매: {group_sales}, 회전율: {group_turnover:.2%})"):
        # groupby에 observed=True 추가
        person_summary = df_group.groupby('담당', observed=True)['판매수량'].sum().sort_values(ascending=False).reset_index()
        
        for person_name in person_summary['담당']:
            df_person = df_group[df_group['담당'] == person_name]
            person_stock = df_person['재고수량'].sum(); person_sales = df_person['판매수량'].sum()
            person_turnover = (person_sales / (person_stock + person_sales)) if (person_stock + person_sales) > 0 else 0
            
            with st.expander(f"👤 **담당: {person_name}** (재고: {person_stock}, 판매: {person_sales}, 회전율: {person_turnover:.2%})"):
                # groupby에 observed=True 추가
                df_store = df_person.groupby('출고처', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                df_store = df_store.sort_values(by='판매수량', ascending=False)
                
                store_total = df_store['재고수량'] + df_store['판매수량']
                df_store['재고회전율'] = (df_store['판매수량'] / store_total).apply(lambda x: f"{x:.2%}")

                for idx, row in df_store.iterrows():
                    with st.expander(f"🏪 **판매점: {row['출고처']}** (재고: {row['재고수량']}, 판매: {row['판매수량']}, 회전율: {row['재고회전율']})"):
                        df_model = df_person[df_person['출고처'] == row['출고처']]
                        # groupby에 observed=True 추가
                        model_detail = df_model.groupby('모델명', observed=True).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                        model_detail = model_detail.sort_values(by='판매수량', ascending=False)
                        
                        model_total = model_detail['재고수량'] + model_detail['판매수량']
                        model_detail['재고회전율'] = (model_detail['판매수량'] / model_total).apply(lambda x: f"{x:.2%}")
                        st.markdown(model_detail.to_html(index=False), unsafe_allow_html=True)
