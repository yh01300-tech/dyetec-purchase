import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 설정
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data(ws):
    try:
        return conn.read(worksheet=ws)
    except:
        return pd.DataFrame()

# 2. 사이드바
st.sidebar.title("🏢 현대다이텍 시스템")
menu_choice = st.sidebar.radio("메뉴 선택", ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# 3. 각 메뉴별 기능
if menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_v, df_i, df_h = load_data("거래처"), load_data("품목"), load_data("단가이력")
    
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
        base_p = df_i[df_i['제품명'] == item]['단가'].values[0] if not df_i.empty and item in df_i['제품명'].values else 0
        final_p = item_price_map.get(item, base_p)
        qty = st.number_input("수량", min_value=1)
        price = st.number_input("단가", value=int(final_p), min_value=0, key=f"p_{item}")
        remarks = st.text_input("비고")

    if st.button("✅ 입력 완료"):
        df_p = load_data("매입자료")
        new_row = {"매입일자": str(date_input), "거래처": vendor, "품목명": item, "수량": qty, "단가": price, "총액": qty*price, "비고": remarks}
        updated = pd.concat([df_p, pd.DataFrame([new_row])], ignore_index=True)
        conn.update(worksheet="매입자료", data=updated)
        st.cache_data.clear(); st.rerun()
    
    st.subheader("📊 누적 매입 내역")
    df_p = load_data("매입자료")
    if not df_p.empty: st.dataframe(df_p, use_container_width=True)
    else: st.info("입력된 매입 데이터가 없습니다.")

elif menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    with st.form("v_form", clear_on_submit=True):
        v_name, v_biz = st.text_input("거래처명 *"), st.text_input("사업자번호")
        submitted = st.form_submit_button("저장")
    if submitted and v_name:
        df = load_data("거래처")
        conn.update(worksheet="거래처", data=pd.concat([df, pd.DataFrame([{"거래처명": v_name, "사업자등록번호": v_biz}])], ignore_index=True))
        st.cache_data.clear(); st.rerun()
    st.subheader("🏢 등록된 거래처 목록")
    df_v = load_data("거래처")
    if not df_v.empty: st.dataframe(df_v, use_container_width=True)
    else: st.info("등록된 거래처가 없습니다.")

# ==========================================
# 💡 거래처 입력 기능이 추가된 [품목 등록] 메뉴
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 품목 등록/수정")
    df_v = load_data("거래처")  # 거래처 목록을 불러옵니다.
    
    with st.form("i_form", clear_on_submit=True):
        i_name = st.text_input("제품명 *")
        # 등록된 거래처 목록을 가져와서 선택 박스로 제공합니다.
        i_vendor = st.selectbox("주거래처 선택", df_v['거래처명'].tolist() if not df_v.empty else ["등록된 거래처 없음"])
        i_price = st.number_input("기본 단가", min_value=0)
        submitted = st.form_submit_button("등록/수정")
        
    if submitted and i_name:
        if i_vendor == "등록된 거래처 없음":
            st.error("거래처를 먼저 등록하신 후 품목을 등록할 수 있습니다.")
        else:
            df, hist = load_data("품목"), load_data("단가이력")
            
            # 품목 시트 업데이트 (주거래처 열 포함)
            new_item = pd.DataFrame([{"제품명": i_name, "주거래처": i_vendor, "단가": i_price}])
            if not df.empty and i_name in df['제품명'].values: 
                df.loc[df['제품명'] == i_name, '단가'] = i_price
                df.loc[df['제품명'] == i_name, '주거래처'] = i_vendor
            else: 
                df = pd.concat([df, new_item], ignore_index=True)
            conn.update(worksheet="품목", data=df)
            
            # 단가이력 기록 시에도 거래처 정보와 함께 기록
            new_h = pd.DataFrame([{"품목명": i_name, "거래처": i_vendor, "단가": i_price, "변경일자": str(date.today())}])
            conn.update(worksheet="단가이력", data=pd.concat([hist, new_h], ignore_index=True))
            
            st.cache_data.clear(); st.rerun()
            
    st.subheader("📦 현재 품목 목록")
    df_i = load_data("품목")
    if not df_i.empty: st.dataframe(df_i, use_container_width=True)
    else: st.info("등록된 품목이 없습니다.")

elif menu_choice == "단가변동이력":
    st.title("📈 품목별 단가 변동 이력")
    df = load_data("단가이력")
    if not df.empty: st.dataframe(df, use_container_width=True)
    else: st.info("아직 변경된 단가 이력이 없습니다.")

elif menu_choice == "거래처별 내역":
    st.title("🔍 거래처 및 날짜별 매입 조회")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        c1, c2 = st.columns(2)
        with c1:
            vendor_list = ["전체"] + df['거래처'].unique().tolist()
            sel_vendor = st.selectbox("거래처 선택", vendor_list)
        with c2:
            min_d = df['매입일자_dt'].min().date() if pd.notnull(df['매입일자_dt'].min()) else date.today()
            max_d = df['매입일자_dt'].max().date() if pd.notnull(df['매입일_dt'].max()) else date.today()
            sel_date = st.date_input("조회 기간 선택", value=(min_d, max_d))
        
        filtered_df = df.copy()
        if sel_vendor != "전체":
            filtered_df = filtered_df[filtered_df['거래처'] == sel_vendor]
        if len(sel_date) == 2:
            start_date, end_date = sel_date
            filtered_df = filtered_df[(filtered_df['매입일자_dt'].dt.date >= start_date) & (filtered_df['매입일자_dt'].dt.date <= end_date)]
        elif len(sel_date) == 1:
            start_date = sel_date[0]
            filtered_df = filtered_df[filtered_df['매입일자_dt'].dt.date == start_date]

        display_df = filtered_df.drop(columns=['매입일자_dt'])
        st.write(f"조회 결과: 총 **{len(display_df)}건**")
        st.dataframe(display_df, use_container_width=True)
        if not display_df.empty and '총액' in display_df.columns:
            total_sum = display_df['총액'].sum()
            st.success(f"💰 해당 기간 **{sel_vendor}**의 매입 총액: **{int(total_sum):,}원**")
    else:
        st.info("조회할 매입 내역이 없습니다.")