import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. CSS 설정 (인쇄 시 제목 제거 및 폰트 축소)
st.markdown("""
    <style>
    table { width: 100% !important; max-width: 100% !important; border-collapse: collapse !important; }
    th, td { border: 1px solid black !important; padding: 8px !important; text-align: center !important; }
    @media print {
        [data-testid="stSidebar"], .stAppHeader, .stButton, .stForm, .stRadio, .stMetric, .stInfo { display: none !important; }
        h1, h2, h3, h4, h5, h6 { display: none !important; } 
        #printable-area { display: block !important; width: 100% !important; margin: 0 !important; padding: 5px !important; }
        table { font-size: 9pt !important; }
        td, th { padding: 3px 5px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
def load_data(ws):
    try:
        return conn.read(worksheet=ws)
    except:
        return pd.DataFrame()

st.title("🏢 현대다이텍 시스템")

# 4. 사이드바 메뉴
menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 5. 각 메뉴별 기능 구현
if menu == "종합 대시보드":
    st.subheader("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 매입액", f"{int(curr['총액'].sum()):,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        st.subheader("🏆 거래처별 매입 비중")
        if not curr.empty:
            chart = alt.Chart(curr.groupby('거래처')['총액'].sum().reset_index()).mark_bar().encode(
                x=alt.X('거래처', axis=alt.Axis(labelAngle=0)), y='총액'
            )
            st.altair_chart(chart, use_container_width=True)

elif menu == "매입 자료 입력":
    st.subheader("📝 원부자재 매입 내역 등록")
    df_v = load_data("거래처")
    df_i = load_data("품목")
    
    with st.form("buy_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d = c1.date_input("매입 일자")
        v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
        i = c2.selectbox("품목", df_i['제품명'].tolist() if not df_i.empty else [])
        
        # [오류 수정] 데이터가 있을 때만 단가 가져오기, 없을 시 0으로 처리
        base_price = 0
        if not df_i.empty and i in df_i['제품명'].values:
            base_price = int(df_i.loc[df_i['제품명'] == i, '단가'].iloc[0])
            
        q = c2.number_input("수량", 1)
        p = c2.number_input("단가", value=base_price)
        rem = st.text_input("비고")
        
        if st.form_submit_button("✅ 내역 등록"):
            current_df = conn.read(worksheet="매입자료")
            new_row = pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "총액":q*p, "비고":rem}])
            conn.update(worksheet="매입자료", data=pd.concat([current_df, new_row], ignore_index=True))
            st.success("등록 완료되었습니다.")
            st.rerun()
    st.dataframe(load_data("매입자료").tail(10), use_container_width=True)

elif menu == "거래처 등록":
    st.subheader("🏢 거래처 등록 및 정보 수정")
    mode = st.radio("작업", ["신규 등록", "정보 수정"], horizontal=True)
    df_v = load_data("거래처")
    with st.form("cust_form", clear_on_submit=True):
        target = st.selectbox("거래처 선택", df_v['거래처명'].tolist()) if mode=="정보 수정" else None
        n = st.text_input("거래처명", value=df_v[df_v['거래처명']==target].iloc[0]['거래처명'] if target else "")
        b = st.text_input("사업자번호", value=df_v[df_v['거래처명']==target].iloc[0]['사업자등록번호'] if target else "")
        if st.form_submit_button("💾 저장"):
            if mode=="신규 등록":
                df = conn.read(worksheet="거래처")
                conn.update(worksheet="거래처", data=pd.concat([df, pd.DataFrame([{"거래처명":n, "사업자등록번호":b}])], ignore_index=True))
            else:
                df_all = conn.read(worksheet="거래처")
                idx = df_all.index[df_all['거래처명'] == target][0]
                df_all.at[idx, '거래처명'] = n; df_all.at[idx, '사업자등록번호'] = b
                conn.update(worksheet="거래처", data=df_all)
            st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.subheader("📦 품목 등록 / 수정")
    mode = st.radio("작업", ["신규 등록", "정보 수정", "조회"], horizontal=True)
    df_i = load_data("품목")
    df_v = load_data("거래처")
    
    if mode in ["신규 등록", "정보 수정"]:
        with st.form("item_form", clear_on_submit=True):
            if mode == "정보 수정":
                target = st.selectbox("수정할 품목 선택", df_i['제품명'].tolist())
                row = df_i[df_i['제품명']==target].iloc[0]
                new_v = st.selectbox("거래처 변경", df_v['거래처명'].tolist(), index=df_v['거래처명'].tolist().index(row['주거래처']) if row['주거래처'] in df_v['거래처명'].tolist() else 0)
                new_p = st.number_input("단가 변경", value=int(row['단가']))
                if st.form_submit_button("💾 수정 완료"):
                    df_all = conn.read(worksheet="품목")
                    idx = df_all.index[df_all['제품명'] == target][0]
                    df_all.at[idx, '주거래처'] = new_v; df_all.at[idx, '단가'] = new_p
                    conn.update(worksheet="품목", data=df_all)
                    st.rerun()
            else:
                n = st.text_input("품목명"); v = st.selectbox("주 거래처", df_v['거래처명'].tolist()); p = st.number_input("단가", 0)
                if st.form_submit_button("💾 신규 등록"):
                    df = conn.read(worksheet="품목")
                    conn.update(worksheet="품목", data=pd.concat([df, pd.DataFrame([{"제품명":n, "주거래처":v, "단가":p}])], ignore_index=True))
                    st.rerun()
    elif mode == "조회":
        q = st.text_input("🔎 품명 검색")
        if q: df_i = df_i[df_i['제품명'].str.contains(q)]
    st.markdown("---"); st.subheader("📋 전체 품목 내역"); st.dataframe(df_i, use_container_width=True)

elif menu == "단가변동이력":
    st.subheader("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.subheader("🔍 상세 내역 조회")
    st.dataframe(load_data("매입자료"), use_container_width=True)

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        ym = st.selectbox("월", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        v = st.selectbox("거래처", df['거래처'].unique().tolist())
        f = df[(df['매입일자'].dt.strftime('%Y-%m') == ym) & (df['거래처'] == v)].sort_values('매입일자')
        f['매입일자'] = f['매입일자'].dt.strftime('%Y-%m-%d')
        f_print = f[['매입일자', '거래처', '품목명', '수량', '단가', '총액', '비고']].copy()
        f_print.columns = ['거래일', '거래처', '품목', '수량', '단가', '합계', '비고']
        st.markdown(f"<div id='printable-area'>{f_print.to_html(index=False)}<div style='font-size:16px; font-weight:bold; margin-top:10px;'>토탈금액: {int(f['총액'].sum()):,} 원</div></div>", unsafe_allow_html=True)