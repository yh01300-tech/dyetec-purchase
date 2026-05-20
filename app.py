import streamlit as st
import pandas as pd
import os

# --- 데이터 저장용 파일 이름 설정 ---
VENDOR_FILE = "vendors.csv"
ITEM_FILE = "items.csv" # 품목 데이터 저장 파일 추가
PURCHASE_FILE = "purchase_records.csv"

# --- 웹사이트 기본 설정 ---
st.set_page_config(page_title="사내 업무 관리 시스템", layout="wide")

# ==========================================
# 1. 왼쪽 사이드바 메뉴 설정
# ==========================================
st.sidebar.title("📌 메인 메뉴")
menu_choice = st.sidebar.radio(
    "원하시는 업무를 선택해 주십시오.",
    ("매입 자료 입력", "거래처 등록", "품목 등록")
)
st.sidebar.markdown("---")
st.sidebar.info("현대다이텍 업무 시스템 V1.2")


# ==========================================
# 2. 거래처 등록 메뉴
# ==========================================
if menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    
    with st.form("vendor_form", clear_on_submit=True):
        st.subheader("거래처 상세 정보 입력")
        vendor_name = st.text_input("거래처명 * (필수)")
        biz_no = st.text_input("사업자등록번호 (예: 000-00-00000)")
        contact = st.text_input("연락처")
        fax = st.text_input("팩스번호")
        remarks = st.text_area("비고 (특이사항 등)")
        submitted = st.form_submit_button("거래처 저장하기")
        
    if submitted:
        if vendor_name.strip() == "":
            st.warning("⚠️ 거래처명은 필수 입력 항목입니다.")
        else:
            new_vendor = pd.DataFrame({
                "거래처명": [vendor_name],
                "사업자등록번호": [biz_no],
                "연락처": [contact],
                "팩스번호": [fax],
                "비고": [remarks]
            })
            if os.path.exists(VENDOR_FILE):
                new_vendor.to_csv(VENDOR_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                new_vendor.to_csv(VENDOR_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')
            st.success(f"✅ [{vendor_name}] 등록이 완료되었습니다.")
            
    st.markdown("---")
    st.subheader("📋 등록된 거래처 목록")
    if os.path.exists(VENDOR_FILE):
        df_vendors = pd.read_csv(VENDOR_FILE)
        st.dataframe(df_vendors, use_container_width=True)


# ==========================================
# 3. 품목 등록 메뉴 (신규 추가)
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
            new_item = pd.DataFrame({
                "제품명": [item_name],
                "단가": [unit_price]
            })
            if os.path.exists(ITEM_FILE):
                new_item.to_csv(ITEM_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                new_item.to_csv(ITEM_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')
            st.success(f"✅ [{item_name}] (단가: {unit_price:,}원) 등록이 완료되었습니다.")
            
    st.markdown("---")
    st.subheader("📋 등록된 품목 목록")
    if os.path.exists(ITEM_FILE):
        df_items = pd.read_csv(ITEM_FILE)
        df_formatted_items = df_items.copy()
        df_formatted_items["단가"] = df_formatted_items["단가"].map("{:,}원".format)
        st.dataframe(df_formatted_items, use_container_width=True)
    else:
        st.info("아직 등록된 품목이 없습니다.")


# ==========================================
# 4. 매입 자료 입력 메뉴 (품목 자동 연동 적용)
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    
    # 1) 등록된 거래처 목록 불러오기
    vendor_list = ["(직접 입력)"]
    if os.path.exists(VENDOR_FILE):
        df_vendors = pd.read_csv(VENDOR_FILE)
        vendor_list = df_vendors['거래처명'].tolist()
        
    # 2) 등록된 품목 목록 및 단가 정보 불러오기
    item_list = ["(직접 입력)"]
    item_price_dict = {} # 품목을 고르면 단가를 자동으로 찾기 위한 사전
    
    if os.path.exists(ITEM_FILE):
        df_items = pd.read_csv(ITEM_FILE)
        item_list = df_items['제품명'].tolist()
        # 제품명을 키(Key)로, 단가를 값(Value)으로 하는 딕셔너리 생성
        item_price_dict = dict(zip(df_items['제품명'], df_items['단가']))

    # 3) 입력 폼 (화면을 2단으로 나누어 깔끔하게 배치)
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("매입 일자")
        selected_vendor = st.selectbox("매입 거래처", vendor_list)
        # 품목 선택 시, 해당 품목의 단가를 자동으로 계산 로직에 넘겨주기 위해 준비
        selected_item = st.selectbox("품목명 (등록된 품목 선택)", item_list)
        
    with col2:
        # 선택한 품목의 기본 단가를 불러오고, 원하면 수정도 가능하게 함
        default_price = int(item_price_dict.get(selected_item, 0)) if selected_item != "(직접 입력)" else 0
        quantity = st.number_input("매입 수량", min_value=1, step=1)
        unit_price = st.number_input("매입 단가(원)", value=default_price, min_value=0, step=10)
        
    # 저장 버튼은 폼 바깥으로 빼서 전체 데이터에 접근하기 쉽게 변경
    if st.button("데이터 저장하기", use_container_width=True, type="primary"):
        if selected_item == "(직접 입력)":
             st.warning("⚠️ 품목을 등록 메뉴에서 먼저 추가하시거나, 올바른 품목을 선택해 주십시오.")
        else:
            total_price = quantity * unit_price
            new_data = pd.DataFrame({
                "매입일자": [date.strftime("%Y-%m-%d")],
                "거래처": [selected_vendor],
                "품목명": [selected_item],
                "수량": [quantity],
                "단가": [unit_price],
                "총액": [total_price]
            })
            
            if os.path.exists(PURCHASE_FILE):
                new_data.to_csv(PURCHASE_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                new_data.to_csv(PURCHASE_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')
            st.success(f"✅ [{selected_item}] 내역이 성공적으로 저장되었습니다!")

    st.markdown("---")
    st.subheader("📊 현재까지 누적된 매입 내역")
    if os.path.exists(PURCHASE_FILE):
        df_records = pd.read_csv(PURCHASE_FILE)
        # 최신 입력 데이터가 위로 올라오도록 정렬(역순)
        df_records = df_records[::-1].reset_index(drop=True) 
        
        df_formatted = df_records.copy()
        df_formatted["수량"] = df_formatted["수량"].map("{:,}".format)
        df_formatted["단가"] = df_formatted["단가"].map("{:,}원".format)
        df_formatted["총액"] = df_formatted["총액"].map("{:,}원".format)
        st.dataframe(df_formatted, use_container_width=True)
    else:
        st.info("아직 저장된 매입 내역이 없습니다.")