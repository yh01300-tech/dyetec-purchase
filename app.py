import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. 기본 설정 ---
st.set_page_config(page_title="현대다이텍 매입 관리", layout="wide")
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")
    st.stop()

st.sidebar.title("📌 메인 메뉴")
menu_choice = st.sidebar.radio("원하시는 업무를 선택해 주십시오.", 
                               ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# --- 2. 함수: 데이터 읽기 (오류 방지) ---
def get_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0)
    except Exception as e:
        st.error(f"시트 '{worksheet_name}' 연결 오류. 권한을 확인해주세요.")
        return pd.DataFrame()

# ==========================================
# [거래처 등록]
# ==========================================
if menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    with st.form("vendor_form", clear_on_submit=True):
        vendor_name = st.text_input("거래처명 *")
        biz_no = st.text_input("사업자등록번호")
        contact = st.text_input("연락처")
        submitted = st.form_submit_button("거래처 저장하기")
        
    if submitted and vendor_name:
        existing = get_data("거래처")
        new = pd.DataFrame([{"거래처명": vendor_name, "사업자등록번호": biz_no, "연락처": contact}])
        conn.update(worksheet="거래처", data=pd.concat([existing, new], ignore_index=True))
        st.success("✅ 저장 완료")
        st.rerun()
    st.dataframe(get_data("거래처"), use_container_width=True)

# ==========================================
# [품목 등록]
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 신규 품목 등록 (단가 이력 자동 저장)")
    with st.form("item_form", clear_on_submit=True):
        item_name = st.text_input("제품명 *")
        unit_price = st.number_input("기본 매입 단가(원)", min_value=0, step=10)
        submitted = st.form_submit_button("품목 저장하기")
        
    if submitted and item_name:
        df = get_data("품목")
        new_row = pd.DataFrame([{"제품명": item_name, "단가": unit_price}])
        # 데이터 업데이트 로직
        if not df.empty and item_name in df['제품명'].values:
            df.loc[df['제품명'] == item_name, '단가'] = unit_price
        else:
            df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="품목", data=df)
        
        # 이력 저장
        hist = get_data("단가이력")
        new_hist = pd.DataFrame([{"품목명": item_name, "단가": unit_price, "변경일자": str(date.today())}])
        conn.update(worksheet="단가이력", data=pd.concat([hist, new_hist], ignore_index=True))
        
        st.success("✅ 등록 완료!")
        st.rerun()
    st.dataframe(get_data("품목"), use_container_width=True)

# ==========================================
# [매입 자료 입력]
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_vendors = get_data("거래처")
    df_items = get_data("품목")
    df_history = get_data("단가이력")
    
    # 최신 단가 불러오기
    default_price = 0
    if not df_history.empty and '단가' in df_history.columns:
        df_history['변경일자'] = pd.to_datetime(df_history['변경일자'])
        latest = df_history.sort_values('변경일자').groupby('품목명').tail(1)
        item_map = dict(zip(latest['품목명'], latest['단가']))
    else:
        item_map = dict(zip(df_items['제품명'], df_items['단가'])) if not df_items.empty else {}

    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("매입 일자")
        vendor = st.selectbox("매입 거래처", df_vendors['거래처명'].tolist() if not df_vendors.empty else [])
        selected_item = st.selectbox("품목명", df_items['제품명'].tolist() if not df_items.empty else [])
        default_price = item_map.get(selected_item, 0)
    
    with st.form("purchase_form", clear_on_submit=True):
        col3, col4 = st.columns(2)
        with col3:
            qty = st.number_input("수량", min_value=1)
            price = st.number_input("단가", value=int(default_price), min_value=0)
        with col4:
            remarks = st.text_input("비고")
            submit = st.form_submit_button("입력 완료")

    if submit:
        df_purchase = get_data("매입자료")
        new_row = pd.DataFrame([{"매입일자": str(date_input), "거래처": vendor, "품목명": selected_item, 
                                 "수량": qty, "단가": price, "총액": qty*price, "비고": remarks}])
        if not df_purchase.empty: new_row = new_row[df_purchase.columns]
        conn.update(worksheet="매입자료", data=pd.concat([df_purchase, new_row], ignore_index=True))
        st.success("✅ 저장 완료!")
        st.rerun()

    st.subheader("📊 누적 매입 내역")
    st.dataframe(get_data("매입자료"), use_container_width=True)

# ==========================================
# [나머지 메뉴] (단가변동이력/거래처별 조회 생략)
# ==========================================
elif menu_choice == "단가변동이력":
    st.title("📈 단가 변동 이력")
    st.dataframe(get_data("단가이력"), use_container_width=True)
elif menu_choice == "거래처별 내역":
    st.title("🔍 거래처별 조회")
    df = get_data("매입자료")
    if not df.empty:
        sel = st.selectbox("거래처 선택", df['거래처'].unique())
        st.dataframe(df[df['거래처']==sel], use_container_width=True)