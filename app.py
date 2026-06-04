import streamlit as st
import pandas as pd 
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import altair as alt
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="현대다이텍 통합 ERP", page_icon="🏢", layout="wide")

# 🚨 이 줄을 추가해 주세요! (구글 시트와 통신하는 'conn' 객체 생성)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 화면용 CSS (인쇄용 CSS는 모두 삭제)
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 3. 🖨️ 인쇄 전용 버튼 함수 정의 (이 함수는 그대로 둡니다)
# =====================================================================
def create_print_button(table_html, total_sum_html=""):
    html_code = f"""
    <button onclick="printDocument()" style="background-color: #0052CC; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">
        🖨️ 다중 페이지 인쇄하기
    </button>
    
    <script>
    function printDocument() {{
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>구매 내역 인쇄</title>
                <style>
                    body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; color: black; }}
                    h2 {{ text-align: center; margin-bottom: 20px; }}
                    .total-sum {{ font-size: 13pt; font-weight: bold; margin-bottom: 10px; text-align: right; }}
                    table {{ width: 100%; border-collapse: collapse; font-size: 10pt; border: 2px solid black; }}
                    th, td {{ border: 1px solid black; padding: 6px 4px; text-align: center; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                    
                    @media print {{
                        thead {{ display: table-header-group; }} 
                        tr {{ page-break-inside: avoid; }}       
                        @page {{ margin: 1cm; }}                 
                    }}
                </style>
            </head>
            <body>
                <h2>구매 내역</h2>
                {total_sum_html}
                {table_html} 
            </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        
        setTimeout(() => {{
            printWindow.print();
            printWindow.close();
        }}, 500);
    }}
    </script>
    """
    components.html(html_code, height=60)


# =====================================================================
# 4. 데이터 로드 및 상태 관리
# =====================================================================
# 변경할 코드
def load_data(ws): 
    try: 
        return conn.read(worksheet=ws, ttl=5)
    except Exception as e: 
        st.error(f"🚨 '{ws}' 시트 데이터를 불러오는 데 실패했습니다! 원인: {e}")
        return pd.DataFrame()

if 'temp_entries' not in st.session_state:
    st.session_state.temp_entries = pd.DataFrame(columns=["매입일자", "거래처", "품목명", "수량", "단가", "총액", "비고"])
if 'price_input' not in st.session_state: st.session_state.price_input = 0

def on_item_change():
    item = st.session_state.get('item_select')
    df_i = load_data("품목")
    if not df_i.empty and '제품명' in df_i.columns:
        match = df_i[df_i['제품명'] == item]
        if not match.empty:
            raw = str(match.iloc[0]['단가']).replace(',', '').replace('원', '').strip()
            try: st.session_state.price_input = int(float(raw))
            except: st.session_state.price_input = 0
        else: st.session_state.price_input = 0
    else: st.session_state.price_input = 0

# =====================================================================
# 5. 사이드바 구성
# =====================================================================
st.sidebar.markdown("### ⚙️ H-DYETEC ERP")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navigation", (
    "📊 경영 대시보드", 
    "📝 매입 전표 입력", 
    "🏢 거래처 마스터 관리", 
    "📦 품목 마스터 관리", 
    "📈 단가 변동 이력", 
    "🔍 매입 원장 상세조회", 
    "🖨️ 월마감 정산서 출력"
))
st.sidebar.markdown("---")
st.sidebar.caption("ⓒ 2026 Hyundai Dyetec SCM Team")

# =====================================================================
# 6. 메인 화면 로직
# =====================================================================
if menu == "📊 경영 대시보드":
    st.markdown("## 📊 경영 대시보드")
    st.divider()
    df = load_data("매입자료")
    if not df.empty and '매입일자' in df.columns:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        t = date.today()
        curr = df[(df['매입일자'].dt.month == t.month) & (df['매입일자'].dt.year == t.year)]
        prev = df[(df['매입일자'].dt.month == (t.month-1 if t.month > 1 else 12))]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            diff = int(curr['총액'].sum() - prev['총액'].sum())
            st.metric("당월 총 매입액", f"{int(curr['총액'].sum()):,} 원", f"전월 대비 {diff:,} 원")
        with c2:
            st.metric("당월 매입 전표 건수", f"{len(curr)} 건")
        with c3:
            if not curr.empty: 
                st.metric("당월 최다 매입 거래처", curr.groupby('거래처')['총액'].sum().idxmax())
        
        st.markdown("<br><br>#### 🏆 거래처별 매입 비중", unsafe_allow_html=True)
        if not curr.empty:
            chart = alt.Chart(curr.groupby('거래처')['총액'].sum().reset_index()).mark_bar(color='#0052CC').encode(
                x=alt.X('거래처', axis=alt.Axis(labelAngle=0, title=None)), 
                y=alt.Y('총액', axis=alt.Axis(title='매입액 (원)'))
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

elif menu == "📝 매입 전표 입력":
    st.markdown("## 📝 매입 전표 관리")
    st.divider()
    tab1, tab2, tab3 = st.tabs(["➕ 전표 일괄 입력", "📋 전표 원장 현황", "🗑️ 오등록 전표 삭제"])
    
    with tab1:
        df_v, df_i = load_data("거래처"), load_data("품목")
        with st.container():
            c1, c2, c3, c4 = st.columns([1.5, 2, 1, 1])
            d = c1.date_input("매입 일자")
            v = c2.selectbox("거래처", df_v['거래처명'].tolist() if not df_v.empty else [])
            i = c3.selectbox("품목", df_i['제품명'].tolist() if not df_i.empty else [], key="item_select", on_change=on_item_change)
            q = c4.number_input("수량", min_value=0, value=1)
            
            c5, c6 = st.columns([1.5, 3.5])
            p = c5.number_input("단가 (VAT별도)", min_value=0, value=st.session_state.price_input, key="price_input")
            rem = c6.text_input("적요 (비고)")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ 대기 목록에 전표 추가"):
                new_entry = pd.DataFrame([{"매입일자":str(d), "거래처":v, "품목명":i, "수량":int(q), "단가":int(p), "총액":int(q*p), "비고":rem}])
                st.session_state.temp_entries = pd.concat([st.session_state.temp_entries, new_entry], ignore_index=True)
                st.rerun()

        if not st.session_state.temp_entries.empty:
            st.markdown("---")
            st.dataframe(st.session_state.temp_entries, use_container_width=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🚀 서버로 일괄 전송"):
                    df = conn.read(worksheet="매입자료", ttl=0)
                    conn.update(worksheet="매입자료", data=pd.concat([df, st.session_state.temp_entries], ignore_index=True))
                    st.session_state.temp_entries = pd.DataFrame(columns=["매입일자", "거래처", "품목명", "수량", "단가", "총액", "비고"])
                    st.rerun()
            with col_b:
                if st.button("초기화 (대기열 비우기)"):
                    st.session_state.temp_entries = pd.DataFrame(columns=["매입일자", "거래처", "품목명", "수량", "단가", "총액", "비고"])
                    st.rerun()

    with tab2:
        df_display = load_data("매입자료")
        if not df_display.empty:
            st.dataframe(df_display.sort_values('매입일자', ascending=False), use_container_width=True)
            
    with tab3:
        df_del = load_data("매입자료")
        if not df_del.empty:
            df_del['표시'] = "[No." + df_del.index.astype(str) + "]  " + df_del['매입일자'].astype(str) + " | " + df_del['거래처'].astype(str) + " | " + df_del['품목명'].astype(str) + " | " + df_del['총액'].astype(str) + "원"
            target = st.selectbox("삭제할 전표 선택", df_del['표시'].tolist()[::-1])
            if st.button("선택 전표 DB에서 삭제"):
                del_idx = int(target.split("]")[0].replace("[No.", ""))
                df_realtime = conn.read(worksheet="매입자료", ttl=0)
                conn.update(worksheet="매입자료", data=df_realtime.drop(index=del_idx))
                st.rerun()

elif menu == "🏢 거래처 마스터 관리":
    st.markdown("## 🏢 거래처 마스터 관리")
    st.divider()
    tab1, tab2 = st.tabs(["➕ 거래처 신규 등록", "✏️ 거래처 정보 수정"])
    df_v = load_data("거래처")
    with tab1:
        c1, c2 = st.columns(2)
        n = c1.text_input("거래처명 (상호)"); b = c1.text_input("사업자등록번호")
        p1 = c1.text_input("연락처 1"); p2 = c2.text_input("연락처 2 (담당자 등)")
        fax = c2.text_input("팩스번호"); rem = c2.text_input("적요 (비고)")
        if st.button("저장 (신규 등록)"):
            df = conn.read(worksheet="거래처", ttl=0)
            conn.update(worksheet="거래처", data=pd.concat([df, pd.DataFrame([{"거래처명":n, "사업자등록번호":b, "연락처1":p1, "연락처2":p2, "팩스번호":fax, "비고":rem}])], ignore_index=True))
            st.rerun()
    with tab2:
        target = st.selectbox("마스터 정보를 수정할 거래처 선택", df_v['거래처명'].tolist() if not df_v.empty else [])
        if target:
            row = df_v[df_v['거래처명'] == target].iloc[0]
            c1, c2 = st.columns(2)
            n = c1.text_input("거래처명 (수정)", value=row['거래처명']); b = c1.text_input("사업자번호 (수정)", value=row['사업자등록번호'])
            p1 = c1.text_input("연락처1 (수정)", value=row['연락처1']); p2 = c2.text_input("연락처2 (수정)", value=row['연락처2'])
            fax = c2.text_input("팩스 (수정)", value=row['팩스번호']); rem = c2.text_input("비고 (수정)", value=row['비고'])
            if st.button("업데이트 (수정 완료)"):
                df = conn.read(worksheet="거래처", ttl=0)
                idx = df.index[df['거래처명'] == target][0]
                for col, val in zip(['거래처명','사업자등록번호','연락처1','연락처2','팩스번호','비고'], [n,b,p1,p2,fax,rem]): df.at[idx, col] = val
                conn.update(worksheet="거래처", data=df)
                st.rerun()
    st.dataframe(df_v, use_container_width=True)

elif menu == "📦 품목 마스터 관리":
    st.markdown("## 📦 품목 마스터 관리")
    st.divider()
    tab1, tab2 = st.tabs(["➕ 품목 신규 등록", "✏️ 품목 정보 및 단가 수정"])
    df_i, df_v = load_data("품목"), load_data("거래처")
    with tab1:
        c1, c2 = st.columns(2)
        n = c1.text_input("신규 품목명"); v = c2.selectbox("주 거래처 매핑", df_v['거래처명'].tolist() if not df_v.empty else [])
        p = st.number_input("기준 단가 설정 (원)", 0)
        if st.button("품목 마스터 저장"):
            df = conn.read(worksheet="품목", ttl=0)
            conn.update(worksheet="품목", data=pd.concat([df, pd.DataFrame([{"제품명":n, "주거래처":v, "단가":p}])], ignore_index=True))
            st.rerun()
    with tab2:
        target = st.selectbox("수정할 품목 선택", df_i['제품명'].tolist() if not df_i.empty else [])
        if target:
            row = df_i[df_i['제품명']==target].iloc[0]
            v = st.selectbox("주 거래처 변경", df_v['거래처명'].tolist(), index=df_v['거래처명'].tolist().index(row['주거래처']) if row['주거래처'] in df_v['거래처명'].tolist() else 0)
            
            # 기존 단가를 변수로 미리 저장해 둡니다.
            old_price = int(float(str(row['단가']).replace(',','')))
            p = st.number_input("단가 변경 (원)", value=old_price)
            
            if st.button("품목 정보 업데이트"):
                # 1. 기존 로직: '품목' 시트 업데이트
                df = conn.read(worksheet="품목", ttl=0)
                idx = df.index[df['제품명'] == target][0]
                df.at[idx, '주거래처'] = v; df.at[idx, '단가'] = p
                conn.update(worksheet="품목", data=df)
                
                # 2. 🚨 추가된 로직: 단가가 실제로 변경되었을 때만 '단가이력' 시트에 기록 추가
                if p != old_price:
                    df_hist = conn.read(worksheet="단가이력", ttl=0)
                    new_hist = pd.DataFrame([{
                        "변경일자": date.today().strftime("%Y-%m-%d"),
                        "품목명": target,
                        "이전단가": old_price,
                        "변경단가": p
                    }])
                    # 기존 이력 데이터에 새 이력 행(Row)을 병합하여 구글 시트 업데이트
                    conn.update(worksheet="단가이력", data=pd.concat([df_hist, new_hist], ignore_index=True))

                st.rerun()
                
    st.dataframe(df_i, use_container_width=True)

elif menu == "📈 단가 변동 이력": 
    st.markdown("## 📈 단가 변동 이력 조회")
    st.divider()
    st.dataframe(load_data("단가이력"), use_container_width=True)

elif menu == "🔍 매입 원장 상세조회":
    st.markdown("## 🔍 매입 원장 상세조회")
    st.divider()
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        c1, c2, c3 = st.columns(3)
        d_range = c1.date_input("조회 기간 설정", value=(date.today()-timedelta(30), date.today()))
        v = c2.selectbox("거래처 필터", ["전체"] + df['거래처'].dropna().unique().tolist())
        i = c3.selectbox("품목 필터", ["전체"] + df['품목명'].dropna().unique().tolist())
        if v != "전체": df = df[df['거래처'] == v]
        if i != "전체": df = df[df['품목명'] == i]
        if len(d_range)==2: df = df[(df['매입일자'].dt.date >= d_range[0]) & (df['매입일자'].dt.date <= d_range[1])]
        df_sorted = df.sort_values('매입일자', ascending=False)
        st.markdown(f"**총 조회 건수:** {len(df_sorted)} 건 &nbsp;&nbsp;|&nbsp;&nbsp; **총 합계 금액:** {int(df_sorted['총액'].sum()):,} 원")
        st.dataframe(df_sorted, use_container_width=True)

elif menu == "🖨️ 월마감 정산서 출력":
    st.markdown("## 🖨️ 월마감 정산서 생성 및 인쇄")
    st.divider()
    
    df = load_data("매입자료")
    if not df.empty:
        df['매입일자'] = pd.to_datetime(df['매입일자'], errors='coerce')
        
        c1, c2 = st.columns(2)
        ym = c1.selectbox("마감 월 선택", sorted(df['매입일자'].dt.strftime('%Y-%m').unique().tolist(), reverse=True))
        v = c2.selectbox("정산 거래처 선택", df['거래처'].unique().tolist())
        
        f = df[(df['매입일자'].dt.strftime('%Y-%m') == ym) & (df['거래처'] == v)].sort_values('매입일자')
        if not f.empty:
            f['매입일자'] = f['매입일자'].dt.strftime('%Y-%m-%d')
            
            # [화면용 UI] 스트림릿 데이터프레임 및 파란 박스 출력
            st.dataframe(f[['매입일자', '거래처', '품목명', '수량', '단가', '총액', '비고']], use_container_width=True)
            st.markdown(f"""
            <div style="background-color: #f4f5f7; padding: 20px; border-radius: 5px; text-align: right; border-left: 5px solid #0052CC; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #172b4d;">총 정산 금액: <span style="color: #0052CC;">{int(f['총액'].sum()):,}</span> 원</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # [인쇄용 데이터 가공] HTML 표로 변환
            f_print = f.copy()
            f_print.insert(0, '거래월', ym)
            f_print.rename(columns={'거래처': '거래처명', '매입일자': '거래일', '품목명': '품목', '총액': '합계액'}, inplace=True)
            f_print = f_print[['거래월', '거래처명', '거래일', '품목', '수량', '단가', '합계액']].fillna("")
            
            for col in ['수량', '단가', '합계액']:
                f_print[col] = pd.to_numeric(f_print[col], errors='coerce').fillna(0)
                f_print[col] = f_print[col].apply(lambda x: f"{int(x):,}" if x != 0 else "")
                
            html_table = f_print.to_html(index=False, justify='center')
            total_sum_string = f"<div class='total-sum'>총 정산 합계액: {int(f['총액'].sum()):,} 원</div>"
            
            # 🚨 드디어 핵심! 우리가 만든 파란색 인쇄 버튼을 여기에 띄웁니다!
            create_print_button(table_html=html_table, total_sum_html=total_sum_string)
            
        else:
            st.warning("해당 조건의 정산 내역이 존재하지 않습니다.")