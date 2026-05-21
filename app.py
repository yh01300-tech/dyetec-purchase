import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 웹사이트 기본 설정 ---
st.set_page_config(page_title="현대다이텍 업무 관리 시스템", layout="wide")

# 구글 스프레드시트 연결 엔진 켜기
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 1. 왼쪽 사이드바 메뉴 설정
# ==========================================
st.sidebar.title("📌 메인 메뉴")
menu_choice = st.sidebar.radio(
    "원하시는 업무를 선택해 주십시오.",
    ("매입 자료 입력", "거래처 등록", "품목 등록")
)
st.sidebar.markdown("---")
st.sidebar.info("현대다이텍 업무 시스템 V2.0 (클라우드 DB 연동)")

# ==========================================
# 2. 거래처 등록 메뉴
# ==========================================
if menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    
    with st.form("vendor_form", clear_on_submit=True):
        st.subheader("거래처 상세 정보 입력")
        vendor_name = st.text_input("거래처명 * (필수)")
        biz_no = st.text_input("사업자등록번호")
        contact = st.text_input("연락처")
        fax = st.text_input("팩스번호")
        remarks = st.text_area("비고")
        submitted = st.form_submit_button("거래처 저장하기")
        
    if submitted:
        if vendor_name.strip() == "":
            st.warning("⚠️ 거래처명은 필수 입력 항목입니다.")
        else:
            # 1) 구글 시트의 '거래처' 탭 데이터 불러오기
            existing_data = conn.read(worksheet="거래처")
            
            # 2) 새 데이터 만들기
            new_vendor = pd.DataFrame([{
                "거래처명": vendor_name, "사업자등록번호": biz_no, 
                "연락처": contact, "팩스번호": fax, "비고": remarks
            }])
            
            # 3) 기존 데이터 밑에 새 데이터 붙이기
            updated_data = pd.concat([existing_data, new_vendor], ignore_index=True)
            
            # 4) 구글 시트에 업데이트(저장)
            conn.update(worksheet="거래처", data=updated_data)
            st.success(f"✅ [{vendor_name}] 구글 시트에 등록 완료되었습니다.")
            st.rerun()
            
    st.markdown("---")
    st.subheader("📋 등록된 거래처 목록")
    # 구글 시트에서 실시간으로 읽어와서 보여주기
    df_vendors = conn.read(worksheet="거래처")
    st.dataframe(df_vendors, use_container_width=True)

# ==========================================
# 3. 품목 등록 메뉴
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 신규 품목 등록")
    
    with st.form("item_form", clear_on_submit=True):
        st.subheader("매입 품목 기본 정보")
        item_name = st.text_input("제품명 * (필수)")
        unit_price = st.number_input("기본 매입 단가(원)", min_value=0, step=10)
        submitted = st.form_submit_button("품목 저장하기")
        
    if submitted:
        if item_name.strip() == "":
            st.warning("⚠️ 제품명은 필수 입력 항목입니다.")
        else:
            existing_data = conn.read(worksheet="품목")
            new_item = pd.DataFrame([{"제품명": item_name, "단가": unit_price}])
            updated_data = pd.concat([existing_data, new_item], ignore_index=True)
            conn.update(worksheet="품목", data=updated_data)
            st.success(f"✅ [{item_name}] 구글 시트에 등록 완료되었습니다.")
            
    st.markdown("---")
    st.subheader("📋 등록된 품목 목록")
    df_items = conn.read(worksheet="품목")
    st.dataframe(df_items, use_container_width=True)

# ==========================================
# 4. 매입 자료 입력 메뉴
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    
    # 구글 시트에서 목록 불러오기
    df_vendors = conn.read(worksheet="거래처")
    vendor_list = ["(직접 입력)"] + df_vendors['거래처명'].dropna().tolist()
        
    df_items = conn.read(worksheet="품목")
    item_list = ["(직접 입력)"] + df_items['제품명'].dropna().tolist()
    item_price_dict = dict(zip(df_items['제품명'], df_items['단가']))

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("매입 일자")
        selected_vendor = st.selectbox("매입 거래처", vendor_list)
        selected_item = st.selectbox("품목명", item_list)
        
    with col2:
        default_price = int(item_price_dict.get(selected_item, 0)) if selected_item != "(직접 입력)" else 0
        quantity = st.number_input("매입 수량", min_value=1, step=1)
        unit_price = st.number_input("매입 단가(원)", value=default_price, min_value=0, step=10)
        
    if st.button("데이터 저장하기", use_container_width=True, type="primary"):
        if selected_item == "(직접 입력)":
             st.warning("⚠️ 올바른 품목을 선택해 주십시오.")
        else:
            total_price = quantity * unit_price
            new_data = pd.DataFrame([{
                "매입일자": date.strftime("%Y-%m-%d"),
                "거래처": selected_vendor,
                "품목명": selected_item,
                "수량": quantity,
                "단가": unit_price,
                "총액": total_price
            }])
            
            existing_data = conn.read(worksheet="매입자료")
            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(worksheet="매입자료", data=updated_data)
            st.success(f"✅ [{selected_item}] 내역이 구글 시트에 안전하게 저장되었습니다!")

    st.markdown("---")
    st.subheader("📊 현재까지 누적된 매입 내역")
    df_records = conn.read(worksheet="매입자료")
    st.dataframe(df_records[::-1].reset_index(drop=True), use_container_width=True)