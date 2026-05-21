import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 기본 설정
st.set_page_config(page_title="현대다이텍 매입 관리", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(ws):
    try: return conn.read(worksheet=ws, ttl=0)
    except: return pd.DataFrame()

# 2. 사이드바 메뉴 (대리님이 말씀하신 5개 구성)
st.sidebar.title("🏢 현대다이텍 관리 시스템")
menu_choice = st.sidebar.radio("메뉴 선택", 
                               ("매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# ==========================================
# 1. 매입 자료 입력
# ==========================================
elif menu_choice == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_v = load_data("거래처")
    df_i = load_data("품목")
    df_h = load_data("단가이력")
    
    # 1. 단가이력 시트에서 최신 단가 찾기
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
            # 💡 [핵심 로직] 이력이 있으면 이력단가, 없으면 품목시트 기본단가 적용
            base_price = 0
            if not df_i.empty and item in df_i['제품명'].values:
                base_price = df_i[df_i['제품명'] == item]['단가'].values[0]
            
            # 최종 단가 결정: 이력에 있으면 이력값, 없으면 기본값
            final_price = item_price_map.get(item, base_price)
            
            qty = st.number_input("수량", min_value=1)
            # key를 주지 않거나, key를 품목명에 따라 바꾸면 값이 갱신됩니다.
            price = st.number_input("단가", value=int(final_price), min_value=0)
            remarks = st.text_input("비고")
            submit = st.form_submit_button("입력 완료")

    if submit:
        df_p = load_data("매입자료")
        new = pd.DataFrame([{"매입일자": str(date_input), "거래처": vendor, "품목명": item, "수량": qty, "단가": price, "총액": qty*price, "비고": remarks}])
        if not df_p.empty: new = new[df_p.columns]
        conn.update(worksheet="매입자료", data=pd.concat([df_p, new], ignore_index=True))
        st.success(f"✅ {item} 단가 {price}원으로 저장 완료!")
        st.rerun()

# ==========================================
# 2. 거래처 등록
# ==========================================
elif menu_choice == "거래처 등록":
    st.title("🏢 신규 거래처 등록")
    with st.form("vendor_form", clear_on_submit=True):
        v_name = st.text_input("거래처명 *")
        v_biz = st.text_input("사업자번호")
        submitted = st.form_submit_button("거래처 저장하기")
    
    if submitted and v_name:
        df = load_data("거래처")
        new = pd.DataFrame([{"거래처명": v_name, "사업자등록번호": v_biz}])
        conn.update(worksheet="거래처", data=pd.concat([df, new], ignore_index=True))
        st.rerun()
    st.dataframe(load_data("거래처"), use_container_width=True)

# ==========================================
# 3. 품목 등록
# ==========================================
elif menu_choice == "품목 등록":
    st.title("📦 품목 등록/수정")
    with st.form("item_form", clear_on_submit=True):
        i_name = st.text_input("제품명 *")
        i_price = st.number_input("기본 단가", min_value=0)
        submitted = st.form_submit_button("등록/수정")
        
    if submitted and i_name:
        df = load_data("품목")
        hist = load_data("단가이력")
        # 품목 시트 업데이트
        if not df.empty and i_name in df['제품명'].values:
            df.loc[df['제품명'] == i_name, '단가'] = i_price
        else:
            df = pd.concat([df, pd.DataFrame([{"제품명": i_name, "단가": i_price}])], ignore_index=True)
        conn.update(worksheet="품목", data=df)
        # 단가이력 기록
        new_h = pd.DataFrame([{"품목명": i_name, "단가": i_price, "변경일자": str(date.today())}])
        conn.update(worksheet="단가이력", data=pd.concat([hist, new_h], ignore_index=True))
        st.rerun()
    st.dataframe(load_data("품목"), use_container_width=True)

# ==========================================
# 4. 단가변동이력
# ==========================================
elif menu_choice == "단가변동이력":
    st.title("📈 품목별 단가 변동 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

# ==========================================
# 5. 거래처별 내역
# ==========================================
elif menu_choice == "거래처별 내역":
    st.title("🔍 거래처별 조회")
    df = load_data("매입자료")
    if not df.empty:
        sel = st.selectbox("거래처 선택", df['거래처'].unique())
        st.dataframe(df[df['거래처']==sel], use_container_width=True)