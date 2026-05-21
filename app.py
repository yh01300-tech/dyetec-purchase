import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 연결
st.set_page_config(page_title="현대다이텍 매입 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 캐시를 활용한 데이터 로드 (429 에러 방지)
@st.cache_data(ttl=600)
def load_data(ws):
    try: return conn.read(worksheet=ws, ttl=0)
    except: return pd.DataFrame()

# 3. 사이드바
st.sidebar.title("🏢 현대다이텍 관리 시스템")
menu_choice = st.sidebar.radio("업무 선택", 
                               ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# ==========================================
# 1. 매입 자료 입력
# ==========================================
if menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_v = load_data("거래처")
    df_i = load_data("품목")
    df_h = load_data("단가이력")
    
    # 단가 이력 데이터 처리
    item_price_map = {}
    if not df_h.empty:
        df_h['변경일자'] = pd.to_datetime(df_h['변경일자'])
        latest = df_h.sort_values('변경일자').groupby('품목명').tail(1)
        item_price_map = dict(zip(latest['품목명'], latest['단가']))

    c1, c2 = st.columns(2)
    with c1:
        date_input = st.date_input("매입 일자")
        vendor = st.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
        item = st.selectbox("품목명", df_i['제품명'].tolist() if not df_i.empty else [])
    with c2:
        # 단가 계산 (품목 바뀔 때마다 자동 갱신)
        base_p = df_i[df_i['제품명'] == item]['단가'].values[0] if not df_i.empty and item in df_i['제품명'].values else 0
        final_p = item_price_map.get(item, base_p)
        
        qty = st.number_input("수량", min_value=1)
        price = st.number_input("단가", value=int(final_p), min_value=0, key=f"price_{item}")
        remarks = st.text_input("비고")

    if st.button("✅ 입력 완료"):
        df_p = load_data("매입자료")
        new = pd.DataFrame([{"매입일자": str(date_input), "거래처": vendor, "품목명": item, "수량": qty, "단가": price, "총액": qty*price, "비고": remarks}])
        if not df_p.empty: new = new[df_p.columns]
        conn.update(worksheet="매입자료", data=pd.concat([df_p, new], ignore_index=True))
        st.cache_data.clear() # 캐시 초기화
        st.success("저장 완료!")
        st.rerun()

    st.subheader("📊 누적 내역")
    st.dataframe(load_data("매입자료"), use_container_width=True)

# ==========================================
# 2. 거래처 등록
# ==========================================
elif menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")