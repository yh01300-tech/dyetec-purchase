import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 설정
st.set_page_config(page_title="현대다이텍 매입 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 읽기 보조 함수 (에러 방지)
def load_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame() # 에러 시 빈 데이터프레임 반환

# 2. 사이드바
st.sidebar.title("🏢 현대다이텍 관리 시스템")
menu_choice = st.sidebar.radio("업무 선택", ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# ==========================================
# 1. 거래처 등록
# ==========================================
if menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    with st.form("vendor_form", clear_on_submit=True):
        v_name = st.text_input("거래처명 *")
        v_biz = st.text_input("사업자번호")
        v_tel = st.text_input("연락처")
        submitted = st.form_submit_button("등록")
    
    if submitted and v_name:
        df = load_sheet("거래처")
        new = pd.DataFrame([{"거래처명": v_name, "사업자등록번호": v_biz, "연락처": v_tel}])
        conn.update(worksheet="거래처", data=pd.concat([df, new], ignore_index=True))
        st.rerun()
    st.dataframe(load_sheet("거래처"), use_container_width=True)

# ==========================================
# 2. 품목 등록
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 품목 등록/수정")
    with st.form("item_form", clear_on_submit=True):
        i_name = st.text_input("제품명 *")
        i_price = st.number_input("기본 단가", min_value=0)
        submitted = st.form_submit_button("등록/수정")
        
    if submitted and i_name:
        # 품목 시트
        df = load_sheet("품목")
        new = pd.DataFrame([{"제품명": i_name, "단가": i_price}])
        if not df.empty and i_name in df['제품명'].values:
            df.loc[df['제품명'] == i_name, '단가'] = i_price
        else:
            df = pd.concat([df, new], ignore_index=True)
        conn.update(worksheet="품목", data=df)
        
        # 단가이력 시트
        hist = load_sheet("단가이력")
        new_h = pd.DataFrame([{"품목명": i_name, "단가": i_price, "변경일자": str(date.today())}])
        conn.update(worksheet="단가이력", data=pd.concat([hist, new_h], ignore_index=True))
        st.success("등록 완료")
        st.rerun()
    st.dataframe(load_sheet("품목"), use_container_width=True)

# ==========================================
# 3. 매입 자료 입력
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_v = load_sheet("거래처")
    df_i = load_sheet("품목")
    df_h = load_sheet("단가이력")
    
    # 최신 단가 계산
    item_price_map = {}
    if not df_h.empty:
        df_h['변경일자'] = pd.to_datetime(df_h['변경일자'])
        latest = df_h.sort_values('변경일자').groupby('품목명').tail(1)
        item_price_map = dict(zip(latest['품목명'], latest['단가']))

    with st.form("purchase_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date_input = st.date_input("매입 일자")
            vendor = st.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
            item = st.selectbox("품목명", df_i['제품명'].tolist() if not df_i.empty else [])
        with c2:
            qty = st.number_input("수량", min_value=1)
            # 기본값 설정: 단가이력 있으면 최신단가, 없으면 품목시트단가
            default_p = item_price_map.get(item, df_i[df_i['제품명']==item]['단가'].values[0] if not df_i.empty and item in df_i['제품명'].values else 0)
            price = st.number_input("단가", value=int(default_p), min_value=0)