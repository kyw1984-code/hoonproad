import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="관리자 패널 - 훈프로", layout="wide")

# -----------------------------------------------------------
# 설정값 (app.py와 동일하게 유지)
# -----------------------------------------------------------
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "users.json")
TRIAL_DAYS = 7
ADMIN_PASSWORD = "3805"

# -----------------------------------------------------------
# 데이터 관리 함수
# -----------------------------------------------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -----------------------------------------------------------
# 관리자 인증
# -----------------------------------------------------------
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

if not st.session_state['admin_authenticated']:
    st.title("🛠️ 관리자 패널")
    st.info("관리자 전용 페이지입니다.")
    with st.form("admin_login"):
        pw = st.text_input("관리자 비밀번호", type="password")
        if st.form_submit_button("접속"):
            if pw == ADMIN_PASSWORD:
                st.session_state['admin_authenticated'] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# -----------------------------------------------------------
# 관리자 패널 메인
# -----------------------------------------------------------
st.title("🛠️ 관리자 패널")

col_logout, _ = st.columns([1, 5])
if col_logout.button("로그아웃"):
    st.session_state['admin_authenticated'] = False
    st.rerun()

users = load_users()
today = datetime.now().date()

# ── 요약 지표 ──
total = len(users)
pending_count  = sum(1 for u in users.values() if u["status"] == "pending")
approved_count = sum(1 for u in users.values() if u["status"] == "approved")
expired_count  = sum(
    1 for u in users.values()
    if u["status"] == "approved" and u.get("trial_start")
    and (today - datetime.fromisoformat(u["trial_start"]).date()).days >= TRIAL_DAYS
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 신청자", f"{total}명")
m2.metric("승인 대기", f"{pending_count}명")
m3.metric("승인 완료", f"{approved_count}명")
m4.metric("체험 만료", f"{expired_count}명")

st.divider()

# ── 탭 구성 ──
tab1, tab2, tab3 = st.tabs(["⏳ 승인 대기", "✅ 승인된 사용자", "❌ 거절/만료"])

# ── 승인 대기 탭 ──
with tab1:
    pending = {uid: u for uid, u in users.items() if u["status"] == "pending"}
    if not pending:
        st.info("대기 중인 신청이 없습니다.")
    else:
        # 일괄 승인 영역
        selected = []
        for uid, u in pending.items():
            with st.container(border=True):
                c0, c1, c2, c3 = st.columns([0.5, 4, 1, 1])
                checked = c0.checkbox("", key=f"chk_{uid}")
                if checked:
                    selected.append(uid)
                name_str = f"{u.get('name', '-')} / {u.get('full_name', '-')}"
                c1.markdown(f"**{uid}** | 성함: {name_str}  \n신청일: {u['registered_at']}")
                if c2.button("✅ 승인", key=f"approve_{uid}", use_container_width=True):
                    users[uid]["status"] = "approved"
                    users[uid]["approved_at"] = today.isoformat()
                    save_users(users)
                    st.success(f"{uid} 승인 완료")
                    st.rerun()
                if c3.button("❌ 거절", key=f"reject_{uid}", use_container_width=True):
                    users[uid]["status"] = "rejected"
                    save_users(users)
                    st.warning(f"{uid} 거절됨")
                    st.rerun()

        st.divider()
        col_bulk, col_info = st.columns([1, 3])
        if col_bulk.button("✅ 선택 일괄 승인", type="primary", use_container_width=True, disabled=len(selected) == 0):
            for uid in selected:
                users[uid]["status"] = "approved"
                users[uid]["approved_at"] = today.isoformat()
            save_users(users)
            st.success(f"{len(selected)}명 일괄 승인 완료: {', '.join(selected)}")
            st.rerun()
        if selected:
            col_info.info(f"선택된 사용자: {len(selected)}명 ({', '.join(selected)})")
        else:
            col_info.caption("체크박스로 사용자를 선택하면 일괄 승인할 수 있습니다.")

# ── 승인된 사용자 탭 ──
with tab2:
    approved = {uid: u for uid, u in users.items() if u["status"] == "approved"}
    if not approved:
        st.info("승인된 사용자가 없습니다.")
    else:
        rows = []
        for uid, u in approved.items():
            trial_start = u.get("trial_start")
            if trial_start:
                start = datetime.fromisoformat(trial_start).date()
                elapsed = (today - start).days
                remaining = max(0, TRIAL_DAYS - elapsed)
                expire_date = start + timedelta(days=TRIAL_DAYS)
                status_str = f"잔여 {remaining}일" if remaining > 0 else "만료"
            else:
                expire_date = "-"
                status_str = "미시작 (아직 로그인 안 함)"
            rows.append({
                "아이디": uid,
                "성함": u.get("name", "-"),
                "연락처": u.get("full_name", "-"),
                "승인일": u.get("approved_at", "-"),
                "체험 시작일": trial_start or "-",
                "체험 만료일": str(expire_date),
                "체험 상태": status_str
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🔄 체험 기간 초기화 (5일 재시작)")
        active_uids = [uid for uid, u in approved.items() if u.get("trial_start")]
        if active_uids:
            reset_uid = st.selectbox("초기화할 사용자", active_uids)
            if st.button("체험 기간 초기화", type="primary"):
                users[reset_uid]["trial_start"] = None
                save_users(users)
                st.success(f"✅ {reset_uid}의 체험 기간이 초기화되었습니다. 다음 로그인 시 5일이 새로 시작됩니다.")
                st.rerun()
        else:
            st.info("아직 로그인한 사용자가 없습니다.")

        st.divider()
        st.subheader("🚫 사용자 비활성화")
        deact_uid = st.selectbox("비활성화할 사용자", list(approved.keys()), key="deact_select")
        if st.button("비활성화 (거절 처리)", type="secondary"):
            users[deact_uid]["status"] = "rejected"
            save_users(users)
            st.warning(f"{deact_uid} 비활성화 완료")
            st.rerun()

# ── 거절/만료 탭 ──
with tab3:
    rejected = {uid: u for uid, u in users.items() if u["status"] == "rejected"}
    expired  = {
        uid: u for uid, u in users.items()
        if u["status"] == "approved" and u.get("trial_start")
        and (today - datetime.fromisoformat(u["trial_start"]).date()).days >= TRIAL_DAYS
    }

    st.subheader(f"❌ 거절된 사용자 ({len(rejected)}명)")
    if rejected:
        for uid, u in rejected.items():
            c1, c2 = st.columns([5, 1])
            name_str = f"{u.get('name', '-')} / {u.get('full_name', '-')}"
            c1.write(f"**{uid}** | 성함: {name_str} (신청일: {u['registered_at']})")
            if c2.button("복구", key=f"restore_{uid}"):
                users[uid]["status"] = "pending"
                save_users(users)
                st.rerun()
    else:
        st.write("없음")

    st.divider()
    st.subheader(f"⏰ 체험 만료된 사용자 ({len(expired)}명)")
    if expired:
        for uid, u in expired.items():
            start = datetime.fromisoformat(u["trial_start"]).date()
            expire = start + timedelta(days=TRIAL_DAYS)
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{uid}** | 만료일: {expire}")
            if c2.button("기간 초기화", key=f"reset_expired_{uid}"):
                users[uid]["trial_start"] = None
                save_users(users)
                st.success(f"{uid} 체험 기간 초기화 완료")
                st.rerun()
    else:
        st.write("없음")
