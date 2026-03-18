import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# -----------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------
st.set_page_config(page_title="쇼크트리 훈프로 광고 분석기 체험판(7일)", layout="wide")

# -----------------------------------------------------------
# 설정값
# -----------------------------------------------------------
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
TRIAL_DAYS = 7
ADMIN_PASSWORD = "3805"  # 관리자 패널 비밀번호 (별도 관리)

# -----------------------------------------------------------
# 사용자 데이터 관리 함수
# -----------------------------------------------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def register_user(user_id, name, full_name):
    """신규 가입 신청. 반환: (성공여부, 메시지)"""
    uid = user_id.strip().lower()
    if not uid:
        return False, "아이디를 입력해주세요."
    if not name.strip():
        return False, "이름을 입력해주세요."
    if not full_name.strip():
        return False, "성함을 입력해주세요."
    users = load_users()
    if uid in users:
        status = users[uid]["status"]
        if status == "pending":
            return False, "이미 가입 신청이 접수되어 승인 대기 중입니다."
        elif status == "approved":
            return False, "이미 등록된 아이디입니다. 로그인 탭을 이용해주세요."
        elif status == "rejected":
            return False, "관리자에 의해 거절된 아이디입니다. 관리자에게 문의해주세요."
    users[uid] = {
        "status": "pending",
        "name": name.strip(),
        "full_name": full_name.strip(),
        "registered_at": datetime.now().date().isoformat(),
        "trial_start": None,
        "approved_at": None
    }
    save_users(users)
    return True, "가입 신청이 완료되었습니다. 관리자 승인 후 이용 가능합니다."

def do_login(user_id):
    """로그인 처리. 반환: (성공여부, 메시지, 남은일수)"""
    uid = user_id.strip().lower()
    if not uid:
        return False, "아이디를 입력해주세요.", None

    users = load_users()
    if uid not in users:
        return False, "가입 신청이 필요합니다. '가입 신청' 탭을 이용해주세요.", None

    user = users[uid]
    if user["status"] == "pending":
        return False, "아직 관리자 승인 대기 중입니다. 잠시 후 다시 시도해주세요.", None
    if user["status"] == "rejected":
        return False, "관리자에 의해 거절된 계정입니다. 관리자에게 문의해주세요.", None

    # 승인된 사용자 - 체험 기간 확인
    today = datetime.now().date()
    if user["trial_start"] is None:
        users[uid]["trial_start"] = today.isoformat()
        save_users(users)
        trial_start = today
    else:
        trial_start = datetime.fromisoformat(user["trial_start"]).date()

    days_elapsed = (today - trial_start).days
    if days_elapsed >= TRIAL_DAYS:
        expire_date = trial_start + timedelta(days=TRIAL_DAYS)
        return False, f"TRIAL_EXPIRED|{trial_start.isoformat()}|{expire_date.isoformat()}", None

    days_remaining = TRIAL_DAYS - days_elapsed
    return True, "로그인 성공", days_remaining

# -----------------------------------------------------------
# 세션 상태 초기화
# -----------------------------------------------------------
for key, default in [('authenticated', False), ('current_user', None),
                     ('trial_days_remaining', None), ('admin_mode', False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# -----------------------------------------------------------
# 로그인/가입 화면
# -----------------------------------------------------------
if not st.session_state['authenticated'] and not st.session_state['admin_mode']:
    st.title("🔐 쇼크트리 훈프로 광고 분석기 체험판(7일)")

    tab_register, tab_login, tab_admin = st.tabs(["📝 가입 신청", "🔑 로그인", "🛠️ 관리자"])

    # ── 로그인 탭 ──
    with tab_login:
        st.subheader("로그인")
        login_msg = st.session_state.get("login_msg", "")
        if login_msg.startswith("TRIAL_EXPIRED|"):
            parts = login_msg.split("|")
            st.error("⛔ 무료 체험 기간이 종료되었습니다.")
            st.warning(
                f"체험 시작일: **{parts[1]}**  \n"
                f"체험 종료일: **{parts[2]}** (5일 무료 제공)  \n\n"
                "계속 이용하시려면 관리자에게 문의해주세요."
            )
        elif login_msg:
            st.error(f"❌ {login_msg}")

        with st.form("login_form"):
            uid = st.text_input("아이디", placeholder="가입 시 사용한 아이디")
            if st.form_submit_button("로그인"):
                ok, msg, days = do_login(uid)
                if ok:
                    st.session_state['authenticated'] = True
                    st.session_state['current_user'] = uid.strip().lower()
                    st.session_state['trial_days_remaining'] = days
                    st.session_state.pop("login_msg", None)
                    st.rerun()
                else:
                    st.session_state["login_msg"] = msg
                    st.rerun()
        st.caption("※ 무료 체험은 최초 로그인일로부터 5일간 제공됩니다.")

    # ── 가입 신청 탭 ──
    with tab_register:
        st.subheader("가입 신청")
        st.info("아래 정보를 입력하면 관리자에게 승인 요청이 전달됩니다. 승인 후 로그인이 가능합니다.")
        reg_msg = st.session_state.get("reg_msg", "")
        if reg_msg:
            if st.session_state.get("reg_ok"):
                st.success(f"✅ {reg_msg}")
            else:
                st.error(f"❌ {reg_msg}")

        with st.form("register_form"):
            new_uid = st.text_input("아이디", placeholder="예: hong_gildong")
            new_name = st.text_input("성함", placeholder="예: 홍길동")
            new_fullname = st.text_input("연락처", placeholder="예: 010-1234-5678")
            st.markdown("""
**[개인정보 수집 및 이용 동의]**

- **수집 항목**: 아이디, 성함, 연락처
- **수집 목적**: 서비스 이용 승인 및 회원 관리
- **보유 기간**: 서비스 이용 종료 후 즉시 파기
- 위 개인정보 수집·이용에 동의하지 않으실 경우 서비스 이용이 제한될 수 있습니다.
""")
            agree = st.checkbox("개인정보 수집 및 이용에 동의합니다. (필수)")
            if st.form_submit_button("가입 신청하기"):
                if not agree:
                    st.session_state["reg_msg"] = "개인정보 수집 및 이용에 동의해주세요."
                    st.session_state["reg_ok"] = False
                else:
                    ok, msg = register_user(new_uid, new_name, new_fullname)
                    st.session_state["reg_msg"] = msg
                    st.session_state["reg_ok"] = ok
                st.rerun()

    # ── 관리자 탭 ──
    with tab_admin:
        st.subheader("관리자 로그인")
        with st.form("admin_login_form"):
            admin_pw = st.text_input("관리자 비밀번호", type="password")
            if st.form_submit_button("관리자 접속"):
                if admin_pw == ADMIN_PASSWORD:
                    st.session_state['admin_mode'] = True
                    st.rerun()
                else:
                    st.error("❌ 관리자 비밀번호가 틀렸습니다.")

    st.stop()

# -----------------------------------------------------------
# 관리자 패널
# -----------------------------------------------------------
if st.session_state['admin_mode']:
    st.title("🛠️ 관리자 패널")
    users = load_users()

    if st.button("← 관리자 로그아웃"):
        st.session_state['admin_mode'] = False
        st.rerun()

    st.divider()

    # 대기 중 사용자
    pending = {uid: u for uid, u in users.items() if u["status"] == "pending"}
    st.subheader(f"⏳ 승인 대기 중 ({len(pending)}명)")
    if pending:
        for uid, u in pending.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{uid}** (신청일: {u['registered_at']})")
            if col2.button("✅ 승인", key=f"approve_{uid}"):
                users[uid]["status"] = "approved"
                users[uid]["approved_at"] = datetime.now().date().isoformat()
                save_users(users)
                st.rerun()
            if col3.button("❌ 거절", key=f"reject_{uid}"):
                users[uid]["status"] = "rejected"
                save_users(users)
                st.rerun()
    else:
        st.write("대기 중인 신청이 없습니다.")

    st.divider()

    # 승인된 사용자 목록
    approved = {uid: u for uid, u in users.items() if u["status"] == "approved"}
    st.subheader(f"✅ 승인된 사용자 ({len(approved)}명)")
    if approved:
        rows = []
        today = datetime.now().date()
        for uid, u in approved.items():
            trial_start = u.get("trial_start")
            if trial_start:
                start = datetime.fromisoformat(trial_start).date()
                elapsed = (today - start).days
                remaining = max(0, TRIAL_DAYS - elapsed)
                status_str = f"잔여 {remaining}일" if remaining > 0 else "만료"
            else:
                status_str = "미시작"
            rows.append({"아이디": uid, "승인일": u.get("approved_at", "-"),
                         "체험시작": trial_start or "미시작", "체험상태": status_str})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.divider()
        st.subheader("🔄 체험 기간 초기화")
        reset_uid = st.selectbox("초기화할 사용자 선택", list(approved.keys()))
        if st.button("체험 기간 초기화 (5일 재시작)"):
            users[reset_uid]["trial_start"] = None
            save_users(users)
            st.success(f"✅ {reset_uid}의 체험 기간이 초기화되었습니다.")
            st.rerun()
    else:
        st.write("승인된 사용자가 없습니다.")

    st.stop()

# -----------------------------------------------------------
# 2. 쿠팡 광고 성과 분석기 (메인 기능)
# -----------------------------------------------------------
def run_analyzer():
    st.title("📊 쇼크트리 훈프로 쿠팡 광고 성과 분석기")
    st.markdown("쿠팡 보고서(CSV 또는 XLSX)를 업로드하면 훈프로의 정밀 운영 전략이 자동으로 생성됩니다.")

    # --- 사이드바: 수익성 계산 설정 ---
    st.sidebar.header("💰 마진 계산 설정")
    unit_price = st.sidebar.number_input("상품 판매가 (원)", min_value=0, value=0, step=100)
    unit_cost = st.sidebar.number_input("최종원가(매입가 등) (원)", min_value=0, value=0, step=100)

    delivery_fee = st.sidebar.number_input("로켓그로스 입출고비 (원)", min_value=0, value=3650, step=10)
    coupang_fee_rate = st.sidebar.number_input("쿠팡 수수료(vat포함) (%)", min_value=0.0, max_value=100.0, value=11.55, step=0.1)

    total_fee_amount = unit_price * (coupang_fee_rate / 100)
    net_unit_margin = unit_price - unit_cost - delivery_fee - total_fee_amount

    st.sidebar.divider()
    st.sidebar.write(f"**📦 입출고비 합계:** {delivery_fee:,.0f}원")
    st.sidebar.write(f"**📊 예상 수수료 ({coupang_fee_rate}%):** {total_fee_amount:,.0f}원")
    st.sidebar.write(f"**💡 개당 예상 마진:** :green[{net_unit_margin:,.0f}원]")

    if unit_price > 0:
        margin_rate = (net_unit_margin / unit_price) * 100
        st.sidebar.write(f"**📈 예상 마진율:** {margin_rate:.1f}%")

    st.sidebar.divider()
    user_name = st.session_state.get("current_user", "")
    days_left = st.session_state.get("trial_days_remaining")
    if user_name:
        st.sidebar.caption(f"👤 사용자: {user_name}")
    if days_left is not None:
        if days_left <= 1:
            st.sidebar.warning(f"⚠️ 무료 체험 D-{days_left} (오늘 포함)")
        else:
            st.sidebar.info(f"🗓️ 무료 체험 잔여: {days_left}일")

    if st.sidebar.button("로그아웃"):
        st.session_state['authenticated'] = False
        st.session_state['current_user'] = None
        st.session_state['trial_days_remaining'] = None
        st.rerun()

    uploaded_file = st.file_uploader("보고서 파일을 선택하세요 (CSV 또는 XLSX)", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                try: df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                except: df = pd.read_csv(uploaded_file, encoding='cp949')
            else:
                df = pd.read_excel(uploaded_file, engine='openpyxl')

            df.columns = [str(c).strip() for c in df.columns]
            qty_targets = ['총 판매수량(14일)', '총 판매수량(1일)', '총 판매수량', '전환 판매수량', '판매수량']
            col_qty = next((c for c in qty_targets if c in df.columns), None)

            if '광고 노출 지면' in df.columns and col_qty:
                for col in ['노출수', '클릭수', '광고비', col_qty]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').replace('-', '0'), errors='coerce').fillna(0)

                summary = df.groupby('광고 노출 지면').agg({'노출수': 'sum', '클릭수': 'sum', '광고비': 'sum', col_qty: 'sum'}).reset_index()
                summary.columns = ['지면', '노출수', '클릭수', '광고비', '판매수량']

                summary['실제매출액'] = summary['판매수량'] * unit_price
                summary['실제ROAS'] = (summary['실제매출액'] / summary['광고비']).fillna(0)
                summary['클릭률(CTR)'] = (summary['클릭수'] / summary['노출수']).fillna(0)
                summary['구매전환율(CVR)'] = (summary['판매수량'] / summary['클릭수']).fillna(0)
                summary['CPC'] = (summary['광고비'] / summary['클릭수']).fillna(0).astype(int)
                summary['실질순이익'] = (summary['판매수량'] * net_unit_margin) - summary['광고비']

                tot = summary.sum(numeric_only=True)
                total_real_revenue = tot['판매수량'] * unit_price
                total_real_roas = total_real_revenue / tot['광고비'] if tot['광고비'] > 0 else 0
                total_profit = (tot['판매수량'] * net_unit_margin) - tot['광고비']

                total_data = {
                    '클릭률(CTR)': tot['클릭수'] / tot['노출수'] if tot['노출수'] > 0 else 0,
                    '구매전환율(CVR)': tot['판매수량'] / tot['클릭수'] if tot['클릭수'] > 0 else 0
                }

                st.subheader("📌 핵심 성과 지표")
                m1, m2, m3, m4 = st.columns(4)
                p_color = "#FF4B4B" if total_profit >= 0 else "#1C83E1"

                cols = [m1, m2, m3, m4]
                vals = [("최종 실질 순이익", f"{total_profit:,.0f}원", p_color),
                        ("총 광고비", f"{tot['광고비']:,.0f}원", "#31333F"),
                        ("실제 ROAS", f"{total_real_roas:.2%}", "#31333F"),
                        ("총 판매수량", f"{tot['판매수량']:,.0f}개", "#31333F")]

                for c, (l, v, clr) in zip(cols, vals):
                    c.markdown(f"<div style='background-color:#f0f2f6;padding:15px;border-radius:10px;text-align:center;'> <p style='margin:0;font-size:14px;'>{l}</p><h2 style='margin:0;color:{clr};'>{v}</h2></div>", unsafe_allow_html=True)

                def color_p(val): return f'color: {"red" if val >= 0 else "blue"}; font-weight: bold;'
                st.write(""); st.subheader("📍 지면별 상세 분석")
                st.dataframe(summary.style.format({'노출수': '{:,.0f}', '클릭수': '{:,.0f}', '광고비': '{:,.0f}원', '판매수량': '{:,.0f}', '실제매출액': '{:,.0f}원', 'CPC': '{:,.0f}원', '클릭률(CTR)': '{:.2%}', '구매전환율(CVR)': '{:.2%}', '실제ROAS': '{:.2%}', '실질순이익': '{:,.0f}원'}).applymap(color_p, subset=['실질순이익']), use_container_width=True)

                if '광고집행 상품명' in df.columns:
                    st.divider(); st.subheader("🛍️ 옵션별 성과 분석")
                    df['광고집행 상품명'] = df['광고집행 상품명'].fillna('미확인')
                    prod_agg = df.groupby('광고집행 상품명').agg({'광고비': 'sum', col_qty: 'sum', '노출수': 'sum', '클릭수': 'sum'}).reset_index()
                    prod_agg.columns = ['상품명', '광고비', '판매수량', '노출수', '클릭수']
                    prod_agg['실질순이익'] = (prod_agg['판매수량'] * net_unit_margin) - prod_agg['광고비']

                    st.markdown("##### 🏆 효자 옵션 (판매순)")
                    st.dataframe(prod_agg[prod_agg['판매수량']>0].sort_values('판매수량', ascending=False).style.format({'광고비': '{:,.0f}원', '판매수량': '{:,.0f}개', '실질순이익': '{:,.0f}원'}), use_container_width=True)

                    st.markdown("##### 💸 돈만 쓰는 옵션 (판매0)")
                    st.dataframe(prod_agg[(prod_agg['판매수량']==0) & (prod_agg['광고비']>0)].sort_values('광고비', ascending=False), use_container_width=True)

                if '키워드' in df.columns:
                    st.divider(); st.subheader("✂️ 제외 키워드 제안")
                    kw_df = df.groupby('키워드').agg({'광고비': 'sum', col_qty: 'sum'}).reset_index()
                    bad_kws = kw_df[(kw_df[col_qty]==0) & (kw_df['광고비']>0)].sort_values('광고비', ascending=False)
                    st.text_area("복사해서 제외 등록하세요:", ", ".join(bad_kws['키워드'].astype(str).tolist()))

                st.divider()
                st.subheader("💡 훈프로의 정밀 운영 제안")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.info("🖼️ **클릭률(CTR) 분석 (썸네일)**")
                    ctr_val = total_data['클릭률(CTR)']
                    st.write(f"- **현재 CTR: {ctr_val:.2%}**")
                    if ctr_val < 0.01:
                        st.write("- **상태**: 고객의 눈길을 전혀 끌지 못하고 있습니다.")
                        st.write("- **액션**: 썸네일 배경 제거, 텍스트 강조, 혹은 주력 이미지 교체가 시급합니다.")
                    else:
                        st.write("- **상태**: 시각적 매력이 충분합니다. 클릭률을 유지하며 공격적인 노출을 시도하세요.")

                with col2:
                    st.warning("🛒 **구매전환율(CVR) 분석 (상세페이지)**")
                    cvr_val = total_data['구매전환율(CVR)']
                    st.write(f"- **현재 CVR: {cvr_val:.2%}**")
                    if cvr_val < 0.05:
                        st.write("- **상태**: 유입은 되나 설득력이 부족해 구매로 이어지지 않습니다.")
                        st.write("- **액션**: 상단에 '무료배송', '이벤트' 등 혜택을 강조하고 구매평 관리에 집중하세요.")
                    else:
                        st.write("- **상태**: 상세페이지 전환 능력이 탁월합니다. 유입 단가(CPC) 관리에 힘쓰세요.")

                with col3:
                    st.error("💰 **목표수익률 최적화 가이드**")
                    st.write(f"- **현재 실제 ROAS: {total_real_roas:.2%}**")

                    if total_real_roas < 2.0:
                        st.write("🔴 **[200% 미만] 절대 손실 구간**")
                        st.write("- **액션**: 광고를 새로만드시거나 대대적인 수정이 시급합니다. 목표수익률을 최소 200%p 이상 상향하세요.")
                    elif 2.0 <= total_real_roas < 3.0:
                        st.write("🟠 **[200%~300%] 적자 지속 구간**")
                        st.write("- **액션**: 역마진이 심각합니다. 목표수익률 상향과 고비용 키워드 차단이 필요합니다.")
                    elif 3.0 <= total_real_roas < 4.0:
                        st.write("🟡 **[300%~400%] 손익분기점 안착 구간**")
                        st.write("- **액션**: 수익이 나기 시작합니다. 효율 낮은 키워드를 솎아내며 목표수익률을 50%p 상향하세요.")
                    elif 4.0 <= total_real_roas < 5.0:
                        st.write("🟢 **[400%~500%] 안정적 수익 구간**")
                        st.write("- **전략**: 황금 밸런스입니다. 현재를 유지하며 매출 확대를 위해 목표수익률을 미세 조정하세요.")
                    elif 5.0 <= total_real_roas < 6.0:
                        st.write("🔵 **[500%~600%] 시장 점유 확장 단계**")
                        st.write("- **전략**: 수익이 넉넉합니다. 목표수익률을 하향 조정한 후 노출량을 극대화하세요.")
                    else:
                        st.write("🚀 **[600% 이상] 시장 지배 구간**")
                        st.write("- **전략**: 과감한 하향 조정을 통해 매출 규모 자체를 키우세요.")

        except Exception as e:
            st.error(f"데이터 처리 중 오류 발생: {e}")
            if "openpyxl" in str(e):
                st.error("💡 해결방법: 터미널(또는 CMD)에 'pip install openpyxl'을 입력하여 설치해 주세요.")

# -----------------------------------------------------------
# 3. 메인 실행
# -----------------------------------------------------------
run_analyzer()

# 푸터
st.divider()
st.markdown("<div style='text-align: center;'><a href='https://hoonpro.liveklass.com/' target='_blank'>🏠 쇼크트리 훈프로 홈페이지 바로가기</a></div>", unsafe_allow_html=True)
