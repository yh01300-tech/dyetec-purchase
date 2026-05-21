import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 웹사이트 기본 설정 ---
st.set_page_config(page_title="현대다이텍 업무 관리 시스템", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("📌 메인 메뉴")
menu_choice = st.sidebar.radio("원하시는 업무를 선택해 주십시오.", ("매입 자료 입력", "거래처 등록", "품목 등록"))

# ==========================================
# 1. 거래처 등록
# ==========================================
if menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    with st.form("vendor_form", clear_on_submit=True):
        vendor_name = st.text_input("거래처명 *")
        biz_no = st.text_input("사업자등록번호")
        contact = st.text_input("연락처")
        fax = st.text_input("팩스번호")
        remarks = st.text_area("비고")
        submitted = st.form_submit_button("거래처 저장하기")
        
    if submitted and vendor_name:
        existing_data = conn.read(worksheet="거래처")
        new_data = pd.DataFrame([{"거래처명": vendor_name, "사업자등록번호": biz_no, "연락처": contact, "팩스번호": fax, "비고": remarks}])
        conn.update(worksheet="거래처", data=pd.concat([existing_data, new_data], ignore_index=True))
        st.success("✅ 저장되었습니다.")
        st.rerun()

    st.subheader("📋 등록된 거래처 목록")
    st.dataframe(conn.read(worksheet="거래처"), use_container_width=True)

# ==========================================
# 2. 품목 등록
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 신규 품목 등록")
    with st.form("item_form", clear_on_submit=True):
        item_name = st.text_input("제품명 *")
        unit_price = st.number_input("기본 매입 단가(원)", min_value=0, step=10)
        submitted = st.form_submit_button("품목 저장하기")
        
    if submitted and item_name:
        existing_data = conn.read(worksheet="품목")
        new_data = pd.DataFrame([{"제품명": item_name, "단가": unit_price}])
        conn.update(worksheet="품목", data=pd.concat([existing_data, new_data], ignore_index=True))
        st.success("✅ 저장되었습니다.")
        st.rerun()

    st.subheader("📋 등록된 품목 목록")
    st.dataframe(conn.read(worksheet="품목"), use_container_width=True)

# ==========================================
# 3. 매입 자료 입력
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    
    # 데이터 불러오기
    df_vendors = conn.read(worksheet="거래처")
    df_items = conn.read(worksheet="품목")
    
    # 입력 폼
    with st.form("purchase_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("매입 일자")
            vendor = st.selectbox("매입 거래처", df_vendors['거래처명'].tolist())
            item = st.selectbox("품목명", df_items['제품명'].tolist())
        with col2:
            qty = st.number_input("수량", min_value=1)
            price = st.number_input("단가", min_value=0)
            remarks = st.text_input("비고")  # 비고 입력창
            submit = st.form_submit_button("입력 완료")

    if submit:
        # 💡 총액 자동 계산
        total_price = qty * price
        
        new_row = pd.DataFrame([{
            "매입일자": str(date), 
            "거래처": vendor, 
            "품목명": item, 
            "수량": qty, 
            "단가": price, 
            "총액": total_price, # 자동 계산된 총액
            "비고": remarks
        }])
        
        # 기존 데이터에 추가
        existing_data = conn.read(worksheet="매입자료")
        conn.update(worksheet="매입자료", data=pd.concat([existing_data, new_row], ignore_index=True))
        st.success("✅ 매입 내역(총액 포함)이 저장되었습니다.")
        st.rerun()

    st.subheader("📊 누적 매입 내역")
    # 구글 시트에서 최신 데이터 다시 불러와서 표로 보여주기
    st.dataframe(conn.read(worksheet="매입자료"), use_container_width=True)