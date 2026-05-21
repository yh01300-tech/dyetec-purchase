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
# 3. 매입 자료 입력 (단가 자동 불러오기 버전)
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    
    # 1. 데이터 불러오기
    df_vendors = conn.read(worksheet="거래처")
    df_items = conn.read(worksheet="품목")
    
    # 💡 품목명과 단가를 매칭하는 사전(Dictionary) 만들기
    item_price_map = dict(zip(df_items['제품명'], df_items['단가']))

    # 2. 폼 바깥에서 필수 정보 선택 (그래야 단가가 바로 바뀜)
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("매입 일자")
        vendor = st.selectbox("매입 거래처", df_vendors['거래처명'].tolist())
        # 품목 선택
        selected_item = st.selectbox("품목명", df_items['제품명'].tolist())
        # 선택한 품목의 단가 가져오기 (없으면 0)
        default_price = item_price_map.get(selected_item, 0)
    
    # 3. 입력 폼 (수량, 단가 등)
    with st.form("purchase_form", clear_on_submit=True):
        col3, col4 = st.columns(2)
        with col3:
            qty = st.number_input("수량", min_value=1)
            # 💡 위에서 가져온 단가를 기본값(value)으로 설정
            price = st.number_input("단가", value=int(default_price), min_value=0)
        with col4:
            remarks = st.text_input("비고")
            submit = st.form_submit_button("입력 완료")

    # 4. 저장 로직
   if submit:
        total_price = qty * price
        
        # 1. 기존 데이터 읽기
        existing_data = conn.read(worksheet="매입자료")
        
        # 2. 💡 가장 중요한 부분: 제목이 안 읽혀도 데이터가 삭제되지 않도록 보완
        # 혹시 기존 데이터의 제목과 코드의 제목이 미세하게 달라서 
        # 데이터가 안 읽히는 경우를 대비해, 기존 데이터를 억지로 살려냅니다.
        if existing_data is None or existing_data.empty:
             # 만약 시트가 비어있다고 나오면, 제목을 강제로 생성해서 덮어쓰기 방지
             existing_data = pd.DataFrame(columns=["매입일자", "거래처", "품목명", "수량", "단가", "총액", "비고"])
        
        # 3. 새로운 데이터 행 생성
        new_row = pd.DataFrame([{
            "매입일자": str(date), 
            "거래처": vendor, 
            "품목명": selected_item, 
            "수량": qty, 
            "단가": price, 
            "총액": total_price, 
            "비고": remarks
        }])
        
        # 4. 데이터 합치기
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # 5. 저장
        conn.update(worksheet="매입자료", data=updated_df)
        
        st.success(f"✅ 저장 완료! (이번 입력 건 총액: **{total_price:,}원**)")
    
    # 5. 목록 표시
    st.subheader("📊 누적 매입 내역")
    st.dataframe(conn.read(worksheet="매입자료"), use_container_width=True)