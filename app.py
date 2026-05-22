import streamlit as st
import pandas as pd
from datetime import date
import os
import altair as alt
from streamlit_gsheets import GSheetsConnection

# 1. 설정 및 인쇄 전용 스타일(CSS)
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header { visibility: hidden !important; }
        .stButton { display: none !important; }
        .main .block-container { padding-top: 2rem !important; max-width: 100% !important; }
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data(ws):
    try: return conn.read(worksheet=ws)
    except: return pd.DataFrame()

# 2. 사이드바 및 로고
try:
    if os.path.exists("logo.png"): st.logo("logo.png")
    else: st.sidebar.title("🏢 현대다이텍 시스템")
except: st.sidebar.title("🏢 현대다이텍 시스템")

if st.sidebar.button("🔄 시스템 새로고침"):
    st.cache_data.clear(); st.rerun()

menu = st.sidebar.radio("메뉴 선택", ("종합 대시보드", "단가 검색", "매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"))

# 3. 메뉴별 기능
if menu == "종합 대시보드":
    st.title("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        curr = df[df['매입일자_dt'].dt.month == date.today().month]
        st.metric("이번 달 총 매입액", f"{int(curr['총액'].sum()):,} 원")
        if '거래처' in df.columns:
            st.bar_chart(curr.groupby('거래처')['총액'].sum())

elif menu == "단가 검색":
    st.title("🔎 품목별 단가 검색")
    df_h = load_data("단가이력")
    if not df_h.empty:
        item = st.selectbox("품목 선택", df_h['품목명'].unique())
        hist = df_h[df_h['품목명'] == item].sort_values('변경일자', ascending=False)
        st.write(f"최신 단가: {int(hist.iloc[0]['단가']):,} 원")
        st.dataframe(hist, use_container_width=True)

elif menu == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    with st.form("buy_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        d = col1.date_input("날짜"); v = col1.selectbox("거래처", load_data("거래처")['거래처명'])
        i = col2.selectbox("품목", load_data("품목")['제품명']); q = col2.number_input("수량", 1); p = col2.number_input("단가", 0)
        rem = st.text_input("비고"); sub = st.form_submit_button("등록")
    if sub:
        df = load_data("매입자료")
        conn.update("매입자료", pd.concat([df, pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "단가":p, "총액":q*p, "비고":rem}])], ignore_index=True))
        st.rerun()

elif menu == "거래처 등록":
    st.title("🏢 거래처 등록 및 수정")
    action = st.radio("작업", ("신규 등록", "정보 수정"), horizontal=True)
    df_v = load_data("거래처")
    
    # 수정 모드 데이터 로드 로직 (이전 코드와 동일)
    default = {}
    if action == "정보 수정":
        sel = st.selectbox("거래처 선택", df_v['거래처명'].unique())
        default = df_v[df_v['거래처명'] == sel].iloc[0].to_dict()
    
    with st.form("v_form", clear_on_submit=True):
        n = st.text_input("거래처명", value=default.get('거래처명', ''))
        biz = st.text_input("사업자번호", value=default.get('사업자등록번호', ''))
        p1 = st.text_input("연락처1", value=default.get('연락처1', ''))
        p2 = st.text_input("연락처2", value=default.get('연락처2', ''))
        fax = st.text_input("팩스번호", value=default.get('팩스번호', ''))
        addr = st.text_input("주소", value=default.get('주소', ''))
        rem = st.text_input("비고", value=default.get('비고', ''))
        if st.form_submit_button("저장"):
            # 데이터 저장 로직 (이전 코드와 동일)
            st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.title("📦 품목 등록 및 수정")
    # 신규/수정 모드 (이전 코드와 동일)
    # ... (상세 등록/수정 코드) ...

elif menu == "단가변동이력":
    st.title("📈 단가 변동 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.title("🔍 상세 내역 조회")
    # 품목/거래처/날짜 필터링 (이전 코드와 동일)
    # ... (필터링 상세 코드) ...

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 대금 정산서")
    # 년월/거래처 선택 및 인쇄용 정산 표 출력 (이전 코드와 동일)
    # ... (정산서 상세 코드) ...