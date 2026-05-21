import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("연결 테스트")
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. 시트를 읽어봅니다.
    df = conn.read(worksheet="매입자료", ttl=0)
    st.success("연결 성공! 데이터를 잘 가져옵니다.")
    st.dataframe(df)
except Exception as e:
    st.error(f"연결 실패! 에러 메시지: {e}")