import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 설정 ---
st.set_page_config(page_title="현대다이텍 업무 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("📌 메인 메뉴")
menu_choice = st.sidebar.radio("원하시는 업무를 선택해 주십시오.", 
                               ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

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
        existing_data = conn.read(worksheet="거래처", ttl=0)
        new_data = pd.DataFrame([{"거래처명": vendor_name, "사업자등록번호": biz_no, "연락처": contact, "팩스번호": fax, "비고": remarks}])
        conn.update(worksheet="거래처", data=pd.concat([existing_data, new_data], ignore_index=True))
        st.success("✅ 저장되었습니다.")
        st.rerun()
    st.dataframe(conn.read(worksheet="거래처", ttl=0), use_container_width=True)

# ==========================================
# 2. 품목 등록 (이력 자동 기록)
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 신규 품목 등록")
    with st.form("item_form", clear_on_submit=True):
        item_name = st.text_input("제품명 *")
        unit_price = st.number_input("기본 매입 단가(원)", min_value=0, step=10)
        submitted = st.form_submit_button("품목 저장하기")
        
    if submitted and item_name:
        df_items = conn.read(worksheet="품목", ttl=0)
        # 품목 업데이트
        if item_name in df_items['제품명'].values:
            df_items.loc[df_items['제품명'] == item_name, '단가'] = unit_price
        else:
            df_items = pd.concat([df_items, pd.DataFrame([{"제품명": item_name, "단가": unit_price}])], ignore_index=True)
        conn.update(worksheet="품목", data=df_items)
        
        # 단가 이력 저장
        df_history = conn.read(worksheet="단가이력", ttl=0)
        new_history = pd.DataFrame([{"품목명": item_name, "단가": unit_price, "변경일자": str(date.today())}])
        conn.update(worksheet="단가이력", data=pd.concat([df_history, new_history], ignore_index=True))
        
        st.success("✅ 품목 등록 및 이력 저장 완료!")
        st.rerun()
    st.dataframe(conn.read(worksheet="품목", ttl=0), use_container_width=True)

# ==========================================
# 3. 매입 자료 입력
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_vendors = conn.read(worksheet="거래처", ttl=0)
    df_items = conn.read(worksheet="품목", ttl=0)
    
    # 단가 이력 읽기
    df_history = conn.read(worksheet="단가이력", ttl=0)
    item_price_map = {}
    if not df_history.empty and '단가' in df_history.columns:
        df_history['변경일자'] = pd.to_datetime(df_history['변경일자'])
        latest_prices = df_history.sort_values('변경일자').groupby('품목명').tail(1)
        item_price_map = dict(zip(latest_prices['품목명'], latest_prices['단가']))

    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("매입 일자")
        vendor = st.selectbox("매입 거래처", df_vendors['거래처명'].tolist())
        selected_item = st.selectbox("품목명", df_items['제품명'].tolist())
        default_price = item_price_map.get(selected_item, 0)
    
    with st.form("purchase_form", clear_on_submit=True):
        col3, col4 = st.columns(2)
        with col3:
            qty = st.number_input("수량", min_value=1)
            price = st.number_input("단가", value=int(default_price), min_value=0)
        with col4:
            remarks = st.text_input("비고")
            submit = st.form_submit_button("입력 완료")

    if submit:
        total_price = qty * price
        existing_data = conn.read(worksheet="매입자료", ttl=0)
        new_row = pd.DataFrame([{"매입일자": str(date_input), "거래처": vendor, "품목명": selected_item, 
                                 "수량": qty, "단가": price, "총액": total_price, "비고": remarks}])
        new_row = new_row[existing_data.columns]
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="매입자료", data=updated_df)
        st.success(f"✅ 저장 완료!")
        st.rerun()

    # 📊 누적 내역 표시 (누락되었던 부분)
    st.subheader("📊 누적 매입 내역")
    st.dataframe(conn.read(worksheet="매입자료", ttl=0), use_container_width=True)

# ==========================================
# 4. 단가변동이력 조회 (새로 추가!)
# ==========================================
elif menu_choice == "단가변동이력":
    st.title("📈 품목별 단가 변동 이력")
    df_history = conn.read(worksheet="단가이력", ttl=0)
    if df_history.empty:
        st.warning("아직 등록된 단가 이력이 없습니다.")
    else:
        st.dataframe(df_history.sort_values(by='변경일자', ascending=False), use_container_width=True)

# ==========================================
# 5. 거래처별 & 기간별 내역 조회
# ==========================================
elif menu_choice == "거래처별 내역":
    st.title("🔍 기간 및 거래처별 내역 조회")
    df = conn.read(worksheet="매입자료", ttl=0)
    if df.empty:
        st.warning("데이터가 없습니다.")
    else:
        df['매입일자'] = pd.to_datetime(df['매입일자'])
        start_date = st.date_input("시작일", value=df['매입일자'].min())
        end_date = st.date_input("종료일", value=df['매입일자'].max())
        selected_vendor = st.selectbox("조회할 거래처 선택", df['거래처'].unique().tolist())
        
        mask = (df['매입일자'].dt.date >= start_date) & (df['매입일자'].dt.date <= end_date) & (df['거래처'] == selected_vendor)
        st.dataframe(df[mask], use_container_width=True)
        st.metric(label="총 매입액", value=f"{df[mask]['총액'].sum():,} 원")