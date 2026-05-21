import streamlit as st
import pandas as pd
from datetime import date
import os
from streamlit_gsheets import GSheetsConnection

# 1. 설정
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data(ws):
    try:
        return conn.read(worksheet=ws)
    except:
        return pd.DataFrame()

# 2. 사이드바 (로고 및 새로고침)
try:
    if os.path.exists("logo.png"):
        st.logo("logo.png")
    else:
        st.sidebar.title("🏢 현대다이텍 시스템")
except Exception:
    st.sidebar.title("🏢 현대다이텍 시스템")

if st.sidebar.button("🔄 시스템 새로고침 (오류 해결)"):
    st.cache_data.clear()
    st.rerun()

menu_choice = st.sidebar.radio("메뉴 선택", ("종합 대시보드", "매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# ==========================================
# 1. 종합 대시보드
# ==========================================
if menu_choice == "종합 대시보드":
    st.title("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    
    if df.empty or '매입일자' not in df.columns or '총액' not in df.columns:
        st.info("📈 매입 데이터가 충분히 누적되면 대시보드가 자동으로 생성됩니다.")
    else:
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        df['총액'] = pd.to_numeric(df['총액'], errors='coerce').fillna(0)
        valid_df = df.dropna(subset=['매입일자_dt'])
        
        if valid_df.empty:
            st.info("유효한 날짜 데이터가 없습니다.")
        else: