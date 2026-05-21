import streamlit as st
import pandas as pd
from datetime import date
import os
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

# 2. 사이드바 (로고 및 새로고침)
try:
    if os.path.exists("logo.png"):
        st.logo("logo.png")
    else:
        st.sidebar.title("🏢 현대다이텍 시스템")
except Exception:
    st.sidebar.title("🏢 현대다이텍 시스템")

if st.sidebar.button("🔄 시스템 새로고침 (오류 해결)"):
    st.cache_data.clear()
    st.rerun()

# 💡 첫 번째 메뉴로 '종합 대시보드'가 추가되었습니다.
menu_choice = st.sidebar.radio("메뉴 선택", ("종합 대시보드", "매입 자료 입력", "거래처 등록", "품목 등록", "단가변동이력", "거래처별 내역"))

# ==========================================
# 💡 1. 종합 대시보드 (신규 기능)
# ==========================================
if menu_choice == "종합 대시보드":
    st.title("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    
    if df.empty or '매입일자' not in df.columns or '총액' not in df.columns:
        st.info("📈 매입 데이터가 충분히 누적되면 대시보드가 자동으로 생성됩니다.")
    else:
        # 데이터 안전하게 변환
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        df['총액'] = pd.to_numeric(df['총액'], errors='coerce').fillna(0)
        valid_df = df.dropna(subset=['매입일자_dt'])
        
        if valid_df.empty:
            st.info("유효한 날짜 데이터가 없습니다.")
        else:
            # 날짜 기준 설정 (이번 달, 지난 달)
            today = date.today()
            this_month = today.month
            this_year = today.year
            
            if this_month == 1:
                last_month = 12
                last_month_year = this_year - 1
            else:
                last_month = this_month - 1
                last_month_year = this_year
            
            # 데이터 분류
            curr_df = valid_df[(valid_df['매입일자_dt'].dt.year == this_year) & (valid_df['매입일자_dt'].dt.month == this_month)]
            prev_df = valid_df[(valid_df['매입일자_dt'].dt.year == last_month_year) & (valid_df['매입일자_dt'].dt.month == last_month)]
            
            curr_total = curr_df['총액'].sum()
            prev_total = prev_df['총액'].sum()
            diff = curr_total - prev_total
            
            # 상단 핵심 요약 (Metric)
            st.subheader(f"🗓️ {this_year}년 {this_month}월 매입 요약")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.metric(label="이번 달 총 매입액", value=f"{int(curr_total):,} 원", delta=f"전월 대비 {int(diff):,} 원" if prev_total > 0 else None)
            with c2:
                st.metric(label="이번 달 매입 건수", value=f"{len(curr_df)} 건")
            with c3:
                top_vendor = curr_df.groupby('거래처')['총액'].sum().idxmax() if not curr_df.empty else "데이터 없음"
                st.metric(label="최다 매입 거래처", value=str(top_vendor))
            
            st.divider() # 시각적 구분선
            
            # 하단 그래프
            st.subheader(f"🏆 {this_month}월 거래처별 매입 비중 (단위: 원)")
            if not curr_df.empty and '거래처' in curr_df.columns:
                vendor_totals = curr_df.groupby('거래처')['총액'].sum().reset_index()
                # 거래처명을 인덱스로 설정하여 깔끔한 바 차트 생성
                st.bar_chart(vendor_totals.set_index('거래처'))
            else:
                st.info("이번 달 등록된 매입 내역이 없어 그래프를 표시할 수 없습니다.")

# ==========================================
# 2. 매입 자료 입력
# ==========================================
elif menu_choice == "매입 자료 입력":
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
        price = st.number_input("단가", value=int(final_p), min_value=0, key=f"p