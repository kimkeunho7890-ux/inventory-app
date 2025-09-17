import streamlit as st
import pandas as pd
import os

# --- 여기에 원하는 비밀번호를 설정하세요 ---
ADMIN_PASSWORD = "2178149594" 

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
                # 데이터 처리 함수 (이전 코드와 유사)
                df = None
                for encoding in ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']:
                    try:
                        inventory_df = pd.read_csv(inventory_file, encoding=encoding)
                        sales_df = pd.read_csv(sales_file, encoding=encoding)
                        break
                    except Exception: continue

                sales_df.columns = sales_df.columns.str.replace('\\n', '', regex=True)
                inventory_df.rename(columns={'색상': '단말기색상'}, inplace=True)

                grouping_cols = ['영업그룹', '담당', '출고처', '모델명', '단말기색상']
                inventory_summary = inventory_df.groupby(grouping_cols).size().reset_index(name='재고수량')
                sales_summary = sales_df.groupby(grouping_cols).size().reset_index(name='판매수량')

                df_detailed = pd.merge(inventory_summary, sales_summary, on=grouping_cols, how='outer')
                df_detailed[['재고수량', '판매수량']] = df_detailed[['재고수량', '판매수량']].fillna(0).astype(int)

                st.write("✅ 데이터 처리 완료. 데이터베이스에 저장 중...")

                # 데이터베이스 연결 및 저장
                DB_URL = os.environ.get('DATABASE_URL')
                conn = st.connection('db', type='sql', url=DB_URL)

                # 'inventory_data'라는 테이블에 데이터프레임을 저장 (기존 테이블이 있으면 덮어쓰기)
                df_detailed.to_sql('inventory_data', conn.engine, if_exists='replace', index=False)

                st.success("🎉 데이터베이스 업로드 완료! 메인 페이지에서 결과를 확인하세요.")

            except Exception as e:
                st.error(f"업로드 중 오류가 발생했습니다: {e}")

elif password:
    st.error("비밀번호가 틀렸습니다.")