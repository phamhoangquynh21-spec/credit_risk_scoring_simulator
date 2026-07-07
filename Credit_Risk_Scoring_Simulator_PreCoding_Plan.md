# KẾ HOẠCH TRƯỚC KHI CODE
## Dự án: Credit Risk Scoring Simulator (BNPL/Fintech Risk Dashboard)
**Người thực hiện:** Adam Pham | **Stack:** Claude Code (AI Agent Workflow) | **Timeline:** 3–4 tuần

---

## NHẬN XÉT VỀ FRAMEWORK TRONG ẢNH

Framework gốc (9 bước + 5 Agent) là một khung tốt nhưng còn thiếu 5 điểm quan trọng mà một dự án Data Science/AI thực tế cần có:

1. **Thiếu bước Data Acquisition & Data Governance** — ảnh nhảy thẳng từ "Data Model" sang "MVP", bỏ qua việc dataset đến từ đâu, license thế nào, có bias không.
2. **Thiếu Risk Register** — chỉ có "Bổ sung để đi xa hơn" (Testing/Security/CI-CD/AI Spec) nhưng không có bảng liệt kê rủi ro dự án cụ thể (data quality, scope creep, overfitting...).
3. **"AI Coding/Spec" quá mỏng** — chỉ ghi "Spec rõ trước khi code, Agent lập plan, Code đúng hướng đi" — chưa nói cụ thể spec gồm những gì.
4. **Thiếu Model Evaluation & Ethics layer** — với bài toán credit risk, đây là phần BẮT BUỘC (fairness, explainability, regulatory) — ảnh không đề cập.
5. **Thiếu bước Success Metrics / Definition of Done** — không có tiêu chí nào để biết dự án "hoàn thiện" thực sự.

Mình đã bổ sung tất cả các phần này vào kế hoạch dưới đây. Cấu trúc cuối cùng: **9 bước gốc → mở rộng thành 11 bước**, cộng thêm 4 hạng mục "đi xa hơn" (giữ nguyên A-B-C-D nhưng làm rõ chi tiết), và quy trình 5-Agent áp dụng cụ thể cho dự án này.

---

## TỔNG QUAN DỰ ÁN

| Mục | Nội dung |
|---|---|
| Tên dự án | Credit Risk Scoring Simulator |
| Bài toán | Dự đoán xác suất khách hàng vỡ nợ (default) dựa trên hồ sơ tài chính/hành vi, kèm dashboard giải thích cho người không kỹ thuật |
| Domain | Fintech / Credit Risk / BNPL |
| Đối tượng dùng | (giả lập) Risk Analyst tại một công ty BNPL — bạn đóng vai vừa là Data Scientist vừa là Business Analyst trình bày cho "stakeholder" |
| Output cuối cùng | 1 Jupyter/script pipeline (EDA → Model → Evaluation) + 1 Streamlit dashboard tương tác + 1 báo cáo business (PDF/slide) |

---

# BƯỚC 1 — MỤC TIÊU (WHY)

Trước khi hỏi "code gì", phải trả lời 3 câu hỏi nền tảng. Đây là phần Business Analyst làm trước tiên trong mọi dự án thật.

**1.1 Vì sao làm dự án này (Vision)?**
- Mục tiêu nghề nghiệp: chứng minh năng lực Data Scientist + Business Analyst trong domain Finance — đúng 2 major của bạn.
- Mục tiêu học thuật: áp dụng kiến thức Statistics, ML Classification, Business Communication vào một bài toán thật.
- Mục tiêu portfolio: đây sẽ là dự án "flagship" — loại dự án nhà tuyển dụng fintech Úc (Afterpay, Zip, big 4 banks) thực sự quan tâm.

**1.2 Ai sử dụng (User)?**
Hai nhóm người dùng giả lập — phải thiết kế cho cả hai vì đây chính là kỹ năng Business Analyst:
- **Risk Analyst (technical)**: cần xem chỉ số mô hình (AUC, Precision/Recall, Confusion Matrix), feature importance.
- **Risk Manager / Non-technical stakeholder**: cần dashboard trực quan, giải thích bằng ngôn ngữ thường ("khách hàng này rủi ro cao vì...") chứ không phải con số thống kê thô.

**1.3 Giá trị cốt lõi là gì (Value proposition)?**
- Giảm thời gian đánh giá rủi ro thủ công.
- Tăng tính minh bạch (explainability) — đúng xu hướng "Responsible AI" trong tài chính hiện nay (rất được đánh giá cao khi phỏng vấn).
- Định lượng được: ví dụ "mô hình giúp giảm X% rủi ro nợ xấu so với rule-based truyền thống" (sẽ tính cụ thể ở bước Model Evaluation).

**Kiến thức cần biết:** Đây chính là kỹ năng *Requirement Gathering* trong Business Analysis — luôn bắt đầu bằng Why/Who/What Value trước khi chạm vào dữ liệu hay code.

---

# BƯỚC 2 — USER STORIES (Người dùng cần gì)

Viết theo format chuẩn: *"Là [vai trò], tôi muốn [hành động], để [giá trị]"*. Đây cũng chính là input cho "Acceptance Criteria" sau này.

| # | User Story | Acceptance Criteria |
|---|---|---|
| US1 | Là Risk Analyst, tôi muốn nhập hồ sơ một khách hàng và nhận điểm rủi ro (0-100) | Hệ thống trả về điểm + nhãn risk band (Low/Medium/High) trong < 2 giây |
| US2 | Là Risk Manager, tôi muốn xem vì sao mô hình đánh giá một khách hàng là rủi ro cao | Dashboard hiển thị top 3-5 yếu tố ảnh hưởng (SHAP values) bằng ngôn ngữ dễ hiểu |
| US3 | Là Risk Analyst, tôi muốn xem hiệu suất tổng thể của mô hình | Dashboard có tab Model Performance: AUC-ROC, Confusion Matrix, Precision/Recall |
| US4 | Là Risk Manager, tôi muốn so sánh phân khúc khách hàng theo rủi ro | Dashboard có biểu đồ phân bố risk score theo các nhóm (độ tuổi, thu nhập, lịch sử tín dụng) |
| US5 | Là người dùng bất kỳ, tôi muốn hiểu giới hạn của mô hình | Dashboard có mục "Model Limitations & Disclaimer" |

**Kiến thức cần biết:** User Stories + Acceptance Criteria là nền tảng của Agile/Scrum — chúng biến yêu cầu mơ hồ thành tiêu chí kiểm tra được (testable), tránh "scope creep" (dự án phình to không kiểm soát).

---

# BƯỚC 3 — DATA ACQUISITION (Bước mới — ảnh thiếu)

Vì bạn chưa có dataset, đây là bước phải làm kỹ trước khi chạm Data Model.

**3.1 Nguồn dữ liệu đề xuất (theo độ ưu tiên):**
1. **Kaggle — "Give Me Some Credit"** (~150k dòng, dữ liệu tín dụng cá nhân, có biến target SeriousDlqin2yrs) — sạch, phổ biến, nhiều benchmark để so sánh.
2. **Kaggle — "Lending Club Loan Data"** — lớn hơn, thực tế hơn, nhưng cần làm sạch nhiều (phù hợp nếu muốn thể hiện kỹ năng Data Engineering).
3. **UCI — "Default of Credit Card Clients (Taiwan)"** — nhỏ gọn, sạch, phù hợp nếu muốn làm nhanh trong 3 tuần.

**Khuyến nghị cho bạn:** dùng **UCI Default of Credit Card Clients** làm dataset chính (30k dòng, đủ lớn để có ý nghĩa thống kê, đủ nhỏ để chạy nhanh trên máy cá nhân, đã được dùng trong hàng trăm paper nên bạn dễ tham khảo cách người khác làm).

**3.2 Data Governance checklist (phải làm, kể cả với dataset học thuật):**
- [ ] Kiểm tra license dataset (Kaggle/UCI đều cho phép dùng học thuật/portfolio — vẫn nên trích dẫn nguồn trong README).
- [ ] Kiểm tra dataset có PII (Personally Identifiable Information) thật không — nếu có, phải anonymize trước khi public lên GitHub.
- [ ] Ghi chú ngày tải dataset + phiên bản (data versioning) — để tái lập kết quả sau này.

**Kiến thức cần biết:** Trong công việc thật, đây là lúc một Data Engineer/Analyst phải hỏi: dữ liệu có hợp pháp để dùng không, có đại diện cho dân số thực không (representativeness), có bị lệch (bias) theo nhóm nhân khẩu học không — vì credit risk model bị quy định chặt bởi luật chống phân biệt đối xử (anti-discrimination) ở hầu hết quốc gia, kể cả Úc.

---

# BƯỚC 4 — DATA MODEL

**4.1 Xác định dữ liệu chính (sau khi chọn dataset ở Bước 3):**
- Biến target: `default_payment_next_month` (binary: 0 = không vỡ nợ, 1 = vỡ nợ).
- Biến đầu vào dự kiến: hạn mức tín dụng, tuổi, giới tính, học vấn, tình trạng hôn nhân, lịch sử thanh toán 6 tháng gần nhất, số dư hóa đơn, số tiền đã thanh toán.

**4.2 Quan hệ giữa các thực thể:**
Với dataset dạng bảng phẳng (flat CSV) thì không cần ERD phức tạp, nhưng vẫn nên vẽ sơ đồ logic:
```
Customer (1) ---- (n) Payment History (6 tháng)
Customer (1) ---- (1) Risk Score (output của model)
```

**4.3 Schema/Định dạng, phân quyền:**
- Vì là dự án cá nhân, không cần phân quyền phức tạp — nhưng nên thiết kế "as if" có 2 role (Analyst xem chi tiết, Manager chỉ xem dashboard tổng) để thể hiện tư duy hệ thống thật.
- Lưu schema vào file `data_dictionary.md` — liệt kê tên cột, kiểu dữ liệu, ý nghĩa, đơn vị.

**Kiến thức cần biết:** Data Dictionary là tài liệu bắt buộc trong mọi dự án dữ liệu chuyên nghiệp — giúp người khác (hoặc chính bạn 6 tháng sau) hiểu dữ liệu mà không cần đọc lại code.

---

# BƯỚC 5 — MVP (Minimum Viable Product)

**Câu hỏi cốt lõi: cái gì là tối thiểu để dự án "chạy được và có giá trị"?**

MVP của bạn (tuần 1-2):
1. EDA cơ bản (phân bố target, missing values, outliers).
2. Một mô hình baseline (Logistic Regression) — đơn giản, dễ giải thích, là chuẩn ngành để so sánh.
3. Một mô hình nâng cao (Random Forest hoặc XGBoost) — để so sánh hiệu suất.
4. Dashboard Streamlit tối giản: nhập input → ra risk score.

**Những gì KHÔNG nằm trong MVP (để tránh scope creep):**
- Deep Learning / Neural Network (không cần thiết cho bài toán tabular nhỏ này, và Random Forest/XGBoost thường còn tốt hơn).
- Real-time API phục vụ production thật.
- Hệ thống authentication/login.

**Kiến thức cần biết:** MVP không có nghĩa là "làm cẩu thả" — nó có nghĩa là "phạm vi nhỏ nhất nhưng đầy đủ vòng đời" (end-to-end). Một MVP tốt luôn đi từ đầu đến cuối (data → model → output) trước khi tối ưu từng phần.

---

# BƯỚC 6 — PROTOTYPE

**6.1 Phác thảo luồng (User Flow):**
```
[Người dùng mở dashboard]
        ↓
[Chọn 1 trong 2 chế độ: "Nhập khách hàng mới" / "Xem tổng quan dataset"]
        ↓
[Nhập input form] → [Model dự đoán] → [Hiển thị Risk Score + SHAP explanation]
        ↓
[Tab Model Performance] → [AUC, Confusion Matrix, Feature Importance toàn cục]
```

**6.2 Kiểm tra khả năng mở rộng (Can it scale)?**
- Với dataset 30k dòng và Streamlit, không có vấn đề về scale ở giai đoạn portfolio.
- Nhưng vẫn nên thiết kế code theo hướng "nếu sau này dataset lên 1 triệu dòng thì sao" — ví dụ dùng `@st.cache_data` để tránh load lại dữ liệu mỗi lần tương tác.

**6.3 Wireframe (gợi ý dùng Lucid hoặc vẽ tay):**
Mình có thể tạo wireframe trực quan cho dashboard này trong Lucidchart nếu bạn muốn — chỉ cần xác nhận.

**Kiến thức cần biết:** Prototype không cần code thật — có thể là wireframe giấy hoặc Figma. Mục đích là phát hiện vấn đề UX TRƯỚC khi tốn thời gian code, vì sửa thiết kế trên giấy rẻ hơn rất nhiều so với sửa code.

---

# BƯỚC 7 — TƯƠNG LAI DỰ ÁN (Định hướng dài hạn)

**7.1 Holiday hay production?**
Dự án này ở dạng "portfolio production-quality" — nghĩa là không phải production thật (không cần chịu tải hàng nghìn user) nhưng phải đạt chất lượng đủ để demo trong phỏng vấn hoặc deploy public.

**7.2 Có cần scale không?**
Không trong giai đoạn này — nhưng kiến trúc nên tách rời rõ ràng: `data/`, `src/model/`, `src/dashboard/`, `notebooks/` để dễ refactor sau.

**7.3 Hướng mở rộng tương lai (ghi vào README để thể hiện tầm nhìn):**
- Tích hợp thêm dữ liệu hành vi (transaction history) nếu có.
- Thêm mô hình Fairness Audit (kiểm tra mô hình có thiên vị theo giới tính/độ tuổi không).
- Deploy lên Streamlit Cloud hoặc Hugging Face Spaces để có link public trong CV.

---

# BƯỚC 8 — THÀNH PHẦN HỆ THỐNG (System Architecture)

| Layer | Công nghệ | Vai trò |
|---|---|---|
| Frontend | Streamlit | Dashboard tương tác, input form |
| Backend/Logic | Python (scikit-learn, xgboost, shap) | Training, inference, explainability |
| Database/Storage | CSV/Parquet local (không cần DB thật cho quy mô này) | Lưu dataset đã xử lý + model đã train (`.pkl`) |
| Tích hợp job nền | Không cần (batch xử lý 1 lần khi chạy script) | — |

**Lý do chọn Streamlit thay vì Power BI/Tableau cho dự án này:** vì bạn cần tích hợp model ML Python trực tiếp (SHAP explainability, real-time inference) — điều Power BI/Tableau không làm tốt. Tuy nhiên, mình khuyến nghị bạn **làm thêm 1 bản Power BI dashboard đơn giản song song** (chỉ phần thống kê mô tả, không cần model) — vì đây là kỹ năng BI Developer riêng biệt nhà tuyển dụng Business Analyst sẽ tìm kiếm.

---

# BƯỚC 9 — TECH STACK

| Hạng mục | Lựa chọn | Lý do |
|---|---|---|
| Ngôn ngữ | Python 3.11+ | Chuẩn ngành Data Science |
| Data handling | Pandas, NumPy | Xử lý dữ liệu bảng |
| ML | scikit-learn (Logistic Regression, Random Forest), XGBoost | Chuẩn ngành cho tabular classification |
| Explainability | SHAP | Chuẩn ngành cho model interpretability — rất được đánh giá cao trong fintech |
| Visualization | Plotly, Matplotlib/Seaborn | Plotly cho dashboard tương tác, Matplotlib cho biểu đồ báo cáo tĩnh |
| Dashboard | Streamlit | Nhanh, dễ deploy, phù hợp trình độ hiện tại |
| Version control | Git + GitHub | Bắt buộc cho mọi dự án portfolio |
| Environment | venv hoặc conda | Tránh xung đột thư viện |
| AI coding agent | Claude Code | Theo yêu cầu của bạn |

**Kiến thức cần biết — vì sao không dùng Deep Learning:** Với bài toán tabular (dữ liệu dạng bảng, không phải ảnh/văn bản/chuỗi thời gian phức tạp), các nghiên cứu (và thực tế Kaggle competitions) liên tục cho thấy Gradient Boosting (XGBoost/LightGBM) thường vượt trội hơn Neural Network. Biết điều này — và GIẢI THÍCH ĐƯỢC trong phỏng vấn — là một điểm cộng lớn, vì nó cho thấy bạn hiểu "dùng đúng công cụ cho đúng bài toán" thay vì chạy theo trend.

---

# BƯỚC 10 — MODEL EVALUATION & RESPONSIBLE AI (Bước mới — bắt buộc cho bài toán Credit Risk)

Đây là phần ảnh gốc hoàn toàn thiếu nhưng **bắt buộc phải có** với bài toán tín dụng.

**10.1 Metrics đánh giá mô hình:**
- AUC-ROC (chỉ số chính cho bài toán imbalanced classification).
- Precision/Recall/F1 — đặc biệt quan trọng vì False Negative (dự đoán an toàn nhưng thực ra vỡ nợ) tốn kém hơn nhiều so với False Positive.
- Confusion Matrix với business interpretation (ví dụ: "100 trường hợp False Negative tương đương bao nhiêu rủi ro tài chính giả định").

**10.2 Fairness Audit (kiểm tra thiên vị):**
- So sánh tỷ lệ dự đoán "rủi ro cao" giữa các nhóm giới tính, độ tuổi, học vấn.
- Nếu phát hiện chênh lệch lớn không có cơ sở kinh doanh hợp lý → ghi rõ trong báo cáo như một "limitation" — đây chính xác là điều một Risk Analyst thực thụ phải làm trước khi đưa mô hình vào production.

**10.3 Explainability:**
- SHAP summary plot (toàn cục): yếu tố nào ảnh hưởng nhiều nhất đến rủi ro nói chung.
- SHAP force plot (cục bộ): vì sao MỘT khách hàng cụ thể bị đánh giá rủi ro cao.

**Kiến thức cần biết:** Trong ngành tài chính thật (Úc và toàn cầu), các mô hình credit scoring chịu sự giám sát của luật chống phân biệt đối xử (Anti-Discrimination Act) và yêu cầu minh bạch (Right to Explanation dưới GDPR-style regulation). Thể hiện rằng bạn HIỂU điều này — dù chỉ là dự án portfolio — là một tín hiệu mạnh cho nhà tuyển dụng fintech.

---

# BƯỚC 11 — PHÁT TRIỂN (Development & Deployment)

**11.1 Chia thành phần để test:**
- Unit test cho hàm xử lý dữ liệu (`preprocessing.py`).
- Test cho pipeline model (đảm bảo input/output đúng shape).

**11.2 Deploy:**
- Streamlit Cloud (miễn phí, dễ nhất) hoặc Hugging Face Spaces.

**11.3 Thường xuyên (định kỳ):**
- Không cần CI/CD phức tạp cho dự án solo, nhưng nên commit Git thường xuyên theo từng milestone (xem Bước A-D bên dưới).

---

# BỔ SUNG ĐỂ ĐI XA HƠN (Mở rộng chi tiết A-B-C-D)

## A. TESTING
- **Unit test**: dùng `pytest` cho các hàm xử lý dữ liệu và feature engineering.
- **Integration test**: đảm bảo toàn bộ pipeline (raw data → cleaned data → model → prediction) chạy không lỗi end-to-end.
- **Acceptance criteria check**: chạy lại checklist từ Bước 2 (User Stories) để xác nhận đã đáp ứng.

## B. SECURITY
- Không có authentication thật cần thiết (dự án local/demo) — nhưng nếu deploy public, cân nhắc giới hạn input (validate input để tránh injection nếu dùng SQL sau này).
- Không bao giờ commit dataset có PII thật lên GitHub public (dataset bạn dùng đã anonymized sẵn).
- Validate input form trên Streamlit (ví dụ: tuổi phải > 0, hạn mức tín dụng không âm).

## C. CI/CD + OBSERVABILITY
- Ở quy mô portfolio, "CI/CD" đơn giản hóa thành: GitHub Actions chạy `pytest` tự động mỗi lần push (thể hiện bạn biết khái niệm này, dù dự án nhỏ).
- Observability: log lại số lần dashboard được dùng, lỗi runtime (nếu deploy public) — dùng Streamlit's built-in logging là đủ.

## D. AI CODING / SPEC (làm rõ — đây là phần ảnh viết mơ hồ nhất)

Spec rõ trước khi code nghĩa là viết ra **3 tài liệu** trước khi mở Claude Code:

1. **PRD (Product Requirements Document)** — tổng hợp Bước 1-2 (Mục tiêu + User Stories) thành 1 file.
2. **Technical Spec** — tổng hợp Bước 4, 8, 9 (Data Model, Architecture, Tech Stack) thành 1 file, bao gồm cả cấu trúc thư mục dự kiến:
```
credit-risk-simulator/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   └── 01_eda.ipynb
├── src/
│   ├── preprocessing.py
│   ├── train_model.py
│   ├── explain.py
│   └── dashboard.py
├── tests/
├── models/
├── reports/
├── README.md
└── requirements.txt
```
3. **Agent Plan** — chia nhỏ công việc thành các task cụ thể để đưa cho Claude Code theo từng phiên, KHÔNG đưa toàn bộ dự án vào 1 prompt duy nhất.

**Kiến thức cần biết — vì sao Spec-first quan trọng với AI Agent coding:** AI Agent (kể cả Claude Code) hoạt động tốt nhất khi có ngữ cảnh rõ ràng, phạm vi nhỏ, và tiêu chí thành công cụ thể. Nếu bạn vào thẳng prompt "làm cho tôi dashboard dự đoán rủi ro tín dụng", agent sẽ phải tự đoán rất nhiều quyết định (kiến trúc, tech stack, scope) — dẫn đến code không nhất quán, khó maintain. Đây chính là lý do cả framework trong ảnh tồn tại: **Spec tốt = Code tốt**.

---

# QUY TRÌNH 5-AGENT ÁP DỤNG CHO DỰ ÁN NÀY

Vì bạn dùng Claude Code (1 agent duy nhất, không phải multi-agent platform thật), bạn sẽ **đóng vai điều phối** và yêu cầu Claude Code đóng từng vai trò theo từng phiên làm việc riêng biệt — đây là cách "giả lập" quy trình 5-agent một cách thực tế:

| # | Agent | Việc cần làm | Output |
|---|---|---|---|
| 1 | Business Analyst Agent | Yêu cầu Claude Code tổng hợp Bước 1-2 thành PRD.md | PRD, User Stories |
| 2 | Solution Architect Agent | Yêu cầu thiết kế Data Model + cấu trúc thư mục + tech stack (đã có sẵn ở Bước 4, 8, 9 — đưa vào để agent xác nhận/tinh chỉnh) | Solution Design |
| 3 | Tech Lead Agent | Yêu cầu viết Technical Spec chi tiết: API nội bộ (hàm nào nhận input gì, trả về gì), schema dữ liệu, breakdown task theo tuần | Tech Spec, Task breakdown |
| 4 | QA Engineer Agent | Yêu cầu viết test plan + test cases dựa trên Acceptance Criteria ở Bước 2 | Test Plan |
| 5 | DevOps Agent | Yêu cầu hướng dẫn deploy lên Streamlit Cloud + checklist trước khi public | Deploy Plan |

**Cách thực hành:** mỗi khi mở phiên Claude Code mới cho một giai đoạn, dán đúng phần Spec liên quan (không dán toàn bộ tài liệu này) — giữ ngữ cảnh gọn để agent tập trung.

---

# DEFINITION OF DONE (Bước mới — tiêu chí hoàn thiện)

Dự án được coi là HOÀN THIỆN khi đạt đủ các tiêu chí sau:

- [ ] Tất cả 5 User Stories (Bước 2) đạt Acceptance Criteria.
- [ ] Mô hình đạt AUC-ROC ≥ 0.75 (chuẩn chấp nhận được cho bài toán credit scoring tabular).
- [ ] Có Fairness Audit report (dù chỉ phát hiện và ghi nhận, không cần "sửa" hoàn toàn).
- [ ] Dashboard chạy không lỗi, deploy public có link truy cập được.
- [ ] README.md đầy đủ: mục tiêu, cách chạy, kết quả, limitations, hướng mở rộng.
- [ ] Code có test (`pytest`) chạy pass.
- [ ] Có ít nhất 1 báo cáo business (PDF/slide) trình bày kết quả bằng ngôn ngữ phi kỹ thuật — để luyện kỹ năng Business Analyst.

---

# RISK REGISTER (Bước mới)

| Rủi ro | Khả năng | Tác động | Cách giảm thiểu |
|---|---|---|---|
| Dataset mất cân bằng (ít trường hợp default) | Cao | Trung bình | Dùng class_weight, SMOTE, hoặc đánh giá bằng AUC thay vì Accuracy |
| Overfitting trên Random Forest/XGBoost | Trung bình | Cao | Cross-validation, regularization, theo dõi gap giữa train/test score |
| Scope creep (thêm tính năng giữa chừng) | Cao (đặc biệt với người mới) | Cao | Bám sát MVP ở Bước 5, mọi ý tưởng mới ghi vào "Future Work" thay vì làm ngay |
| Hết thời gian trước deadline tự đặt | Trung bình | Trung bình | Theo timeline 4 tuần bên dưới, review tiến độ cuối mỗi tuần |
| Claude Code tạo code không nhất quán giữa các phiên | Trung bình | Trung bình | Luôn tham chiếu lại Tech Spec khi mở phiên mới (xem mục D) |

---

# TIMELINE ĐỀ XUẤT (3-4 TUẦN)

| Tuần | Giai đoạn | Công việc chính |
|---|---|---|
| Tuần 1 | Planning + Data | Bước 1-4 (Mục tiêu → Data Model), tải & làm sạch dataset, EDA đầy đủ |
| Tuần 2 | Core Build | Bước 5-6 (MVP + Prototype), train baseline + advanced model, SHAP explainability |
| Tuần 3 | System + Testing | Bước 7-11, viết test, Fairness Audit, hoàn thiện dashboard Streamlit |
| Tuần 4 | Polish + Deploy | Mục A-D, deploy public, viết README + báo cáo business, chuẩn bị nói về dự án trong phỏng vấn |

---

# BƯỚC TIẾP THEO

Mình đề xuất bạn xác nhận lại 2 điều trước khi bắt đầu Tuần 1:
1. Đồng ý dùng dataset **UCI Default of Credit Card Clients** hay muốn xem thử cả 3 nguồn trước khi quyết?
2. Bạn muốn mình soạn luôn **PRD.md** và **Technical Spec.md** (2 file thật, sẵn sàng dán vào Claude Code) ngay bây giờ, hay bạn muốn tự làm phần đó để luyện tập trước?
