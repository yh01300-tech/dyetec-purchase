import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import altair as alt

st.set_page_config(page_title="현대다이텍 통합 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 로드 (캐시 10초)
def load_data(ws): 
    try: return conn.read(worksheet=ws, ttl=10)
    except: return pd.DataFrame()

# 단가 자동 계산/타입 고정
def on_item_change():
    item = st.session_state.item_select
    df_i = load_data("품목")
    if not df_i.empty and '제품명' in df_i.columns:
        match = df_i[df_i['제품명'] == item]
        if not match.empty:
            try:
                # 데이터를 확실히 숫자로 변환
                clean_price = int(float(str(match.iloc[0]['단가']).replace(',', '').replace('원', '').strip()))
                st.session_state.price_input = clean_price
            except: st.session_state.price_input = 0
        else: st.session_state.price_input = 0
    else: st.session_state.price_input = 0

st.title("🏢 현대다이텍 통합 관리 시스템")
menu = st.sidebar.radio("메뉴 선택", ("종합 대시보드", "매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"))

# 매입 자료 입력부 (데이터 타입 강제 지정)
if menu == "매입 자료 입력":
    st.subheader("📝 원부자재 매입 내역 등록")
    df_v, df_i = load_data("거래처"), load_data("품목")
    
    c1, c2 = st.columns(2)
    d = c1.date_input("매입 일자")
    v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
    
    # 단가 초기값
    if 'price_input' not in st.session_state: st.session_state.price_input = 0
    
    i = c2.selectbox("품목", df_i['제품명'].tolist() if not df_i.empty else [], key="item_select", on_change=on_item_change)
    q = c2.number_input("수량", min_value=0, value=0)
    p = c2.number_input("단가", min_value=0, value=st.session_state.price_input, key="price_input")
    rem = st.text_input("비고")
    
    if st.button("✅ 내역 등록"):
        # 여기서 확실하게 타입 지정
        new_row = pd.DataFrame([{
            "매입일자": str(d), 
            "거래처": v, 
            "품목명": i, 
            "수량": int(q), 
            "단가": int(p), # 단가 포함
            "총액": int(q * p), 
            "비고": rem
        }])
        df = conn.read(worksheet="매입자료", ttl=0)
        conn.update(worksheet="매입자료", data=pd.concat([df, new_row], ignore_index=True))
        st.success("데이터가 정확히 전송되었습니다.")
        st.rerun()

    st.markdown("---")
    st.dataframe(load_data("매입자료"), use_container_width=True)

# 기타 메뉴는 동일하게 유지하되, 데이터 정렬/표시 최적화
elif menu == "거래처별 내역": 
    st.subheader("🔍 상세 내역 조회")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        c1, c2, c3 = st.columns(3)
        v = c1.selectbox("거래처", ["전체"] + df['거래처'].dropna().unique().tolist())
        date_range = c2.date_input("기간", value=(date.today() - timedelta(days=30), date.today()))
        
        if v != "전체": df = df[df['거래처'] == v]
        if len(date_range) == 2:
            df = df[(df['매입일자'].dt.date >= date_range[0]) & (df['매입일자'].dt.date <= date_range[1])]
        
        st.dataframe(df.sort_values('매입일자', ascending=False), use_container_width=True)
# (나머지 코드 생략 - 위 구조에 맞춰 기존 내용 유지)