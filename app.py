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
# 3. 매입 자료 입력 (최종 완성본)
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    
    # 💡 [핵심] ttl=0을 넣어 무조건 새로 읽어오게 합니다.
    df_vendors = conn.read(worksheet="거래처", ttl=0)
    df_items = conn.read(worksheet="품목", ttl=0)
    item_price_map = dict(zip(df_items['제품명'], df_items['단가']))

    # (입력 폼 부분은 그대로...)
    col1, col2 = st.columns(2)
    # ... (생략) ...
    
    # 저장 로직
    if submit:
        total_price = qty * price
        
        # 💡 [핵심] 여기도 ttl=0 필수!
        existing_data = conn.read(worksheet="매입자료", ttl=0)
        
        new_row = pd.DataFrame([{
            "매입일자": str(date), "거래처": vendor, "품목명": selected_item, 
            "수량": qty, "단가": price, "총액": total_price, "비고": remarks
        }])
        
        new_row = new_row[existing_data.columns]
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="매입자료", data=updated_df)
        
        st.success(f"✅ 저장 완료! (총액: **{total_price:,}원**)")
        st.rerun()

    # 💡 [핵심] 여기도 ttl=0 필수!
    st.subheader("📊 누적 매입 내역")
    st.dataframe(conn.read(worksheet="매입자료", ttl=0), use_container_width=True)