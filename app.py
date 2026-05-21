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
    
    # 1. 기존 데이터 읽기
    existing_data = conn.read(worksheet="매입자료")
    
    # 💡 [핵심] 컴퓨터가 기존 데이터를 제대로 읽었는지 화면에 강제로 띄웁니다.
    st.write("--- 현재 시스템이 인식한 기존 데이터 목록 ---")
    st.dataframe(existing_data) 
    st.write("-------------------------------------------")
    
    # 품목-단가 사전 생성
    item_price_map = dict(zip(df_items['제품명'], df_items['단가']))

    # 2. 폼 바깥에서 품목 선택
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("매입 일자")
        vendor = st.selectbox("매입 거래처", df_vendors['거래처명'].tolist())
        selected_item = st.selectbox("품목명", df_items['제품명'].tolist())
        default_price = item_price_map.get(selected_item, 0)
    
    # 3. 입력 폼
    with st.form("purchase_form", clear_on_submit=True):
        col3, col4 = st.columns(2)
        with col3:
            qty = st.number_input("수량", min_value=1)
            price = st.number_input("단가", value=int(default_price), min_value=0)
        with col4:
            remarks = st.text_input("비고")
            submit = st.form_submit_button("입력 완료")

    # 4. 저장 로직 (이 'if'는 'with' 블록 바깥에 있어야 합니다!)
    if submit:
        total_price = qty * price
        
        # 1. 기존 데이터 읽기
        existing_data = conn.read(worksheet="매입자료")
        
        # 2. 새로운 데이터 만들기 (데이터프레임 형태)
        new_row = pd.DataFrame([{
            "매입일자": str(date), 
            "거래처": vendor, 
            "품목명": selected_item, 
            "수량": qty, 
            "단가": price, 
            "총액": total_price, 
            "비고": remarks
        }])
        
        # 💡 [핵심 해결책] 
        # 기존 데이터의 열 순서와 이름을 그대로 가져와서 new_row에 입힙니다.
        # 이렇게 하면 절대 데이터가 꼬이지 않습니다.
        new_row = new_row[existing_data.columns]
        
        # 3. 데이터 합치기
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # 4. 저장
        conn.update(worksheet="매입자료", data=updated_df)
        
        st.success(f"✅ 저장 완료! (총액: **{total_price:,}원**)")
        st.rerun() # 이제는 저장 후 화면 새로고침이 정상 작동할 겁니다.

    # 5. 목록 표시
    st.subheader("📊 누적 매입 내역")
    st.dataframe(conn.read(worksheet="매입자료"), use_container_width=True)