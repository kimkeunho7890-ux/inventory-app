import streamlit as st
import pandas as pd
import numpy as np

# st.set_page_config는 스크립트에서 한 번만 호출할 수 있습니다.
# 이전에 호출된 적이 없다면 여기에 그대로 둡니다.
st.set_page_config(layout="wide")
st.title('📱 재고 현황 대시보드 (최종 완성본)')

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
selected_groups = st.sidebar.multiselect('영업그룹', group_options, default=group_options)

available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
selected_personnel = st.sidebar.multiselect('담당', available_personnel, default=available_personnel)

df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

# --- <<< 그래프 제거 및 상위 20개 테이블로 변경 >>> ---
st.header('📊 모델별 판매 요약 (상위 20개)')
model_summary = df_filtered.groupby('모델명').agg(
    재고수량=('재고수량', 'sum'),
    판매수량=('판매수량', 'sum')
).sort_values(by='판매수량', ascending=False)

# 재고회전율 계산
total_volume_summary = model_summary['재고수량'] + model_summary['판매수량']
model_summary['재고회전율'] = np.divide(model_summary['판매수량'], total_volume_summary, out=np.zeros_like(total_volume_summary, dtype=float), where=total_volume_summary!=0).apply(lambda x: f"{x:.2%}")

# 상위 20개 모델을 테이블로 표시하고, 화면 폭에 맞춤
st.dataframe(model_summary.head(20), use_container_width=True)

# --- <<< 그래프 관련 조회 기능 제거 >>> ---
st.header('🔎 상세 검색')
show_color = st.checkbox("색상별 상세 보기")
all_models = sorted(df['모델명'].unique())
selected_models = st.multiselect("모델명을 선택하세요", all_models)

if selected_models:
    detail_summary = df[df['모델명'].isin(selected_models)]
    grouping_cols = ['모델명', '단말기색상', '영업그룹'] if show_color else ['모델명', '영업그룹']
    detail_agg = detail_summary.groupby(grouping_cols).agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
    total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
    detail_agg['재고회전율'] = (detail_agg['판매수량'] / total_agg).apply(lambda x: f"{x:.2%}")
    
    detail_agg['영업그룹'] = pd.Categorical(detail_agg['영업그룹'], categories=df['영업그룹'].cat.categories, ordered=True)
    # 화면 폭에 맞춤
    st.dataframe(detail_agg.sort_values(by=['영업그룹', '판매수량'], ascending=[True, False]), use_container_width=True)

st.header('📄 계층형 상세 데이터 보기')
group_options_list = df_filtered['영업그룹'].unique().tolist()

for group in group_options_list:
    df_group = df_filtered[df_filtered['영업그룹'] == group]
    group_stock = df_group['재고수량'].sum()
    group_sales = df_group['판매수량'].sum()
    group_turnover = (group_sales / (group_stock + group_sales)) if (group_stock + group_sales) > 0 else 0
    
    with st.expander(f"🏢 **영업그룹: {group}** (재고: {group_stock}, 판매: {group_sales}, 회전율: {group_turnover:.2%})"):
        
        person_summary = df_group.groupby('담당')['판매수량'].sum().sort_values(ascending=False).reset_index()
        
        for person_name in person_summary['담당']:
            df_person = df_group[df_group['담당'] == person_name]
            person_stock = df_person['재고수량'].sum()
            person_sales = df_person['판매수량'].sum()
            person_turnover = (person_sales / (person_stock + person_sales)) if (person_stock + person_sales) > 0 else 0
            
            with st.expander(f"👤 **담당: {person_name}** (재고: {person_stock}, 판매: {person_sales}, 회전율: {person_turnover:.2%})"):
                
                df_store = df_person.groupby('출고처').agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                df_store = df_store.sort_values(by='판매수량', ascending=False)
                
                store_total = df_store['재고수량'] + df_store['판매수량']
                df_store['재고회전율'] = (df_store['판매수량'] / store_total).apply(lambda x: f"{x:.2%}")

                for idx, row in df_store.iterrows():
                    with st.expander(f"🏪 **판매점: {row['출고처']}** (재고: {row['재고수량']}, 판매: {row['판매수량']}, 회전율: {row['재고회전율']})"):
                        df_model = df_person[df_person['출고처'] == row['출고처']]
                        
                        model_detail = df_model.groupby('모델명').agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index()
                        model_detail = model_detail.sort_values(by='판매수량', ascending=False)
                        
                        model_total = model_detail['재고수량'] + model_detail['판매수량']
                        model_detail['재고회전율'] = (model_detail['판매수량'] / model_total).apply(lambda x: f"{x:.2%}")
                        # 화면 폭에 맞춤
                        st.dataframe(model_detail, use_container_width=True)
