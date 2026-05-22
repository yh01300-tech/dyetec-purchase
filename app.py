import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 인쇄 최적화 CSS
st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"], .stAppHeader, .stButton, .stForm, .stRadio, .stMetric, .stInfo { display: none !important; }
        #printable-area { display: block !important; width: 100% !important; }
        table { width: 100% !important; border-collapse: collapse !important; table-layout: fixed !important; }
        th, td { border: 1px solid black !important; padding: 8px !important; word-wrap: break-word !important; }
        h2, h3 { color: black !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 정제
@st.cache_data(ttl=60)
def load_data(ws):
    try: 
        df = conn.read(worksheet=ws)
        if not df.empty:
            df.columns = df.columns.str.replace(r'\n', '', regex=True).str.strip()
            df = df.replace(r'\n', ' ', regex=True)
        return df
    except: return pd.DataFrame()

st.title("🏢 현대다이텍 시스템")

# 4. 사이드바 메뉴 (단가 검색 삭제, 7개 메뉴 구성)
if st.sidebar.button("🔄 시스템 새로고침"): st.cache_data.clear(); st.rerun()
menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 5. 각 메뉴별 상세 구현
if menu == "종합 대시보드":
    st.subheader("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        prev_m = 12 if t.month == 1 else t.month - 1
        prev = df[df['매입일자'].dt.month == prev_m]
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 매입액", f"{int(curr['총액'].sum()):,} 원", f"전월 대비 {int(curr['총액'].sum() - prev['총액'].sum()):,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        if not curr.empty: c3.metric("최다 매입 거래처", curr.groupby('거래처')['총액'].sum().idxmax())
        st.subheader("🏆 거래처별 매입 비중")
        if not curr.empty: st.bar_chart(curr.groupby('거래처')['총액'].sum())

elif menu == "매입 자료 입력":
    st.subheader("📝 원부자재 매입 내역 등록")
    df_v, df_i = load_data("거래처"), load_data("품목")
    with st.form("buy_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d = c1.date_input("매입 일자"); v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
        i = c2.selectbox("품목", df_i['제품명'].tolist() if not df_i.empty else []); q = c2.number_input("수량", 1); p = c2.number_input("단가", 0)
        rem = st.text_input("비고")
        if st.form_submit_button("✅ 내역 등록"):
            df = load_data("매입자료")
            conn.update("매입자료", pd.concat([df, pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "총액":q*p, "비고":rem}])], ignore_index=True))
            st.rerun()
    st.dataframe(load_data("매입자료").tail(10), use_container_width=True)

elif menu == "거래처 등록":
    st.subheader("🏢 거래처 등록 및 정보 수정")
    mode = st.radio("작업", ["신규 등록", "정보 수정"], horizontal=True)
    df_v = load_data("거래처")
    with st.form("cust_form", clear_on_submit=True):
        target = st.selectbox("거래처 선택", df_v['거래처명'].tolist()) if mode=="정보 수정" else None
        row = df_v[df_v['거래처명']==target].iloc[0] if target else {}
        c1, c2 = st.columns(2)
        n = c1.text_input("거래처명", value=row.get('거래처명',''))
        b = c1.text_input("사업자번호", value=row.get('사업자등록번호',''))
        p1 = c1.text_input("연락처1", value=row.get('연락처1',''))
        p2 = c2.text_input("연락처2", value=row.get('연락처2',''))
        fax = c2.text_input("팩스번호", value=row.get('팩스번호',''))
        rem = c2.text_input("비고", value=row.get('비고',''))
        if st.form_submit_button("💾 저장"):
            if mode=="신규 등록": conn.update("거래처", pd.concat([df_v, pd.DataFrame([{"거래처명":n, "사업자등록번호":b, "연락처1":p1, "연락처2":p2, "팩스번호":fax, "비고":rem}])], ignore_index=True))
            else: 
                idx = df_v[df_v['거래처명']==target].index[0]
                df_v.at[idx, '거래처명'] = n; df_v.at[idx, '사업자등록번호'] = b; df_v.at[idx, '연락처1'] = p1; df_v.at[idx, '연락처2'] = p2; df_v.at[idx, '팩스번호'] = fax; df_v.at[idx, '비고'] = rem
                conn.update("거래처", df_v)
            st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.subheader("📦 품목 등록 / 수정 및 단가 조회")
    mode = st.radio("작업", ["신규 등록", "정보 수정", "조회"], horizontal=True)
    df_i, df_v = load_data("품목"), load_data("거래처")
    
    if mode in ["신규 등록", "정보 수정"]:
        with st.form("item_form", clear_on_submit=True):
            target = st.selectbox("품목 선택", df_i['제품명'].tolist()) if mode=="정보 수정" else None
            row = df_i[df_i['제품명']==target].iloc[0] if target else {}
            n = st.text_input("품목명", value=row.get('제품명',''))
            opts = df_v['거래처명'].tolist(); v = st.selectbox("주 거래처", opts, index=opts.index(row.get('주거래처')) if row.get('주거래처') in opts else 0)
            p = st.number_input("단가", value=int(row.get('단가', 0)))
            if st.form_submit_button("💾 저장"):
                if mode=="신규 등록": conn.update("품목", pd.concat([df_i, pd.DataFrame([{"제품명":n, "주거래처":v, "단가":p}])], ignore_index=True))
                else:
                    idx = df_i[df_i['제품명']==target].index[0]
                    df_i.at[idx, '제품명'] = n; df_i.at[idx, '주거래처'] = v; df_i.at[idx, '단가'] = p
                    conn.update("품목", df_i)
                st.rerun()
    else:
        st.write("🔎 품목별 단가 검색")
        q = st.text_input("검색할 품목명을 입력하세요 (전체 조회 시 공란)")
        df_view = df_i[df_i['제품명'].str.contains(q)] if q else df_i
        st.dataframe(df_view, use_container_width=True)

elif menu == "단가변동이력":
    st.subheader("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.subheader("🔍 상세 내역 조회")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        c1, c2, c3 = st.columns(3)
        v = c1.selectbox("거래처", ["전체"] + df['거래처'].unique().tolist())
        date_range = c2.date_input("조회 기간 선택", value=(date.today()-timedelta(days=30), date.today()))
        i = c3.selectbox("품목", ["전체"] + df['품목명'].unique().tolist())
        if v != "전체": df = df[df['거래처'] == v]
        if i != "전체": df = df[df['품목명'] == i]
        if len(date_range) == 2:
            start_d, end_d = date_range
            df = df[(df['매입일자'].dt.date >= start_d) & (df['매입일자'].dt.date <= end_d)]
        st.dataframe(df.sort_values('매입일자', ascending=False), use_container_width=True)

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        ym = st.selectbox("월", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        v = st.selectbox("거래처", df['거래처'].unique().tolist())
        f = df[(df['매입일자'].dt.strftime('%Y-%m') == ym) & (df['거래처'] == v)]
        st.markdown(f"<div id='printable-area'><h2>[{v}] {ym}월 매입 정산서</h2>{f.to_html(index=False)}<h3>합계: {int(f['총액'].sum()):,} 원</h3></div>", unsafe_allow_html=True)