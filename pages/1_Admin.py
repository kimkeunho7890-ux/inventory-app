import streamlit as st
import pandas as pd
import os

ADMIN_PASSWORD = "2178149594" 

st.title("🔑 관리자 페이지")

password = st.text_input("비밀번호를 입력하세요:", type="password")

if password == ADMIN_PASSWORD:
    st.success("인증되었습니다. 데이터를 업로드하세요.")
    
    inventory_file = st.file_uploader("재고리스트.csv", type=['csv'])
    sales_file = st.file_uploader("판매리스트.csv", type=['csv'])

    if inventory_file and sales_file:
        if st.button("데이터베이스에 업로드"):
            try:
                # ... (데이터 처리 부분은 이전과 동일)

                st.write("✅ 데이터 처리 완료. 데이터베이스에 저장 중...")

                DB_URL = os.environ.get('DATABASE_URL')

                # <<< --- 최종 수정: URL을 안전하게 교정하는 코드 --- >>>
                if DB_URL:
                    DB_URL = DB_URL.strip()
                    if DB_URL.startswith("postgres://"):
                        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
                
                if not DB_URL:
                    st.error("데이터베이스 URL을 찾을 수 없습니다. Render 환경 변수를 확인하세요.")
                    st.stop()

                conn = st.connection('db', type='sql', url=DB_URL)
                
                df_detailed.to_sql('inventory_data', conn.engine, if_exists='replace', index=False)

                st.success("🎉 데이터베이스 업로드 완료! 메인 페이지에서 결과를 확인하세요.")

            except Exception as e:
                st.error(f"업로드 중 오류가 발생했습니다: {e}")

elif password:
    st.error("비밀번호가 틀렸습니다.")