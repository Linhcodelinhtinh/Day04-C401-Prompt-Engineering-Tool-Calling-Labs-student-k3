# Báo cáo Lab Day 04 v2 — Research Agent

## Thông tin nhóm

- Nhóm: _Cần bổ sung_
- Thành viên: _Cần bổ sung_
- Provider/model: OpenRouter
---

# Phần A — Giới thiệu agent

## A1. Agent làm được gì?

Research Agent có thể tìm bài đăng gần đây của một tài khoản cụ thể, tìm kiếm bài đăng mạng xã hội hoặc thông tin web/tin tức, đọc nội dung từ URL do người dùng cung cấp và tổng hợp kết quả thành Markdown digest. Agent cũng hỏi lại khi thiếu thông tin thiết yếu và bắt buộc xác nhận rõ ràng trước khi gửi nội dung lên Telegram.

**URL demo:** _Streamlit chạy local: `http://localhost:8501`

## A2. Các tool hiện có

| Tool | Chức năng | Nhóm tự thêm? |
|---|---|---|
| `clarify` | Hỏi thông tin còn thiếu hoặc yêu cầu xác nhận yes/no | Không |
| `timeline` | Lấy bài đăng gần đây của một tài khoản cụ thể | Không |
| `social_search` | Tìm bài đăng mạng xã hội theo từ khóa/chủ đề | Không |
| `lookup` | Tìm kiếm web hoặc tin tức mới | Không |
| `fetch` | Đọc nội dung của URL cụ thể do người dùng cung cấp | Không |
| `format` | Định dạng các item đã thu thập thành Markdown digest | Không |
| `send` | Gửi text lên Telegram sau khi người dùng xác nhận rõ ràng | Không |
| `policy` | Tìm trong tài liệu policy nội bộ | Không |
| `papers` | Tìm paper trên arXiv | Không |
| `paper_text` | Trích xuất text từ paper arXiv | Không |

## A3. Câu hỏi mẫu để thử agent

1. “Tweet mới nhất của Sam Altman là gì?”
2. “Tìm tin AI hôm nay và mọi người đang bàn gì trên X.”
3. “Tóm tắt bài này: https://example.com/article”
4. “Tìm các paper mới về agentic RAG.”
5. “Gửi bản tin này lên Telegram.”

## A4. Kịch bản demo đã chuẩn bị

| Kịch bản | Tool trace mong đợi | Câu chuyện cải thiện version | Bằng chứng dự phòng |
|---|---|---|---|
| Bài đăng gần đây của một tài khoản | `timeline(screenname=...)` | Prompt v1 làm rõ ranh giới giữa yêu cầu theo tài khoản và tìm theo chủ đề. | `runs/v1_B_base_openrouter_20260729T160017587828.json` |
| Tin AI và thảo luận trên mạng xã hội | `lookup(topic=news)` + `social_search` trong cùng turn | v1 cho phép gọi nhiều source tool khi yêu cầu thực sự cần cả hai nguồn. | Base run v0/v1 |
| Người dùng đã cho URL | Chỉ `fetch(url=...)` | v1 nêu rõ không gọi `lookup` khi đã có URL cụ thể. | Base run v0/v1 |
| Yêu cầu gửi Telegram | `clarify(response_type=yes_no)` trước `send` | Ranh giới xác nhận được quy định trong prompt và tool declaration. | Base run v0/v1 |

---

# Phần B — Chi tiết / bằng chứng

## B1. Bằng chứng theo version

Điều kiện metric hợp lệ: `provider_error_cases = 0` và `measured_cases = total_cases`. Run OpenRouter v0–v4 đáp ứng điều kiện này. Run Gemini v0 không đáp ứng (`12` provider-error case và chỉ đo được `8/20` case), vì vậy không được dùng để so sánh.

| Version | Artifact thay đổi | Lý do thay đổi | Giả thuyết | Metric | Trước | Sau | Run file |
|---|---|---|---|---|---:|---:|---|
| v0 | `system_prompt.md` | Baseline với prompt đầy đủ: routing, never-guess, confirm-before-send và multi-turn carryover. | Prompt đầy đủ rule sẽ xử lý phần lớn lỗi routing/boundary của starter prompt mơ hồ. | Case accuracy | — | 70.0% | `runs/v0_B_base_openrouter_20260729T152920607661.json` |
| v1 | `system_prompt_v1.md` | Ablation: chỉ liệt kê tool + mô tả một dòng; bỏ routing/clarify/confirm rule để đo mức `tools.yaml` tự gánh được. | Routing vẫn cao nhờ `tools.yaml`, nhưng clarify `response_type` và chuyển nguồn giữa các turn sẽ fail. | Case accuracy | 70.0% | 70.0% | `runs/v1_B_base_openrouter_20260729T160017587828.json` |
| v2 | `system_prompt_v2.md` | Thêm block Routing: timeline/social search, `lookup` topic/timeframe, URL và multi-tool. | Sửa R03/R13 mà chưa thay đổi phần clarify. | Case accuracy | 70.0% | 80.0% | `runs/v2_B_base_openrouter_20260729T161006997521.json` |
| v3 | `system_prompt_v3.md` | Thêm Never guess required info, Confirm before action và Multi-turn conversations. | Không đoán dữ liệu, confirm `yes_no`, carryover/correction sẽ cải thiện routing và multiturn; `response_type` vẫn có thể cần một vòng riêng. | Case accuracy | 80.0% | 85.0% | `runs/v3_B_base_openrouter_20260729T161321083713.json` |
| v4 | `system_prompt_final_boss.md` | Thêm When not to call a tool và ghi chú dùng `format`, vốn bị bỏ sót ở v1–v3. | Kỳ vọng bản superset tốt nhất; **không xác nhận**: M06 tái phát và R12 dùng `response_type=text` thay vì `yes_no`. | Case accuracy | 85.0% | 80.0% | `runs/v4_B_base_openrouter_20260729T162852343181.json` |

Các `artifact_version`, hash, tác giả `Krazyrv` và mô tả đầy đủ hơn nằm trong `artifacts/version_log.csv`; bảng trên là bản tóm tắt trực tiếp từ log đó.

## B2. Phân tích failure

| Case ID | Version | Lỗi | Tool call thực tế | Cách sửa / thí nghiệm tiếp theo |
|---|---|---|---|---|
| R08_out_of_scope | v0 | Gọi `send` cho câu hỏi toán học | `send(text=...)` | Duy trì/enforce hành vi không gọi tool cho yêu cầu ngoài phạm vi. |
| R10_missing_handle | v0 | Tự đoán handle tài khoản | `timeline(screenname=sama)` | v1 đổi sang `clarify`; cần kiểm tra lại nếu grader chấm chặt câu hỏi/args. |
| R11_missing_url | v0 | Tự tạo URL | `fetch(url=https://example.com/article)` | v1 đổi sang `clarify`; cần kiểm tra mismatch của args. |
| R12_confirm_before_send | v0 | Gửi khi chưa được xác nhận | `send(text=...)` | v1 dùng `clarify`, nhưng câu hỏi cần hỏi xác nhận yes/no trực tiếp. |
| R13_parallel_web_and_tweets | v0/v1 | Đã gọi song song các tool nhưng args chưa khớp hoàn toàn | `lookup` + `social_search` | Làm rõ quy ước `topic`, `timeframe`, `search_type` theo expectation của eval. |
| M02_carryover_timeframe | v1 | Không giữ timeframe từ lượt trước | `social_search(query=robotics, search_type=Latest)` | v3 thêm rule carryover rõ ràng; multiturn accuracy sau đó đạt 100%. |
| M06_switch_tool | v2 | Vẫn giữ `lookup` sau khi user đổi từ tin tức sang social post | `lookup` + `social_search` | Rule “lượt mới nhất được ưu tiên/ghi đè” trong v3 đã loại bỏ tool call thừa. |
| R10/R11/R12 | v3/v4 | Chọn đúng nhóm tool (`clarify`) nhưng grader không chấp nhận chính xác câu hỏi/args | `clarify(question=...)` | Chỉ điều chỉnh expectation nếu schema chấm cho phép; không được tự bịa handle, URL hoặc xác nhận. |
| M06_switch_tool | v4 (run mới nhất) | Lại gọi thêm `lookup` sau khi user đổi sang social post | `lookup` + `social_search` | Regression so với v3; ưu tiên rõ ràng intent ở user turn mới nhất và rerun trước khi chốt. |

Lưu ý review thủ công: một số tool call routing đúng vẫn lỗi khi thực thi do thiếu external credential (ví dụ `RAPIDAPI_KEY`). Routing PASS không chứng minh tool execution thành công.

## B3. Team eval cases

`data/eval_group.json` hiện vẫn là template rỗng (`cases: []`). Nhóm chưa thêm 10 eval case bắt buộc (5 single-turn và 5 multi-turn), nên chưa thể báo cáo kết quả phần này.

## B4. Bằng chứng live chat

Đã có hai transcript OpenRouter, mỗi transcript gồm ba turn:

| Kịch bản/lượt | Version | Tool call | Transcript | Kết quả |
|---|---|---|---|---|
| Tài khoản Elon Musk | v0 | `timeline(screenname=elonmusk)` | `transcripts/v0_openrouter_20260729T161538608611.transcript.json` | Routing đúng; live API trả HTTP 403. |
| Xác nhận trước khi gửi | v0 | `clarify(response_type=yes_no)` → `send(confirmed=true)` | `transcripts/v0_openrouter_20260729T161538608611.transcript.json` | Ranh giới xác nhận hoạt động; Telegram credential chưa được cấu hình nên gửi thất bại an toàn. |
| Tìm paper mới về robot | v0 | `papers` → `format` | `transcripts/v0_openrouter_20260729T161928643105.transcript.json` | Trả về và định dạng năm kết quả arXiv. |
| Bài đăng trên X về robot | v0 | `social_search(query=robot, search_type=Top)` | `transcripts/v0_openrouter_20260729T161928643105.transcript.json` | Routing đúng; live API trả HTTP 403. |
| Tài khoản Elon Musk | v0 | `timeline(screenname=elonmusk)` | `transcripts/v0_openrouter_20260729T161928643105.transcript.json` | Routing đúng; live API trả HTTP 403. |

## B5. Bằng chứng năng lực tool

| Nhóm tool | Evidence file | Điều đã hoạt động | Rủi ro / guardrail |
|---|---|---|---|
| Core tool | `artifacts/tools.yaml`; run JSON v0–v4 | Tool routing trong base eval đạt 100% ở v3 (v4 mới nhất giảm còn 95%). | API ngoài cần key hợp lệ; phải review thủ công tool-result lỗi. |
| Built-in tùy chọn | `artifacts/tools.yaml`; transcript `...161928643105` | `papers` và `format` đã trả về digest arXiv gồm năm item. | `send` cần xác nhận rõ ràng; tool gọi API có thể lỗi do thiếu credential hoặc HTTP 403. |
| Tool do nhóm tự thêm | Chưa có | Chưa có bằng chứng về tool mới do nhóm tự viết. | Cần có `TOOL.md`, implementation, registry, declaration và smoke test. |

## B6. Reflection / việc cần làm tiếp

- Các cải thiện prompt đã nâng tool routing accuracy từ 75.0% (v0) lên 100.0% (v3), và case accuracy từ 70.0% lên 85.0%.
- Run v4 mới nhất bị regression xuống 80.0% case accuracy và 95.0% routing accuracy, nên v3 là artifact tốt nhất hiện có để demo/nộp bài. Version tiếp theo nên tập trung vào mismatch `clarify.question` ở R10–R12 và rule ưu tiên intent ở turn mới nhất.
- Tool declaration cần nêu rõ default và quy ước argument, đặc biệt là `lookup.topic`, `lookup.timeframe` và `social_search.search_type`.
- Tool-result lỗi cần review thủ công vì routing score không xác thực việc API bên ngoài thực thi thành công.
- Cần thêm đúng 10 group eval case và chạy group evaluation. Live evidence đã có, nhưng nên sửa external credential/API access trước khi demo.
