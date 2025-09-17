import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 데이터 처리 함수 (v10.0 Final) ---
def process_data(inventory_file, sales_file):
    # 인코딩 처리
    encodings_to_try = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
    inventory_df, sales_df = None, None
    for encoding in encodings_to_try:
        try:
            inventory_file.seek(0)
            inventory_df = pd.read_csv(inventory_file, encoding=encoding)
            break
        except Exception: continue
    for encoding in encodings_to_try:
        try:
            sales_file.seek(0)
            sales_df = pd.read_csv(sales_file, encoding=encoding)
            break
        except Exception: continue

    if inventory_df is None or sales_df is None:
        st.error("지원하는 인코딩으로 파일을 읽는 데 실패했습니다.")
        return None

    try:
        if '담당' not in inventory_df.columns or '담당' not in sales_df.columns:
            st.error("재고/판매리스트 파일에 '담당' 컬럼이 없습니다.")
            return None

        sales_df.columns = sales_df.columns.str.replace('\\n', '', regex=True)
        inventory_df.rename(columns={'색상': '단말기색상'}, inplace=True)
        if inventory_df['출고가'].dtype == 'object':
            inventory_df['출고가'] = inventory_df['출고가'].str.replace(',', '', regex=True).astype(float)

        grouping_cols = ['영업그룹', '담당', '출고처', '모델명', '단말기색상']
        inventory_summary = inventory_df.groupby(grouping_cols).size().reset_index(name='재고수량')
        sales_summary = sales_df.groupby(grouping_cols).size().reset_index(name='판매수량')
        
        df_detailed = pd.merge(inventory_summary, sales_summary, on=grouping_cols, how='outer')
        df_detailed[['재고수량', '판매수량']] = df_detailed[['재고수량', '판매수량']].fillna(0).astype(int)
        
        total_volume = df_detailed['재고수량'] + df_detailed['판매수량']
        df_detailed['재고회전율'] = np.divide(df_detailed['판매수량'], total_volume, out=np.zeros_like(total_volume, dtype=float), where=total_volume!=0)
        
        all_groups = df_detailed['영업그룹'].unique()
        custom_order = ['부산', '울산', '경남', '대구', '경주포항', '구미']
        remaining_groups = sorted([g for g in all_groups if g not in custom_order])
        final_order = custom_order + remaining_groups
        df_detailed['영업그룹'] = pd.Categorical(df_detailed['영업그룹'], categories=final_order, ordered=True)
        
        return df_detailed.sort_values(by='영업그룹')

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None

# --- 웹 애플리케이션 UI (v10.0 Final) ---
st.set_page_config(layout="wide")
st.title('📱 재고 현황 대시보드 (최종 완성본)')

st.sidebar.header('파일 업로드')
inventory_file = st.sidebar.file_uploader("재고리스트.csv", type=['csv'])
sales_file = st.sidebar.file_uploader("판매리스트.csv", type=['csv'])

if inventory_file and sales_file:
    df = process_data(inventory_file, sales_file)

    if df is not None:
        st.sidebar.success("데이터 처리가 완료되었습니다!")
        st.sidebar.header('필터')
        
        group_options = df['영업그룹'].cat.categories.tolist()
        selected_groups = st.sidebar.multiselect('영업그룹', group_options, default=group_options)
        
        available_personnel = df[df['영업그룹'].isin(selected_groups)]['담당'].unique()
        selected_personnel = st.sidebar.multiselect('담당', available_personnel, default=available_personnel)
        
        df_filtered = df[df['영업그룹'].isin(selected_groups) & df['담당'].isin(selected_personnel)]

        st.header('📊 모델별 재고/판매 요약')
        
        model_summary = df_filtered.groupby('모델명').agg(재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')).reset_index().sort_values(by='판매수량', ascending=False)
        
        fig = px.bar(
            model_summary.head(15), x='모델명', y=['재고수량', '판매수량'],
            title='모델별 판매 수량 (상위 15개)', barmode='group', text_auto=True
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        st.write("📈 **그래프 모델 바로 조회**")
        top_15_models = model_summary.head(15)['모델명'].tolist()
        
        if 'clicked_model' not in st.session_state:
            st.session_state.clicked_model = None

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
            
            # --- <<< 체크박스 선택 시 정렬 순서 변경 >>> ---
            if show_color:
                grouping_cols = ['모델명', '단말기색상', '영업그룹']
            else:
                grouping_cols = ['모델명', '영업그룹']

            detail_agg = detail_summary.groupby(grouping_cols).agg(
                재고수량=('재고수량', 'sum'),
                판매수량=('판매수량', 'sum')
            ).reset_index()

            total_agg = detail_agg['재고수량'] + detail_agg['판매수량']
            detail_agg['재고회전율'] = np.divide(detail_agg['판매수량'], total_agg, out=np.zeros_like(total_agg, dtype=float), where=total_agg!=0).apply(lambda x: f"{x:.2%}")
            
            st.dataframe(detail_agg.sort_values(by=grouping_cols))
        
        st.header('📄 계층형 상세 데이터 보기')
        for group in [g for g in group_options if g in df_filtered['영업그룹'].unique()]:
            df_group = df_filtered[df_filtered['영업그룹'] == group]
            group_stock = df_group['재고수량'].sum()
            group_sales = df_group['판매수량'].sum()
            group_turnover = (group_sales / (group_stock + group_sales)) if (group_stock + group_sales) > 0 else 0
            
            with st.expander(f"🏢 **영업그룹: {group}** (재고: {group_stock}, 판매: {group_sales}, 회전율: {group_turnover:.2%})"):
                for person in sorted(df_group['담당'].unique()):
                    df_person = df_group[df_group['담당'] == person]
                    person_stock = df_person['재고수량'].sum()
                    person_sales = df_person['판매수량'].sum()
                    person_turnover = (person_sales / (person_stock + person_sales)) if (person_stock + person_sales) > 0 else 0
                    
                    with st.expander(f"👤 **담당: {person}** (재고: {person_stock}, 판매: {person_sales}, 회전율: {person_turnover:.2%})"):
                        df_store = df_person.groupby('출고처').agg(
                            재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')
                        ).reset_index()
                        store_total = df_store['재고수량'] + df_store['판매수량']
                        df_store['재고회전율'] = np.divide(df_store['판매수량'], store_total, out=np.zeros_like(store_total, dtype=float), where=store_total!=0).apply(lambda x: f"{x:.2%}")

                        for idx, row in df_store.iterrows():
                            with st.expander(f"🏪 **판매점: {row['출고처']}** (재고: {row['재고수량']}, 판매: {row['판매수량']}, 회전율: {row['재고회전율']})"):
                                df_model = df_person[df_person['출고처'] == row['출고처']]
                                model_detail = df_model.groupby('모델명').agg(
                                    재고수량=('재고수량', 'sum'), 판매수량=('판매수량', 'sum')
                                ).reset_index()
                                model_total = model_detail['재고수량'] + model_detail['판매수량']
                                model_detail['재고회전율'] = np.divide(model_detail['판매수량'], model_total, out=np.zeros_like(model_total, dtype=float), where=model_total!=0).apply(lambda x: f"{x:.2%}")
                                st.dataframe(model_detail)
else:
    st.info('사이드바에서 재고 및 판매 리스트 CSV 파일을 업로드해주세요.')