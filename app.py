import streamlit as st
import pandas as pd
from datetime import date
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
    }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 정제 함수
@st.cache_data(ttl=60)
def load_data(ws):
    try: 
        df = conn.read(worksheet=ws)
        if not df.empty:
            df.columns = df.columns.str.replace(r'\n', '', regex=True).str.strip()
            df = df.replace(r'\n', ' ', regex=True)
        return df
    except: return pd.DataFrame()

# 4. 공통 상단 제목
st.title("🏢 현대다이텍 시스템")

# 5. 사이드바 메뉴 (8개 전체)
if st.sidebar.button("🔄 시스템 새로고침"): st.cache_data.clear(); st.rerun()
menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "단가 검색", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 6. 각 메뉴별 기능 구현
if menu == "종합 대시보드":
    st.subheader("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        prev = df[(df['매입일자'].dt.month == (t.month-1 if t.month > 1 else 12)) & (df['매입일자'].dt.year == (t.year if t.month > 1 else t.year-1))]
        
        curr_sum = curr['총액'].sum()
        prev_sum = prev['총액'].sum()
        delta = curr_sum - prev_sum
        
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 매입액", f"{int(curr_sum):,} 원", f"전월 대비 {int(delta):,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        if not curr.empty:
            top_v = curr.groupby('거래처')['총액'].sum().idxmax()
            c3.metric("최다 매입 거래처", top_v)
        else: c3.metric("최다 매입 거래처", "-")
        
        st.subheader("🏆 거래처별 매입 비중")
        if not curr.empty:
            st.bar_chart(curr.groupby('거래처')['총액'].sum())
    else: st.info("매입 자료가 없습니다.")

elif menu == "단가 검색":
    st.subheader("🔎 품목별 최신 단가 검색")
    df_h = load_data("단가이력")
    if not df_h.empty:
        item = st.selectbox("품목 선택", df_h['품목명'].unique())
        st.dataframe(df_h[df_h['품목명'] == item].sort_values('변경일자', ascending=False), use_container_width=True)

elif menu == "매입 자료 입력":
    st.subheader("📝 원부자재 매입 내역 등록")
    df_v, df_i = load_data("거래처"), load_data("품목")
    sel_i = st.selectbox("품목 선택", df_i['제품명'].tolist() if not df_i.empty else [])
    default_p = int(df_i[df_i['제품명'] == sel_i].iloc[0]['단가']) if not df_i.empty and sel_i and not df_i[df_i['제품명'] == sel_i].empty else 0
    with st.form("buy_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d = c1.date_input("매입 일자"); v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
        i = c2.selectbox("품목", df_i['제품명'].tolist() if not df_i.empty else []); q = c2.number_input("수량", 1); p = c2.number_input("단가", value=default_p)
        if st.form_submit_button("✅ 내역 등록"):
            df = load_data("매입자료")
            conn.update("매입자료", pd.concat([df, pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "총액":q*p}])], ignore_index=True))
            st.rerun()
    st.dataframe(load_data("매입자료").tail(10), use_container_width=True)

elif menu == "거래처 등록":
    st.subheader("🏢 거래처 등록 및 정보 수정")
    mode = st.radio("작업 선택", ["신규 등록", "정보 수정"], horizontal=True)
    df_v = load_data("거래처")
    with st.form("cust_form", clear_on_submit=True):
        target = st.selectbox("거래처 선택 (수정 시)", [""] + df_v['거래처명'].tolist()) if mode == "정보 수정" else None
        c_name = st.text_input("거래처명", value=df_v[df_v['거래처명']==target].iloc[0]['거래처명'] if target else "")
        c_biz = st.text_input("사업자등록번호", value=df_v[df_v['거래처명']==target].iloc[0]['사업자등록번호'] if target else "")
        c_p1 = st.text_input("연락처1", value=df_v[df_v['거래처명']==target].iloc[0]['연락처1'] if target else "")
        c_p2 = st.text_input("연락처2", value=df_v[df_v['거래처명']==target].iloc[0]['연락처2'] if target else "")
        c_fax = st.text_input("팩스번호", value=df_v[df_v['거래처명']==target].iloc[0]['팩스번호'] if target else "")
        c_rem = st.text_input("비고", value=df_v[df_v['거래처명']==target].iloc[0]['비고'] if target else "")
        if st.form_submit_button("💾 저장"):
            if mode == "신규 등록":
                conn.update("거래처", pd.concat([df_v, pd.DataFrame([{"거래처명":c_name, "사업자등록번호":c_biz, "연락처1":c_p1, "연락처2":c_p2, "팩스번호":c_fax, "비고":c_rem}])], ignore_index=True))
            else:
                idx = df_v[df_v['거래처명'] == target].index[0]
                df_v.loc[idx] = [c_name, c_biz, c_p1, c_p2, c_fax, c_rem]
                conn.update("거래처", df_v)
            st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.subheader("📦 품목 등록 및 정보 수정")
    mode = st.radio("작업 선택", ["신규 등록", "정보 수정"], horizontal=True)
    df_i, df_v = load_data("품목"), load_data("거래처")
    with st.form("item_form", clear_on_submit=True):
        target = st.selectbox("품목 선택 (수정 시)", [""] + df_i['제품명'].tolist()) if mode == "정보 수정" else None
        p_name = st.text_input("품목명", value=df_i[df_i['제품명']==target].iloc[0]['제품명'] if target else "")
        p_vendor = st.selectbox("주 거래처", df_v['거래처명'].tolist(), index=df_v['거래처명'].tolist().index(df_i[df_i['제품명']==target].iloc[0]['주거래처']) if target else 0)
        p_price = st.number_input("단가", value=int(df_i[df_i['제품명']==target].iloc[0]['단가']) if target else 0)
        if st.form_submit_button("💾 저장"):
            if mode == "신규 등록":
                conn.update("품목", pd.concat([df_i, pd.DataFrame([{"제품명":p_name, "주거래처":p_vendor, "단가":p_price}])], ignore_index=True))
            else:
                idx = df_i[df_i['제품명'] == target].index[0]
                df_i.loc[idx] = [p_name, p_vendor, p_price]
                conn.update("품목", df_i)
            st.rerun()
    st.dataframe(df_i, use_container_width=True)

elif menu == "단가변동이력":
    st.subheader("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.subheader("🔍 상세 내역 조회")
    df = load_data("매입자료")
    v = st.selectbox("거래처 선택", ["전체"] + df['거래처'].unique().tolist())
    st.dataframe(df[df['거래처'] == v] if v != "전체" else df, use_container_width=True)

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        sel_ym = st.selectbox("월 선택", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        sel_v = st.selectbox("거래처 선택", df['거래처'].unique().tolist())
        filtered = df[(df['매입일자'].dt.strftime('%Y-%m') == sel_ym) & (df['거래처'] == sel_v)]
        
        st.markdown(f"""<div id='printable-area'>
            <h2>[{sel_v}] {sel_ym}월 매입 정산서</h2>
            {filtered.to_html(index=False)}
            <h3>💰 합계 금액: {int(filtered['총액'].sum()):,} 원</h3>
        </div>""", unsafe_allow_html=True)
        st.info("💡 'Ctrl + P'를 누르면 위 정산서 양식만 출력됩니다.")