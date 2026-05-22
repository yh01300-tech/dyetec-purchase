import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="현대다이텍 시스템", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 인쇄 최적화 CSS (데이터 표와 합계 외 모든 UI 완벽 차단)
st.markdown("""
    <style>
    @media print {
        body * { visibility: hidden !important; }
        #printable-area, #printable-area * { visibility: visible !important; }
        #printable-area { position: absolute; left: 0; top: 0; width: 100%; }
        table { width: 100% !important; border-collapse: collapse !important; }
        th, td { border: 1px solid black !important; padding: 8px !important; text-align: center; }
        h2, h3 { color: black !important; }
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

# 5. 사이드바 메뉴 (8개 항목 복구)
if st.sidebar.button("🔄 시스템 새로고침"): st.cache_data.clear(); st.rerun()
menu = st.sidebar.radio("메뉴 선택", (
    "종합 대시보드", "단가 검색", "매입 자료 입력", "거래처 등록", 
    "품목 등록", "단가변동이력", "거래처별 내역", "월마감 정산서"
))

# 6. 각 메뉴 기능 구현
if menu == "종합 대시보드":
    st.subheader("📊 월간 매입 종합 대시보드")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        prev = df[df['매입일자'].dt.month == (12 if t.month == 1 else t.month - 1)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 매입액", f"{int(curr['총액'].sum()):,} 원")
        c2.metric("이번 달 매입 건수", f"{len(curr)} 건")
        if not curr.empty: c3.metric("최다 매입 거래처", curr.groupby('거래처')['총액'].sum().idxmax())
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
    with st.form("buy_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d, v = c1.date_input("매입 일자"), c1.selectbox("거래처", df_v['거래처명'].tolist())
        i, q = c2.selectbox("품목", df_i['제품명'].tolist()), c2.number_input("수량", 1)
        if st.form_submit_button("✅ 내역 등록"):
            df = load_data("매입자료")
            conn.update("매입자료", pd.concat([df, pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":q, "총액":0}])], ignore_index=True))
            st.rerun()

elif menu == "거래처 등록":
    st.subheader("🏢 거래처 등록 및 정보 수정")
    st.dataframe(load_data("거래처"), use_container_width=True)

elif menu == "품목 등록":
    st.subheader("📦 품목 등록 및 정보 수정")
    st.dataframe(load_data("품목"), use_container_width=True)

elif menu == "단가변동이력":
    st.subheader("📈 단가 변동 전체 이력")
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "거래처별 내역":
    st.subheader("🔍 상세 내역 조회")
    df = load_data("매입자료")
    v = st.selectbox("거래처 선택", ["전체"] + df['거래처'].unique().tolist())
    st.dataframe(df[df['거래처'] == v] if v != "전체" else df, use_container_width=True)

elif menu == "월마감 정산서":
    st.subheader("🖨️ 월마감 정산서")
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        sel_ym = st.selectbox("월 선택", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        sel_v = st.selectbox("거래처 선택", df['거래처'].unique().tolist())
        filtered = df[(df['매입일자'].dt.strftime('%Y-%m') == sel_ym) & (df['거래처'] == sel_v)]
        
        # 인쇄 영역 (HTML 테이블로 직접 변환)
        html_table = filtered.to_html(index=False, border=1)
        st.markdown(f"""
            <div id='printable-area'>
                <h2>[{sel_v}] {sel_ym}월 매입 정산서</h2>
                {html_table}
                <h3>💰 합계 금액: {int(filtered['총액'].sum()):,} 원</h3>
            </div>
        """, unsafe_allow_html=True)
        st.info("💡 'Ctrl + P'를 누르면 위 정산서 양식만 출력됩니다.")