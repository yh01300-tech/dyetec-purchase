import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import altair as alt

# 1. 페이지 설정 및 CSS (인쇄 최적화)
st.set_page_config(page_title="현대다이텍 통합 관리 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
    table { width: 100% !important; border-collapse: collapse !important; }
    th, td { border: 1px solid black !important; padding: 8px !important; text-align: center !important; }
    @media print {
        [data-testid="stSidebar"], .stButton { display: none !important; }
        h1, h2, h3, h4, h5, h6 { display: none !important; } 
        #printable-area { display: block !important; width: 100% !important; margin: 0 !important; padding: 5px !important; }
        table { font-size: 9pt !important; }
        td, th { padding: 3px 5px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 로드 함수 (실시간 데이터 조회)
def load_data(ws): 
    try: return conn.read(worksheet=ws, ttl=0)
    except: return pd.DataFrame()

# 단가 자동 반영 콜백
def on_item_change():
    item = st.session_state.item_select
    df_i = load_data("품목")
    if not df_i.empty and '제품명' in df_i.columns:
        match = df_i[df_i['제품명'] == item]
        if not match.empty:
            st.session_state.price_input = int(match.iloc[0]['단가'])
        else:
            st.session_state.price_input = 0
    else:
        st.session_state.price_input = 0

st.title("🏢 현대다이텍 통합 관리 시스템")

menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 3. 메뉴별 기능 구현
if menu == "종합 대시보드":
    st.subheader("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        prev_m = 12 if t.month == 1 else t.month - 1
        prev_y = t.year if t.month != 1 else t.year - 1
        prev = df[(df['매입일자'].dt.month == prev_m) & (df['매입일자'].dt.year == prev_y)]
        
        c1, c2, c3 = st.columns(3)
        diff = int(curr['총액'].sum() - prev['총액'].sum())
        c1.metric("이번 달 총 매입액", f"{int(curr['총액'].sum()):,} 원", f"전월 대비 {diff:,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        if not curr.empty: c3.metric("최다 매입 거래처", curr.groupby('거래처')['총액'].sum().idxmax())
        
        st.subheader("🏆 거래처별 매입 비중")
        if not curr.empty:
            chart = alt.Chart(curr.groupby('거래처')['총액'].sum().reset_index()).mark_bar().encode(
                x=alt.X('거래처', axis=alt.Axis(labelAngle=0)), y='총액'
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("매입 자료 데이터가 비어 있습니다.")

elif menu == "매입 자료 입력":
    st.subheader("📝 원부자재 매입 내역 등록")
    df_v, df_i = load_data("거래처"), load_data("품목")
    
    if 'price_input' not in st.session_state:
        if not df_i.empty and '단가' in df_i.columns:
            st.session_state.price_input = int(df_i.iloc[0]['단가'])
        else:
            st.session_state.price_input = 0

    c1, c2 = st.columns(2)
    d = c1.date_input("매입 일자")
    v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
    
    item_options = df_i['제품명'].tolist() if not df_i.empty else []
    i = c2.selectbox("품목", item_options, key="item_select", on_change=on_item_change)
    q = c2.number_input("수량", min_value=1, value=1)
    p = c2.number_input("단가", min_value=0, key="price_input")
    rem = st.text_input("비고")
    
    if st.button("✅ 내역 등록"):
        df = conn.read(worksheet="매입자료", ttl=0)
        new_row = pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "총액":q*p, "비고":rem}])
        conn.update(worksheet="매입자료", data=pd.concat([df, new_row], ignore_index=True))
        st.success("매입 내역이 성공적으로 누적 등록되었습니다.")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📋 현재 누적된 매입 내역 (전체)")
    st.dataframe(load_data("매입자료"), use_container_width=True)

elif menu == "거래처 등록":
    st.subheader("🏢 거래처 등록 및 정보 수정")
    mode = st.radio("작업", ["신규 등록", "정보 수정"], horizontal=True)
    df_v = load_data("거래처")
    if mode == "신규 등록":
        c1, c2 = st.columns(2)
        n = c1.text_input("거래처명"); b = c1.text_input("사업자번호")
        p1 = c1.text_input("연락처1"); p2 = c2.text_input("연락처2")
        fax = c2.text_input("팩스번호"); rem = c2.text_input("비고")
        if st.button("💾 저장"):
            df = conn.read(worksheet="거래처", ttl=0)
            conn.update(worksheet="거래처", data=pd.concat([df, pd.DataFrame([{"거래처명":n, "사업자등록번호":b, "연락처1":p1, "연락처2":p2, "팩스번호":fax, "비고":rem}])], ignore_index=True))
            st.rerun()
    else:
        target = st.selectbox("거래처 선택", df_v['거래처명'].tolist() if not df_v.empty else [])
        if target:
            row = df_v[df_v['거래처명'] == target].iloc[0]
            c1, c2 = st.columns(2)
            new_n = c1.text_input("거래처명", value=row['거래처명'])
            new_b = c1.text_input("사업자번호", value=row['사업자등록번호'])
            new_p1 = c1.text_input("연락처1", value=row['연락처1'])
            new_p2 = c2.text_input("연락처2", value=row['연락처2'])
            new_fax = c2.text_input("팩스번호", value=row['팩스번호'])
            new_rem = c2.text_input("비고", value=row['비고'])
            if st.button("💾 수정 저장"):
                df = conn.read(worksheet="거래처", ttl=0)
                idx = df.index[df['거래처명'] == target][0]
                df.at[idx, '거래처명'] = new_n; df.at[idx, '사업자등록번호'] = new_b
                df.at[idx, '연락처1'] = new_p1; df.at[idx, '연락처2'] = new_p2
                df.at[idx, '팩스번호'] = new_fax; df.at[idx, '비고'] = new_rem
                conn.update(worksheet="거래처", data=df)
                st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.subheader("📦 품목 등록 / 수정")
    mode = st.radio("작업", ["신규 등록", "정보 수정"], horizontal=True)
    df_i, df_v = load_data("품목"), load_data("거래처")
    if mode == "정보 수정":
        target = st.selectbox("수정할 품목", df_i['제품명'].tolist() if not df_i.empty else [])
        if target:
            row = df_i[df_i['제품명']==target].iloc[0]
            new_v = st.selectbox("거래처 변경", df_v['거래처명'].tolist() if not df_v.empty else [], index=df_v['거래처명'].tolist().index(row['주거래처']) if row['주거래처'] in df_v['거래처명'].tolist() else 0)
            new_p = st.number_input("단가 변경", value=int(row['단가']))
            if st.button("💾 수정 완료"):
                df = conn.read(worksheet="품목", ttl=0)
                idx = df.index[df['제품명'] == target][0]
                df.at[idx, '주거래처'] = new_v; df.at[idx, '단가'] = new_p
                conn.update(worksheet="품목", data=df)
                st.rerun()
    else:
        n = st.text_input("품목명"); v = st.selectbox("주 거래처", df_v['거래처명'].tolist() if not df_v.empty else []); p = st.number_input("단가", 0)
        if st.button("💾 신규 등록"):
            df = conn.read(worksheet="품목", ttl=0)
            conn.update(worksheet="품목", data=pd.concat([df, pd.DataFrame([{"제품명":n, "주거래처":v, "단가":p}])], ignore_index=True))
            st.rerun()
    st.dataframe(df_i, use_container_width=True)

elif menu == "단가변동이력": 
    st.subheader("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역": 
    st.subheader("🔍 상세 내역 조회 (기간/거래처/품목)")
    df = load_data("매입자료")
    
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        
        c1, c2, c3 = st.columns(3)
        v = c1.selectbox("거래처 선택", ["전체"] + df['거래처'].dropna().unique().tolist())
        date_range = c2.date_input("조회 기간 선택", value=(date.today() - timedelta(days=30), date.today()))
        i = c3.selectbox("품목 선택", ["전체"] + df['품목명'].dropna().unique().tolist())
        
        # 필터링 적용
        if v != "전체": 
            df = df[df['거래처'] == v]
        if i != "전체": 
            df = df[df['품목명'] == i]
            
        if len(date_range) == 2:
            start_d, end_d = date_range
            df = df[(df['매입일자'].dt.date >= start_d) & (df['매입일자'].dt.date <= end_d)]
        elif len(date_range) == 1:
            start_d = date_range[0]
            df = df[df['매입일자'].dt.date >= start_d]
            
        # 화면에 깔끔하게 보여주기 위해 날짜 포맷 변경
        df['매입일자'] = df['매입일자'].dt.strftime('%Y-%m-%d')
        
        st.markdown(f"**총 조회 건수: {len(df)} 건** | **총 합계 금액: {int(df['총액'].sum()) if not df.empty else 0:,} 원**")
        st.dataframe(df.sort_values('매입일자', ascending=False), use_container_width=True)
    else:
        st.info("매입 자료 데이터가 없습니다.")

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        ym = st.selectbox("월", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        v = st.selectbox("거래처", df['거래처'].unique().tolist())
        f = df[(df['매입일자'].dt.strftime('%Y-%m') == ym) & (df['거래처'] == v)].sort_values('매입일자')
        if not f.empty:
            f['매입일자'] = f['매입일자'].dt.strftime('%Y-%m-%d')
            f_print = f[['매입일자', '거래처', '품목명', '수량', '단가', '총액', '비고']].copy()
            f_print.columns = ['거래일', '거래처', '품목', '수량', '단가', '합계', '비고']
            st.markdown(f"<div id='printable-area'>{f_print.to_html(index=False)}<div style='font-size:16px; font-weight:bold; margin-top:10px;'>토탈금액: {int(f['총액'].sum()):,} 원</div></div>", unsafe_allow_html=True)
        else:
            st.info("선택한 월 및 거래처의 내역이 없습니다.")