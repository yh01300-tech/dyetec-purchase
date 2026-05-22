import streamlit as st
import pandas as pd
from datetime import date
import os
import altair as alt
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 인쇄 최적화 스타일
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        header { visibility: hidden !important; }
        .stButton, .stFormSubmitButton, .stRadio, .stTextInput, .stSelectbox { display: none !important; }
        .main .block-container { padding-top: 0rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)
def load_data(ws):
    try: return conn.read(worksheet=ws)
    except: return pd.DataFrame()

# 2. 사이드바 구성
if st.sidebar.button("🔄 시스템 전체 새로고침"): st.cache_data.clear(); st.rerun()
menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "단가 검색", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 3. 메뉴별 기능
if menu == "종합 대시보드":
    st.title("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        # 금월 데이터
        curr = df[(df['매입일자_dt'].dt.month == t.month) & (df['매입일자_dt'].dt.year == t.year)]
        # 전월 데이터
        prev_m = 12 if t.month == 1 else t.month - 1
        prev_y = t.year - 1 if t.month == 1 else t.year
        prev = df[(df['매입일자_dt'].dt.month == prev_m) & (df['매입일자_dt'].dt.year == prev_y)]
        
        curr_val = curr['총액'].sum()
        prev_val = prev['총액'].sum()
        delta = curr_val - prev_val
        
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 매입액", f"{int(curr_val):,} 원", f"전월 대비 {int(delta):,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        if not curr.empty: c3.metric("최다 매입 거래처", curr.groupby('거래처')['총액'].sum().idxmax())
        
        st.subheader("🏆 거래처별 매입 비중")
        if not curr.empty:
            chart = alt.Chart(curr.groupby('거래처')['총액'].sum().reset_index()).mark_bar().encode(
                x=alt.X('거래처', axis=alt.Axis(labelAngle=0)), y='총액'
            )
            st.altair_chart(chart, use_container_width=True)
    else: st.info("매입 자료가 없습니다.")

elif menu == "단가 검색":
    st.title("🔎 품목별 최신 단가 검색")
    df_h = load_data("단가이력")
    if not df_h.empty:
        item = st.selectbox("품목 선택", df_h['품목명'].unique())
        hist = df_h[df_h['품목명'] == item].sort_values('변경일자', ascending=False)
        st.write(f"현재 최신 단가: {int(hist.iloc[0]['단가']):,} 원 / 최종 변동일: {hist.iloc[0]['변경일자']}")
        st.dataframe(hist, use_container_width=True)

elif menu == "매입 자료 입력":
    st.title("📝 원부자재 매입 내역 등록")
    df_v = load_data("거래처"); df_i = load_data("품목")
    sel_i = st.selectbox("품목 선택 (단가 자동 호출)", df_i['제품명'].tolist() if not df_i.empty else [])
    default_p = int(df_i[df_i['제품명'] == sel_i].iloc[0]['단가']) if not df_i.empty and sel_i and not df_i[df_i['제품명'] == sel_i].empty else 0
    with st.form("buy_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d = c1.date_input("매입 일자"); v = c1.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
        q = c2.number_input("수량", min_value=1); p = c2.number_input("단가", value=default_p, min_value=0)
        rem = st.text_input("비고"); sub = st.form_submit_button("✅ 내역 등록")
    if sub:
        df = load_data("매입자료")
        conn.update("매입자료", pd.concat([df, pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":sel_i, "수량":q, "단가":p, "총액":q*p, "비고":rem}])], ignore_index=True))
        st.rerun()
    st.dataframe(load_data("매입자료").tail(10), use_container_width=True)

elif menu == "거래처 등록":
    st.title("🏢 거래처 등록 및 정보 수정")
    df_v = load_data("거래처")
    action = st.radio("작업", ("신규 등록", "정보 수정"), horizontal=True)
    d = {}
    if action == "정보 수정" and not df_v.empty:
        sel = st.selectbox("수정할 거래처", df_v['거래처명'].unique())
        d = df_v[df_v['거래처명'] == sel].iloc[0].to_dict()
    with st.form("v_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("거래처명", value=d.get('거래처명', '')); biz = c1.text_input("사업자번호", value=d.get('사업자등록번호', ''))
        p1 = c1.text_input("연락처1", value=d.get('연락처1', '')); p2 = c2.text_input("연락처2", value=d.get('연락처2', ''))
        fax = c2.text_input("팩스번호", value=d.get('팩스번호', '')); addr = c2.text_input("주소", value=d.get('주소', ''))
        rem = st.text_input("비고", value=d.get('비고', '')); sub = st.form_submit_button("저장")
    if sub:
        if action == "신규 등록": conn.update("거래처", pd.concat([df_v, pd.DataFrame([{"거래처명":n, "사업자등록번호":biz, "연락처1":p1, "연락처2":p2, "팩스번호":fax, "주소":addr, "비고":rem}])], ignore_index=True))
        else:
            idx = df_v[df_v['거래처명'] == d['거래처명']].index[0]
            for k, v in {"거래처명":n, "사업자등록번호":biz, "연락처1":p1, "연락처2":p2, "팩스번호":fax, "주소":addr, "비고":rem}.items(): df_v.at[idx, k] = v
            conn.update("거래처", df_v)
        st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "품목 등록":
    st.title("📦 품목 등록 및 정보 수정")
    df_i = load_data("품목"); df_v = load_data("거래처")
    action = st.radio("작업", ("신규 등록", "정보 수정"), horizontal=True)
    d = {}
    if action == "정보 수정" and not df_i.empty:
        sel = st.selectbox("수정할 품목", df_i['제품명'].unique())
        d = df_i[df_i['제품명'] == sel].iloc[0].to_dict()
    with st.form("i_form", clear_on_submit=True):
        n = st.text_input("제품명", value=d.get('제품명', ''))
        v = st.selectbox("거래처", df_v['거래처명'] if not df_v.empty else [], index=df_v['거래처명'].tolist().index(d['주거래처']) if d.get('주거래처') in df_v['거래처명'].tolist() else 0)
        p = st.number_input("단가", value=int(d.get('단가', 0))); sub = st.form_submit_button("저장")
    if sub:
        if action == "신규 등록": conn.update("품목", pd.concat([df_i, pd.DataFrame([{"제품명":n, "주거래처":v, "단가":p}])], ignore_index=True))
        else:
            idx = df_i[df_i['제품명'] == d['제품명']].index[0]
            df_i.at[idx, '단가'] = p; df_i.at[idx, '주거래처'] = v
            conn.update("품목", df_i)
        st.rerun()
    st.dataframe(df_i, use_container_width=True)

elif menu == "단가변동이력":
    st.title("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.title("🔍 상세 내역 조회")
    df = load_data("매입자료")
    if not df.empty:
        c1, c2 = st.columns(2)
        v = c1.selectbox("거래처", ["전체"] + df['거래처'].unique().tolist())
        i = c2.selectbox("품목", ["전체"] + df['품목명'].unique().tolist())
        if v != "전체": df = df[df['거래처'] == v]
        if i != "전체": df = df[df['품목명'] == i]
        st.dataframe(df, use_container_width=True)

elif menu == "월마감 정산서":
    st.title("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자_dt'] = pd.to_datetime(df['매입일자'], errors='coerce')
        sel_ym = st.selectbox("월 선택", sorted(df['매입일자_dt'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        sel_v = st.selectbox("거래처 선택", df['거래처'].unique().tolist())
        filtered = df[(df['매입일자_dt'].dt.strftime('%Y-%m') == sel_ym) & (df['거래처'] == sel_v)]
        st.dataframe(filtered, use_container_width=True)
        st.write(f"### 💰 합계 금액: {int(filtered['총액'].sum()):,} 원")
        if st.button("🖨️ 인쇄하기"):
            st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
    else: st.info("데이터가 없습니다.")