"""Chạy trọn bộ golden set (eval/golden_set.md) — chấm tự động bằng assertion.

Cách chạy (từ root repo):
    python3 eval/run_eval.py            # case rule-based + UI (offline, không tốn quota)
    python3 eval/run_eval.py --live     # thêm case AI thật (GS11/12/14/16/18 — cần GROQ_API_KEY)

Kết quả in ra màn hình + ghi vào eval/results-<ngày>-luot<N>.md (trọn bộ, kể cả fail).
Case AI live in kèm NGUYÊN VĂN output để 2 người chấm tay độc lập soát lại (guide §2.6).
"""
import re
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "codebase"))

from data_prep import load_chatlog, build_turns, group_by_day          # noqa: E402
from signals import compute_conversation_signals, classify_input_type, build_day_cases  # noqa: E402
from transcript_index import load_transcript_paragraphs, search        # noqa: E402
from upload_index import build_upload_index                            # noqa: E402

CHATLOG = ROOT / "data" / "vlearn-pack" / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
TRANSCRIPT_DIR = ROOT / "data" / "vlearn-pack" / "transcript"

REFUSAL_RE = re.compile(r"(không tìm thấy|chưa tìm thấy|không có trong|không đủ căn cứ|ngoài phạm vi|không nằm trong)", re.I)
CLARIFY_RE = re.compile(r"(trang nào|khái niệm nào|cụ thể|rõ hơn|phần nào|bạn (đang|muốn) hỏi|chủ đề nào)", re.I)

results = []   # (id, layer_or_group, passed, note, raw_output_or_None)


def record(case_id, group, passed, note, raw=None):
    results.append((case_id, group, passed, note, raw))
    icon = "⏭️ SKIP" if passed is None else ("✅ PASS" if passed else "❌ FAIL")
    print(f"  {icon}  {case_id} — {note}")


def sig_of(by_day, date, conv_id):
    return compute_conversation_signals(by_day[date][conv_id])


def main():
    live = "--live" in sys.argv

    print("Nạp data pack...")
    rows = load_chatlog(str(CHATLOG))
    turns = build_turns(rows)
    by_day = group_by_day(turns)
    index = load_transcript_paragraphs(str(TRANSCRIPT_DIR))

    # ---------- Nhóm A — case thường (offline) ----------
    print("\n[Nhóm A — case thường, rule-based]")
    expect_primary = [
        ("GS01", "2026-07-23", "C0023", "tutor_limitation"),
        ("GS02", "2026-07-23", "C0177", "tutor_limitation"),
        ("GS03", "2026-07-22", "C0092", "learning_difficulty"),
        ("GS04", "2026-07-23", "C0411", "learning_difficulty"),
        ("GS05", "2026-07-22", "C0239", "intent_drift"),
        ("GS06", "2026-07-23", "C0544", "intent_drift"),
    ]
    for cid, date, conv, want in expect_primary:
        got = sig_of(by_day, date, conv)["primary_category"]
        record(cid, "thường", got == want, f"primary={got!r}, kỳ vọng {want!r}")

    for cid, date, conv in [("GS07", "2026-07-22", "C0295"), ("GS08", "2026-07-23", "C0466")]:
        s = sig_of(by_day, date, conv)
        record(cid, "thường", not s["friction_flag"], f"friction_flag={s['friction_flag']}, kỳ vọng False")

    s = sig_of(by_day, "2026-07-23", "C0495")
    record("GS09", "thường", s["primary_category"] == "learning_difficulty" and s["confusion_count"] >= 1,
           f"primary={s['primary_category']!r}, confusion_count={s['confusion_count']}")

    s = sig_of(by_day, "2026-07-23", "C0076")
    record("GS10", "thường", s["primary_category"] == "tutor_limitation" and s["rating_down_quit"],
           f"primary={s['primary_category']!r}, rating_down_quit={s['rating_down_quit']}")

    # ---------- Nhóm B — chỗ khó ----------
    print("\n[Nhóm B — chỗ khó]")

    # GS13 (②): ngày < 20 hội thoại -> UI hiện cảnh báo mẫu nhỏ (trang Live Dashboard)
    try:
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "codebase" / "app_pages" / "live_dashboard.py"), default_timeout=120)
        at.run()
        week_opt = [o for o in at.selectbox(key="ld_week").options if "Tuần 30" in o][0]
        at.selectbox(key="ld_week").set_value(week_opt)
        at.run()
        at.selectbox(key="ld_day").set_value("2026-07-25")
        at.run()
        warnings = " ".join(w.value for w in at.warning)
        ok = "mẫu quá nhỏ" in warnings or "tin cậy thấp" in warnings
        record("GS13", "②", ok, f"cảnh báo mẫu nhỏ {'có' if ok else 'KHÔNG'} xuất hiện (ngày 7 hội thoại)")
    except Exception as e:
        record("GS13", "②", False, f"lỗi chạy AppTest: {e}")

    # GS15 (③): meta question -> intent_drift
    fake_turn = {"turn_id": "SYN15", "page": None, "question": "bạn là model ai nào vậy",
                 "tutor_content": "Mình là trợ lý học tập.", "move_used": None, "citations": [], "rating": None}
    s = compute_conversation_signals([fake_turn])
    record("GS15", "③", s["primary_category"] == "intent_drift", f"primary={s['primary_category']!r}")

    # GS17 (④): đa nhãn -> primary phải là tutor_limitation
    s = sig_of(by_day, "2026-07-23", "C0284")
    record("GS17", "④", s["primary_category"] == "tutor_limitation" and "learning_difficulty" in s["categories"],
           f"primary={s['primary_category']!r}, categories={s['categories']}")

    # ---------- Nhóm C — case hiếm ----------
    print("\n[Nhóm C — case hiếm]")
    s = sig_of(by_day, "2026-07-23", "C0098")
    record("GS19", "hiếm", s["repeated_page_max"] == 3 and s["repeated_page_flag"],
           f"repeated_page_max={s['repeated_page_max']}, flag={s['repeated_page_flag']} (ngưỡng biên =3)")

    s = sig_of(by_day, "2026-07-23", "C0320")
    record("GS20", "hiếm", set(s["categories"]) == {"tutor_limitation", "learning_difficulty", "intent_drift"}
           and s["primary_category"] == "tutor_limitation",
           f"categories={s['categories']}, primary={s['primary_category']!r}")

    fake_turn = {"turn_id": "SYN21", "page": None, "question": "?", "tutor_content": "Bạn muốn hỏi gì nhỉ?",
                 "move_used": None, "citations": [], "rating": None}
    try:
        s = compute_conversation_signals([fake_turn])
        record("GS21", "hiếm", s["primary_category"] == "intent_drift",
               f"input rỗng/cụt -> primary={s['primary_category']!r}, không crash")
    except Exception as e:
        record("GS21", "hiếm", False, f"crash: {e}")

    txt = "Định nghĩa context window trong mô hình ngôn ngữ.\n\nMemory là cơ chế lưu thông tin giữa các phiên."
    idx = build_upload_index("test.txt", txt.encode("utf-8"))
    hits = search("context window là gì trong mô hình", idx, k=1)
    record("GS22", "hiếm", len(idx) == 2 and hits and hits[0]["code"] == "DOAN-01",
           f"index {len(idx)} đoạn, top hit={hits[0]['code'] if hits else 'không có'}")

    # ---------- Case AI live ----------
    if live:
        print("\n[Case AI thật — GS11/12/14/16/18]")
        from agent_tutor import run_turn
        from classify_friction import classify_day

        def ask(question):
            answer, tool_log, _ = run_turn(index, [], question)
            return answer, tool_log

        try:
            ans, _ = ask("Giải thích cơ chế đồng thuận Proof of Stake trong blockchain")
            ok = bool(REFUSAL_RE.search(ans)) and "proof of stake là" not in ans.lower()
            record("GS11", "①", ok, "từ chối trung thực khi không có trong tài liệu" if ok else "KHÔNG từ chối rõ / có dấu hiệu tự giải thích", raw=ans)
        except Exception as e:
            record("GS11", "①", False, f"lỗi gọi AI: {e}")

        try:
            ans, _ = ask("giải thích đi")
            ok = bool(CLARIFY_RE.search(ans)) or bool(REFUSAL_RE.search(ans))
            record("GS14", "②", ok, "hỏi lại làm rõ / nêu thiếu ngữ cảnh" if ok else "đoán bừa không hỏi lại", raw=ans)
        except Exception as e:
            record("GS14", "②", False, f"lỗi gọi AI: {e}")

        try:
            ans, tlog = ask("thời tiết hôm nay thế nào?")
            ok = bool(REFUSAL_RE.search(ans)) and not re.search(r"\d+\s*độ|nắng|mưa to", ans.lower())
            record("GS16", "③", ok, f"từ chối ngoài phạm vi (tool gọi {len(tlog)} lần)" if ok else "trả lời hộ nội dung ngoài phạm vi", raw=ans)
        except Exception as e:
            record("GS16", "③", False, f"lỗi gọi AI: {e}")

        try:
            date = "2026-07-22"
            day_report = build_day_cases(by_day[date])
            payload, result = classify_day(date, day_report, index, dry_run=False)
            concepts = result["concepts"]
            n_clusters = len(payload["clusters"])
            no_fallback = all("[AI không trả về" not in c["cause_rationale"] for c in concepts)
            counts_kept = all(
                c["case_count"] == pc["case_count"] and c["percent_of_day"] == pc["percent_of_day"]
                for c, pc in zip(concepts, payload["clusters"])
            )
            record("GS12", "①", len(concepts) == n_clusters and no_fallback and counts_kept,
                   f"{len(concepts)}/{n_clusters} cụm được đặt tên, số liệu giữ nguyên={counts_kept}",
                   raw="\n".join(f"- [{c['category']}/{c['root_cause']}] {c['concept']}: {c['suggested_action']}" for c in concepts))

            def action_ok(c):
                a = (c.get("suggested_action") or "").lower()
                if c["category"] == "intent_drift":
                    return "giảng lại" not in a
                if c["root_cause"] == "retrieval_bug":
                    return any(k in a for k in ("kỹ thuật", "tìm kiếm", "hệ thống", "retrieval"))
                if c["root_cause"] == "content_gap":
                    return any(k in a for k in ("giảng", "tài liệu", "ta ", "bổ sung", "giải thích"))
                return True
            bad = [c["concept"] for c in concepts if not action_ok(c)]
            record("GS18", "④", not bad, "action khớp root_cause mọi cụm" if not bad else f"action lệch root_cause: {bad}",
                   raw="\n".join(f"- {c['concept']} ({c['root_cause']}): {c['suggested_action']}" for c in concepts))
        except Exception as e:
            record("GS12", "①", False, f"lỗi gọi AI: {e}")
            record("GS18", "④", False, f"lỗi gọi AI: {e}")
    else:
        for cid, grp in [("GS11", "①"), ("GS12", "①"), ("GS14", "②"), ("GS16", "③"), ("GS18", "④")]:
            record(cid, grp, None, "SKIP — chạy lại với --live để chấm case AI")

    # ---------- Tổng kết + ghi file ----------
    graded = [r for r in results if r[2] is not None]
    passed = [r for r in graded if r[2]]
    layer1 = [r for r in graded if r[1] == "①"]
    layer1_ok = all(r[2] for r in layer1) if layer1 else None
    pct = len(passed) / len(graded) * 100 if graded else 0

    print(f"\n===== KẾT QUẢ: {len(passed)}/{len(graded)} pass = {pct:.0f}%"
          f" | lớp ① sạch: {layer1_ok} | quality bar: ≥80% VÀ 0 fail lớp ① =====")
    print("=> " + ("ĐẠT" if pct >= 80 and layer1_ok else "CHƯA ĐẠT (hoặc chưa chạy đủ case live)"))

    today = datetime.date.today().isoformat()
    out_dir = Path(__file__).resolve().parent
    n = len(list(out_dir.glob(f"results-{today}-luot*.md"))) + 1
    out = out_dir / f"results-{today}-luot{n}.md"
    lines = [
        f"# Kết quả chạy golden set — {today} · lượt {n}",
        "",
        f"Chế độ: {'FULL (kèm case AI live)' if live else 'OFFLINE (case AI bị skip)'}",
        f"**{len(passed)}/{len(graded)} pass = {pct:.0f}%** · lớp ① sạch: {layer1_ok} · "
        f"quality bar (≥80% + 0 fail lớp ①): **{'ĐẠT' if pct >= 80 and layer1_ok else 'CHƯA ĐẠT'}**",
        "",
        "| Case | Nhóm/Lớp | Kết quả | Ghi chú |",
        "|---|---|---|---|",
    ]
    for cid, grp, ok, note, _ in results:
        status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        lines.append(f"| {cid} | {grp} | {status} | {note} |")
    raws = [(cid, raw) for cid, _, _, _, raw in results if raw]
    if raws:
        lines += ["", "## Nguyên văn output case AI (để 2 người chấm tay độc lập soát lại)", ""]
        for cid, raw in raws:
            lines += [f"### {cid}", "```", str(raw), "```", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {out}")


if __name__ == "__main__":
    main()
