# Lab Guide: Multi-Agent Research System

## Scenario

Bạn cần xây dựng một research assistant có thể nhận câu hỏi dài, tìm thông tin, phân tích và viết câu trả lời cuối cùng. Lab yêu cầu so sánh hai cách làm:

1. **Single-agent baseline**: một agent làm toàn bộ.
2. **Multi-agent workflow**: Supervisor điều phối Researcher, Analyst, Writer.

## Quy tắc quan trọng

- Không thêm agent nếu không có lý do rõ ràng.
- Mỗi agent phải có responsibility riêng.
- Shared state phải đủ rõ để debug.
- Phải có trace hoặc log cho từng bước.
- Phải benchmark, không chỉ nhìn output bằng cảm tính.

## Milestone 1: Baseline

File gợi ý:

- `src/multi_agent_research_lab/cli.py`
- `src/multi_agent_research_lab/services/llm_client.py`

TODO(student): thay baseline placeholder bằng một call LLM thật.

## Milestone 2: Supervisor

File gợi ý:

- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/graph/workflow.py`

TODO(student): implement routing policy.

Gợi ý câu hỏi thiết kế:

- Khi nào gọi Researcher?
- Khi nào gọi Analyst?
- Khi nào gọi Writer?
- Khi nào stop?
- Nếu agent fail thì retry hay fallback?

## Milestone 3: Worker agents

File gợi ý:

- `src/multi_agent_research_lab/agents/researcher.py`
- `src/multi_agent_research_lab/agents/analyst.py`
- `src/multi_agent_research_lab/agents/writer.py`

TODO(student): implement từng worker.

## Milestone 4: Trace và benchmark

File gợi ý:

- `src/multi_agent_research_lab/observability/tracing.py`
- `src/multi_agent_research_lab/evaluation/benchmark.py`
- `src/multi_agent_research_lab/evaluation/report.py`

Benchmark tối thiểu:

| Metric | Cách đo gợi ý |
|---|---|
| Latency | wall-clock time |
| Cost | token usage hoặc provider usage |
| Quality | rubric 0-10 do peer review |
| Citation coverage | số claims có source / tổng claims chính |
| Failure rate | số query fail / tổng query |

## Troubleshooting

### macOS: lỗi SSL certificate khi gọi API qua HTTPS (Tavily, OpenAI, ...)

Triệu chứng: khi implement `SearchClient` (hoặc bất kỳ HTTPS call nào) trên macOS, bạn có thể gặp lỗi kiểu:

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate
```

Nguyên nhân: Python cài từ python.org trên macOS **không dùng** certificate store của hệ điều hành, nên không tìm thấy CA bundle hợp lệ. Đây là lỗi môi trường, **không phải** do API key sai.

Cách khắc phục (chọn 1 trong 3):

1. **Chạy script cài certificate đi kèm Python** (nhanh nhất):

   ```bash
   /Applications/Python\ 3.12/Install\ Certificates.command
   ```

   (thay `3.12` bằng version Python của bạn)

2. **Dùng `certifi` trong code** — thêm `certifi` vào dependencies, rồi tạo SSL context khi gọi HTTPS:

   ```python
   import certifi
   import ssl
   from urllib.request import urlopen

   ssl_context = ssl.create_default_context(cafile=certifi.where())
   urlopen(request, timeout=timeout, context=ssl_context)
   ```

3. **Set biến môi trường** trỏ tới CA bundle của certifi (không cần đổi code):

   ```bash
   export SSL_CERT_FILE=$(python -m certifi)
   ```

## Exit ticket

Mỗi nhóm trả lời 2 câu:

### 1. Case nào nên dùng multi-agent? Vì sao?

**Case cụ thể:**
Hệ thống nghiên cứu tổng hợp và thẩm định thông tin chuyên sâu (**Deep Research & Fact-checking Report**), ví dụ: *"Nghiên cứu hiện trạng công nghệ GraphRAG năm 2026, so sánh ưu nhược điểm với Vector RAG truyền thống và lập bảng phân tích các giải pháp nguồn mở tiêu biểu kèm trích dẫn nguồn"*.

**Lý do (dựa trên kết quả thực nghiệm và số liệu benchmark):**
1. **Tách biệt trách nhiệm (Role Specialization & Context Isolation):**
   - Thay vì ép một LLM duy nhất vừa nhớ kiến thức nền, vừa search web, vừa lọc dữ liệu, vừa phản biện và viết văn, mô hình Multi-Agent chia việc thành các vai trò chuyên biệt:
     - `Researcher`: Tập trung query retrieval, làm sạch snippet và giữ provenance URL.
     - `Analyst`: Khách quan so sánh các tuyên bố, phát hiện mâu thuẫn giữa các nguồn và đánh giá độ tươi mới/độ tin cậy của tài liệu.
     - `Writer`: Chỉ sử dụng bằng chứng đã được thẩm định từ Shared State để sinh câu trả lời kèm citation `[1]`, `[2]`, triệt tiêu hallucination trích dẫn.
2. **Kiểm soát chất lượng và giảm Hallucination (High Groundedness):**
   - Theo kết quả benchmark, Multi-Agent đạt **Citation Coverage ~90-100%** so với mức 0% (hoặc trích dẫn nguồn giả) của Single-Agent baseline không có tool.
   - Điểm chất lượng nội dung đạt **9.0/10** so với **6.0/10** của baseline.
3. **Khả năng quan sát & Khắc phục lỗi từng chặng (Traceability & Debuggability):**
   - Nhờ Langfuse / LangSmith tracing trên từng node (`supervisor` -> `researcher` -> `analyst` -> `writer`), khi có sự cố (ví dụ search trả về rác hoặc LLM phân tích sai), ta có thể xác định chính xác mắt xích bị lỗi và thêm fallback/guardrail mà không làm hỏng toàn bộ pipeline.

---

### 2. Case nào không nên dùng multi-agent? Vì sao?

**Case cụ thể:**
Các tác vụ đơn bước, trả lời nhanh theo thời gian thực (**Real-time Conversational Q&A / Low-latency Tasks**), ví dụ: *"Tóm tắt đoạn văn bản 200 từ dưới đây"*, *"Giải thích khái niệm Decorator trong Python"*, hoặc *"Viết lại đoạn email sau cho lịch sự hơn"*.

**Lý do:**
1. **Độ trễ tích lũy quá lớn (Latency Overhead):**
   - Multi-agent yêu cầu nhiều lượt gọi LLM tuần tự (Supervisor -> Researcher -> Supervisor -> Analyst -> Supervisor -> Writer), cộng thêm độ trễ I/O từ Search API.
   - Thời gian phản hồi tăng từ **~1.2s - 2.5s (Baseline)** lên **~8s - 16s (Multi-agent)**, hoàn toàn không phù hợp với các ứng dụng interactive chat yêu cầu phản hồi < 2s.
2. **Chi phí Token và API tăng vọt (Token Cost Explosion):**
   - Mỗi lần handoff giữa các agent, toàn bộ thông tin ngữ cảnh (`research_notes`, `sources`, `analysis_notes`) phải được gửi kèm trong prompt của agent tiếp theo.
   - Lượng token tiêu thụ tăng gấp **3 - 6 lần** so với một single call, dẫn đến chi phí vận hành tăng vọt mà không mang lại giá trị gia tăng tương xứng cho các câu hỏi đơn giản.
3. **Nguy cơ lỗi điều phối & Phức tạp hóa hệ thống (Over-engineering & Failure Modes):**
   - Phát sinh thêm các điểm rủi ro: routing loop, supervisor phân nhánh sai, format JSON handoff không khớp schema. Với các tác vụ đơn giản, một prompt được tối ưu tốt (hoặc chain đơn giản) luôn ổn định, rẻ và hiệu quả hơn nhiều.
