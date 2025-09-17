import streamlit as st
import pandas as pd
import os
import numpy as np

# --- 여기에 원하는 비밀번호를 설정하세요 ---
ADMIN_PASSWORD = "your_password123" 

st.title("🔑 관리자 페이지")

# 비밀번호 입력
password = st.text_input("비밀번호를 입력하세요:", type="password")

if password == ADMIN_PASSWORD:
    st.success("인증되었습니다. 데이터를 업로드하세요.")
    
    inventory_file = st.file_uploader("재고리스트.csv", type=['csv'])
    sales_file = st.file_uploader("판매리스트.csv", type=['csv'])

    if inventory_file and sales_file:
        if st.button("데이터베이스에 업로드"):
            try:
                with st.spinner('데이터를 처리하고 있습니다...'):
                    # --- <<< 누락되었던 데이터 처리 코드 시작 >>> ---
                    inventory_df, sales_df = None, None
                    for encoding in ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']:
                        try:
                            #파일 포인터를 처음으로 되돌려 여러 번 읽을 수 있게 함
                            inventory_file.seek(0)
                            inventory_df = pd.read_csv(inventory_file, encoding=encoding)
                            sales_file.seek(0)
                            sales_df = pd.read_csv(sales_file, encoding=encoding)
                            break
                        except Exception:
                            continue
                    
                    if inventory_df is None or sales_df is None:
                        st.error("CSV 파일을 읽는데 실패했습니다. 파일 인코딩을 확인해주세요.")
                        st.stop()

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
                    # --- <<< 누락되었던 데이터 처리 코드 끝 >>> ---

                st.write("✅ 데이터 처리 완료. 데이터베이스에 저장 중...")

                DB_URL = os.environ.get('DATABASE_URL')

                if DB_URL:
                    DB_URL = DB_URL.strip()
                    if DB_URL.startswith("postgres://"):
                        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
                
                if not DB_URL:
                    st.error("데이터베이스 URL을 찾을 수 없습니다. Render 환경 변수를 확인하세요.")
                    st.stop()

                conn = st.connection('db', type='sql', url=DB_URL)
                
                # 이제 df_detailed 변수가 정상적으로 정의되었으므로 오류가 발생하지 않습니다.
                df_detailed.to_sql('inventory_data', conn.engine, if_exists='replace', index=False)

                st.success("🎉 데이터베이스 업로드 완료! 메인 페이지에서 결과를 확인하세요.")
                st.balloons()

            except Exception as e:
                st.error(f"업로드 중 오류가 발생했습니다: {e}")

elif password:
    st.error("비밀번호가 틀렸습니다.")