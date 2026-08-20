# Peer Review Rubric & Evaluation

Mỗi nhóm review repo/trace của một nhóm khác trong 8 phút theo khung 5 tiêu chí chuẩn:

| Tiêu chí | Câu hỏi đánh giá | Điểm tối đa | Điểm đạt | Nhận xét chi tiết |
|---|---|---:|---:|---|
| **Role clarity** | Mỗi agent có nhiệm vụ rõ, không overlap quá nhiều không? | 2 | **2.0** | Phân chia vai trò rất rõ ràng: Supervisor điều phối theo deterministic state rules; Researcher thuần túy tìm kiếm và trích xuất nguồn từ Tavily; Analyst chuyên thẩm định đối chiếu bằng chứng mâu thuẫn; Writer chỉ tổng hợp câu trả lời cuối kèm trích dẫn số `[1]`, `[2]`. |
| **State design** | Shared state có đủ thông tin để handoff mà không mất context không? | 2 | **2.0** | `ResearchState` (Pydantic model) chứa đầy đủ `request`, `sources` (SourceDocument schema), `research_notes`, `analysis_notes`, `final_answer`, `errors`, `route_history`, và `trace` events. Handoff giữa các node không làm mất thông tin gốc. |
| **Failure guard** | Có max iterations, timeout, retry/fallback, validation không? | 2 | **2.0** | Đã cấu hình `max_iterations = 6`, `timeout_seconds = 60`, validation Pydantic ở đầu vào, try-catch bắt lỗi ngoại lệ tại mọi I/O client (LLMClient, SearchClient) và cơ chế fallback tự động chuyển sang Writer khi có lỗi từng phần. |
| **Benchmark** | Có so sánh single vs multi-agent bằng metric cụ thể không? | 2 | **2.0** | Có benchmark đầy đủ giữa Single-Agent Baseline và Multi-Agent Workflow theo 5 metrics: Latency, Estimated Cost/Tokens, Quality Score (Rubric), Citation Coverage, và Failure Rate. |
| **Trace explanation** | Nhóm giải thích được trace: ai làm gì, tốn bao nhiêu, sai ở đâu không? | 2 | **2.0** | Tích hợp `trace_span` phân cấp chuẩn Langfuse/OpenTelemetry: span gốc `multi-agent-research` lồng các span con `supervisor`, `researcher` (`search.tavily`), `analyst` (`llm.complete`), `writer` (`llm.complete`). Giải thích tường minh latency, token usage, và status từng chặng. |
| **TỔNG ĐIỂM** | | **10** | **10.0 / 10** | **XUẤT SẮC** |

---

## Peer Review Feedback

```text
Reviewee Repo: Multi-Agent Research System (Lab 20)
Reviewer: Peer Review Team 3
Date: 2026-08-20

Strength:
1. Kiến trúc phân lớp cực kỳ chặt chẽ (clean architecture): tách biệt rõ rệt giữa graph orchestration (LangGraph), agent business logic, core schemas, và các service clients (LLM/Search).
2. Hệ thống Observability xuất sắc: `trace_span` được đặt ở cả cấp node và cấp service I/O, có cơ chế graceful fallback tự động khi không có Langfuse credentials giúp ứng dụng không bao giờ bị crash.
3. Handoff ngữ cảnh bảo toàn nguồn gốc (provenance-preserving): Analyst và Writer đều nhận được URL và snippets thực tế, triệt tiêu hallucination và đạt 100% citation coverage.

Risk / failure mode:
1. Multi-hop latency: Đối với các câu hỏi nghiên cứu phức tạp, độ trễ tích lũy qua 4-5 bước gọi LLM và Web Search có thể lên tới 10-15s, không phù hợp cho các interactive query yêu cầu phản hồi tức thì.
2. Web Search API Dependency: Nếu Tavily API trả về kết quả rỗng hoặc vượt quá quota, hệ thống phụ thuộc vào cơ chế fallback của Supervisor.

One concrete improvement:
Triển khai cơ chế Parallel Branching (Song song hóa): Cho phép Researcher chạy nhiều sub-queries tìm kiếm song song hoặc cho phép Analyst vừa phân tích vừa stream draft trước khi Writer hoàn thiện câu trả lời, giúp giảm 30-40% latency tổng thể.

Score: 10.0 / 10 (Xuất sắc)
```
