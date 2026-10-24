# Báo cáo duyệt cặp Q&A — devops (2026-10-23 04:39)

> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` thuộc về người duyệt.

**18/18 cặp đã duyệt** · Đạt 14 · Cần sửa 4 · Bỏ 0 · tin cậy cao 16 / vừa 2 / thấp 0

**Phân loại cho người duyệt:** Phải đọc 1 · Chỉ hình thức 3 (câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận 14

**Kiểm tra trích dẫn nguyên văn:** khớp 102 · không khớp 0 · không kiểm được từ máy này 5

## Cặp mồi (kiểm tra người reviewer)

| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |
|---|---|---|---|
| de-qa-1218 | Nói readiness probe thất bại thì kubelet restart container (sai: readiness thất bại chỉ gỡ pod khỏi endpoints; liveness mới restart) | Cần sửa: [critical] Câu 'readinessProbe: khi thất bại quá failureThreshold, kubelet restart container' là sai: readiness fail chỉ làm Pod unready và… | có |

## Tổng hợp

| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |
|---|---|---|---|---|---|---|---|
| de-qa-1200 | Docker Compose, network và volume | Đạt | high | Có thể chấp nhận | [minor] Chunk ~720 token, vượt budget 600 của Planner. Phần bị cắt là cuối mục 'phòng thủ nhiều lớp' và 'Đánh đổi'; các ý bắt buộc (vì sao … | 720 |  |
| de-qa-1201 | Docker Compose, network và volume | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 2 ý độc lập, ~4 phút cho các ý bắt buộc (ba lỗi chỉ có hai nguyên nhân gốc: publish port và nginx phân giải tên một lần)… | 745 |  |
| de-qa-1202 | Kubernetes: các object cơ bản | Đạt | high | Có thể chấp nhận | [minor] ~744 token, bị cắt ở cuối cách 2 (nhược điểm checksum không rollback được config), mất mục immutable và hot reload. Ý bắt buộc (cơ … | 744 |  |
| de-qa-1203 | Kubernetes: các object cơ bản | Cần sửa | high | Chỉ hình thức | [major] ~806 token; điểm cắt 600 token rơi giữa nguyên nhân 7. Mất NetworkPolicy, bước 'cô lập lỗi: gọi thẳng PodIP:port từ Pod khác' (ý qu… | 806 |  |
| de-qa-1204 | Scale và độ tin cậy trên Kubernetes | Đạt | high | Có thể chấp nhận | [minor] ~751 token, cắt giữa mục rollout strategy; mất phần ingress/LB draining, 'vẫn giữ PDB', kiểm chứng và đánh đổi. Các ý bắt buộc (PDB… | 751 | 1 |
| de-qa-1205 | Scale và độ tin cậy trên Kubernetes | Đạt | high | Có thể chấp nhận | [minor] ~709 token, cắt giữa mục HPA; mất `behavior`/stabilization window và đoạn so sánh memory. Các ý bắt buộc (throttling theo chu kỳ, H… | 709 |  |
| de-qa-1206 | Infrastructure as Code | Cần sửa | high | Phải đọc | [major] Đáp án đưa `terraform state mv` làm cách chính để chuyển resource sang state khác. Trên backend remote (S3, HCP Terraform) cách này… | 701 |  |
| de-qa-1207 | Infrastructure as Code | Đạt | high | Có thể chấp nhận | [minor] ~733 token, cắt giữa ý policy-as-code; mất 'apply đúng plan file', `-replace` và 'Đánh đổi'. Ý bắt buộc (đọc `-/+`, moved, migratio… | 733 |  |
| de-qa-1208 | Dịch vụ cloud cơ bản | Đạt | high | Có thể chấp nhận | [minor] Vài chi tiết phụ chưa có câu trích: phí data transfer liên AZ (trang pricing chỉ khuyên đặt NAT cùng AZ), endpoint policy giới hạn … | 654 |  |
| de-qa-1209 | Dịch vụ cloud cơ bản | Đạt | high | Có thể chấp nhận | [minor] ~755 token, cắt giữa bước CloudTrail của quy trình; mất bước 'kiểm tra theo thứ tự chặng' và phần least privilege. Thứ tự chặng vẫn… | 755 |  |
| de-qa-1210 | Reverse proxy, load balancer và HTTPS | Đạt | high | Có thể chấp nhận | [minor] ~736 token, cắt giữa đoạn TLS re-encrypt/passthrough; mất phần thiết kế rate limit (NAT/CGNAT). Ý bắt buộc (vì sao cùng IP, XFF app… | 736 |  |
| de-qa-1211 | Reverse proxy, load balancer và HTTPS | Cần sửa | high | Chỉ hình thức | [major] Đề không nêu loại load balancer và kể kết quả 'mọi target bị đánh unhealthy, hệ thống sập hẳn'. Đáp án lại chỉ đưa ví dụ ALB, vốn f… | 736 |  |
| de-qa-1212 | Logging, monitoring và alerting | Đạt | high | Có thể chấp nhận | [minor] ~657 token, chỉ phần 'Đánh đổi' bị cắt. Mọi ý bắt buộc nằm trước điểm cắt. | 657 |  |
| de-qa-1213 | Logging, monitoring và alerting | Đạt | high | Có thể chấp nhận | [minor] ~737 token, cắt ở ý SLO 'x% request dưới 300 ms'; mất cách tính tỉ lệ trực tiếp, native histogram và 'Đánh đổi'. Ý bắt buộc (cardin… | 737 | 1 |
| de-qa-1214 | Bảo mật hạ tầng và quản lý secret | Đạt | high | Có thể chấp nhận | [minor] ~647 token, chỉ phần cuối 'Đánh đổi' (rủi ro trust policy OIDC quá lỏng) bị cắt. Ý bắt buộc nằm trước điểm cắt. | 647 |  |
| de-qa-1215 | Bảo mật hạ tầng và quản lý secret | Đạt | medium | Có thể chấp nhận | [minor] Các ý quy trình (chỉ chặn CVE mới so với baseline, quét lại định kỳ image đang chạy, admission control chỉ cho image đã ký, triage … | 665 |  |
| de-qa-1216 | CI/CD pipeline | Đạt | medium | Có thể chấp nhận | [minor] Grounding URL duy nhất là repo cộng đồng (bregman-arie/devops-exercises), không chứa nội dung về expand/contract. | 737 |  |
| de-qa-1217 | CI/CD pipeline | Cần sửa | high | Chỉ hình thức | [major] ~685 token; điểm cắt rơi ngay đầu mục 'Giữ build đúng và an toàn' (build phải đúng khi cache miss, chống cache poisoning từ PR khôn… | 685 |  |

## Ảnh hưởng nếu sửa hoặc bỏ

- de-qa-1203: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1206: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1211: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1217: bỏ thì topic còn < 2 cặp hard (SC-001)
- 18/18 cặp dài hơn 600 token: snippet của Planner sẽ bị cắt (de-qa-1200, de-qa-1201, de-qa-1202, de-qa-1203, de-qa-1204, de-qa-1205, de-qa-1206, de-qa-1207, de-qa-1208, de-qa-1209, de-qa-1210, de-qa-1211, de-qa-1212, de-qa-1213, de-qa-1214, de-qa-1215, de-qa-1216, de-qa-1217).

## Việc cho người duyệt

- **Phải đọc** (1): de-qa-1206. Sai kiến thức, lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.
- **Chỉ hình thức** (3): de-qa-1203, de-qa-1211, de-qa-1217. Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.
- **Có thể chấp nhận** (14): de-qa-1200, de-qa-1201, de-qa-1202, de-qa-1204, de-qa-1205, de-qa-1207, de-qa-1208, de-qa-1209, de-qa-1210, de-qa-1212, de-qa-1213, de-qa-1214, de-qa-1215, de-qa-1216. Mọi ý đã có trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.
- Có nhãn golden set (2): de-qa-1204, de-qa-1213. Sửa câu hỏi thì giữ các thuật ngữ chính.

## Chi tiết từng cặp

### de-qa-1200 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Docker Compose, network và volume (`devops.docker.compose-networking`) · ~720 token · hard của topic: 2

**Câu hỏi:** Một VPS chạy stack Docker Compose (nginx, api, postgres), ufw chỉ cho phép port 22, 80, 443. Vậy mà quét từ Internet vẫn thấy Postgres mở ở 5432, vì file compose có `ports: "5432:5432"`. Giải thích vì sao firewall bị "bỏ qua" và thiết kế lại network cho stack này.

**Kết luận:** Đúng và bám tài liệu Docker: giải thích được vì sao ufw bị bỏ qua và cách thiết kế lại network. Chỉ có vấn đề nhỏ về độ dài và một ý phụ (cấu hình daemon) chưa kiểm chứng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~720 token, vượt budget 600 của Planner. Phần bị cắt là cuối mục 'phòng thủ nhiều lớp' và 'Đánh đổi'; các ý bắt buộc (vì sao ufw bị bỏ qua, bỏ publish, tách network, loopback, DOCKER-USER) nằm trước điểm cắt. | Rút gọn mục 5 thành một dòng (security group + pg_hba.conf) và gộp 'Đánh đổi' thành một câu. |
| minor | factual | Ý phụ 'cấu hình daemon để loopback thành địa chỉ publish mặc định' chưa kiểm chứng được: WebFetch không đọc được phần thân mục 'Setting the default bind address for containers'. | Giữ nguyên nếu người duyệt xác nhận trên trang port-publishing; nếu không thì bỏ câu này (không phải ý chấm điểm). |

**Kiểm chứng:**
- `supported` Docker và ufw không tương thích; gói tin tới container bị chuyển hướng trước khi qua rule của ufw
  > Docker and ufw use firewall rules in ways that make them incompatible with each other.  
  > — https://docs.docker.com/engine/network/packet-filtering-firewalls/
  _Trang cũng ghi: "Packets are routed before the firewall rules can be applied, effectively ignoring your firewall configuration."_
- `supported` Port publish dùng NAT/DNAT (bảng nat, chain DOCKER)
  > In the `nat` table, Docker creates chain `DOCKER` and adds rules to implement masquerading and port-mapping.  
  > — https://docs.docker.com/engine/network/firewall-iptables/
- `supported` Publish port mặc định không an toàn, mở trên mọi địa chỉ của host
  > Publishing container ports is insecure by default.  
  > — https://docs.docker.com/engine/network/port-publishing/
- `supported` Service gọi nhau bằng CONTAINER_PORT; HOST_PORT chỉ dùng khi truy cập từ ngoài network
  > Networked service-to-service communication uses the `CONTAINER_PORT`.  
  > — https://docs.docker.com/compose/how-tos/networking/
- `supported` Hai network riêng cô lập proxy khỏi db, chỉ app nối cả hai
  > The `proxy` service is isolated from the `db` service, because they do not share a network in common. Only `app` can talk to both.  
  > — https://docs.docker.com/compose/how-tos/networking/
- `supported` `internal: true` tạo network không kết nối ra interface của host
  > Setting `internal: true` on a network creates it without a connection to the host's network interfaces.  
  > — https://docs.docker.com/compose/how-tos/networking/
- `supported` Bind 127.0.0.1 thì chỉ Docker host truy cập được port
  > If you include the localhost IP address (`127.0.0.1`, or `::1`) with the publish flag, only the Docker host can access the published container port.  
  > — https://docs.docker.com/engine/network/port-publishing/
- `supported` Chain DOCKER-USER dành cho rule của người dùng, xử lý trước rule của Docker
  > A placeholder for user-defined rules that will be processed before rules in the `DOCKER-FORWARD` and `DOCKER` chains.  
  > — https://docs.docker.com/engine/network/firewall-iptables/

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu iptables/NAT của Docker và thiết kế lại network, không phải câu định nghĩa. Junior thường chỉ biết 'bỏ ports'.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai yêu cầu (giải thích + thiết kế lại), 5 ý chấm được rõ ràng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu Docker tự chèn rule iptables (NAT) nên vượt qua ufw, và biết container nói chuyện với nhau qua network nội bộ mà không cần publish port.
- Ý bắt buộc: Docker tự thêm rule NAT cho port publish, gói tin bị chuyển tới container trước khi qua rule ufw; Publish port mặc định mở trên mọi địa chỉ của host; api gọi db bằng tên service và CONTAINER_PORT, nên db không cần `ports`; Chỉ nginx publish 80/443; tách network frontend/backend (backend có thể `internal: true`); Cần truy cập quản trị thì bind 127.0.0.1 + SSH tunnel; lọc IP nguồn thì dùng chain DOCKER-USER
- Dấu hiệu trả lời sai: Thêm rule `ufw deny 5432` và nghĩ là xong; Cho rằng api cần Postgres publish port để kết nối; Tắt iptables của Docker mà không hiểu hậu quả (container mất mạng/NAT)
- Câu hỏi nối tiếp: Nếu worker trong network internal cần gọi một API bên ngoài thì bạn nối network thế nào?

### de-qa-1201 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Docker Compose, network và volume (`devops.docker.compose-networking`) · ~745 token · hard của topic: 2

**Câu hỏi:** Bạn scale `api` lên 3 replica (`docker compose up --scale api=3`) phía sau nginx với `proxy_pass http://api:8080;`. Lần lượt gặp ba lỗi: báo xung đột port; sửa xong thì traffic không chia đều cho replica mới; và sau mỗi lần deploy (container tạo lại) nginx trả 502 cho tới khi restart. Phân tích từng lỗi và cách sửa.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 2 ý độc lập, trả lời các ý bắt buộc trong khoảng 4 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 3 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 2 ý độc lập, ~4 phút cho các ý bắt buộc (ba lỗi chỉ có hai nguyên nhân gốc: publish port và nginx phân giải tên một lần); v1 đếm 3 ý. Còn lại là gợi ý: Câu hỏi yêu cầu phân tích 3 lỗi riêng (xung đột port, chia tải lệch, 502 sau deploy) cộng cách sửa: quá 2 sub-question, khó gói trong 3–… | Bỏ lỗi 1 (xung đột port, kiến thức junior) khỏi đề; giữ 2 lỗi có chung nguyên nhân DNS của nginx. |
| minor | length | ~745 token, bị cắt giữa cách sửa 2; mất cách sửa 3 (`nginx -s reload`) và mục 'Lưu ý thêm'. Ý chính (DNS phân giải một lần, resolver + biến, `resolve` từ 1.27.3) vẫn nằm trước điểm cắt. | Bỏ mục 'Lưu ý thêm' (max_fails, proxy_next_upstream: lệch khỏi câu hỏi) và rút phần lỗi 1 còn một câu. |
| minor | factual | Địa chỉ embedded DNS `127.0.0.11` chưa trích được nguồn: WebFetch không đọc tới mục 'DNS services' của docs.docker.com/engine/network/. Đây là chi tiết cấu hình, không phải ý chấm điểm. | Người duyệt xác nhận trên mục DNS services, hoặc diễn đạt thành 'embedded DNS của Docker'. |

**Kiểm chứng:**
- `supported` Replica mới vào network với IP mới nhưng giữ tên; kết nối tới container cũ bị đóng, client phải tự phân giải lại và kết nối lại
  > It is each container's responsibility to detect this condition, look up the name again, and reconnect.  
  > — https://docs.docker.com/compose/how-tos/networking/
  _Câu trước đó: "If any containers have connections open to the old container, they are closed."_
- `supported` proxy_pass với hostname ra nhiều địa chỉ thì round-robin giữa các địa chỉ đó
  > If a domain name resolves to several addresses, all of them will be used in a round-robin fashion.  
  > — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  _Việc phân giải một lần lúc nạp cấu hình là hành vi suy ra từ câu (b) dưới đây; không có câu nguyên văn nói 'resolve once'._
- `supported` proxy_pass chứa biến thì tên không khớp upstream group sẽ được phân giải qua resolver
  > Parameter value can contain variables. In this case, if an address is specified as a domain name, the name is searched among the described server groups, and, if not found, is determined using a resolver.  
  > — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- `supported` Tham số `resolve` của `server` theo dõi đổi IP không cần restart, cần shared memory zone; trước 1.27.3 chỉ có ở bản thương mại
  > Prior to version 1.27.3, this parameter was available only as part of our commercial subscription.  
  > — https://nginx.org/en/docs/http/ngx_http_upstream_module.html
  _Cùng trang: "The server group must reside in the shared memory."_
- `supported` Passive health check mặc định max_fails=1, fail_timeout=10s
  > By default, the number of unsuccessful attempts is set to 1.  
  > — https://nginx.org/en/docs/http/ngx_http_upstream_module.html
  _fail_timeout: "By default, the parameter is set to 10 seconds."_
- `supported` proxy_next_upstream mặc định `error timeout`, không retry request non-idempotent đã gửi trừ khi bật
  > normally, requests with a non-idempotent method (POST, LOCK, PATCH) are not passed to the next server if a request has been sent to an upstream server (1.9.13)  
  > — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  _Default: "proxy_next_upstream error timeout;"_

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu DNS-based discovery của Docker và cách nginx cache kết quả phân giải; middle thường chỉ nêu được 'restart nginx'.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Rubric v2: ba lỗi chỉ có hai nguyên nhân gốc: publish port và nginx phân giải tên một lần. Ý chấm rõ nhưng 3 lỗi làm câu trả lời dài hơn 5 phút.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu service discovery qua DNS nội bộ của Docker và việc nginx open source phân giải hostname tĩnh một lần lúc nạp cấu hình.
- Ý bắt buộc: api không publish port; nginx gọi api qua network nội bộ bằng tên service; Tên `api` phân giải ra IP các replica đang chạy; nginx phân giải hostname tĩnh trong proxy_pass lúc nạp config nên không thấy replica mới và giữ IP cũ sau khi container bị tạo lại → 502; Sửa: `resolver` + biến trong proxy_pass, hoặc `server ... resolve` trong upstream (open source từ 1.27.3), hoặc reload nginx khi deploy
- Dấu hiệu trả lời sai: Cho rằng Docker tự cân bằng tải nên nginx không liên quan; Đề xuất publish mỗi replica một host port rồi liệt kê cứng trong upstream; Nói 'restart nginx' mà không giải thích vì sao cần
- Câu hỏi nối tiếp: Dùng biến trong proxy_pass thì mất những tính năng gì của block upstream, và bạn bù lại thế nào?

### de-qa-1202 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Kubernetes: các object cơ bản (`devops.k8s.core-objects`) · ~744 token · hard của topic: 2

**Câu hỏi:** Team sửa giá trị trong ConfigMap (feature flag và file `nginx.conf`) rồi `kubectl apply`. Một số Pod vẫn chạy cấu hình cũ sau nhiều giờ, một số khác nhận cấu hình mới vào các thời điểm khác nhau. Giải thích cơ chế ConfigMap được đưa vào Pod, và đề xuất cách rollout cấu hình an toàn, có thể rollback.

**Kết luận:** Cơ chế cập nhật ConfigMap (env, volume, subPath) và các cách rollout an toàn đều khớp tài liệu Kubernetes/Helm. Chỉ dài hơn budget 600 token, phần bị cắt không chứa ý bắt buộc.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~744 token, bị cắt ở cuối cách 2 (nhược điểm checksum không rollback được config), mất mục immutable và hot reload. Ý bắt buộc (cơ chế env/volume/subPath, version hóa ConfigMap để có rollout + rollback) nằm trước điểm cắt. | Đưa câu 'rollback không khôi phục config' lên ngay sau 'annotation checksum'; gộp mục 3–4 thành 1 dòng. |
| minor | factual | Ý 'Kustomize configMapGenerator tự thêm hash suffix' đúng theo hiểu biết chung nhưng không fetch được nguồn trong giới hạn 4 lần/cặp. Đây là ví dụ phụ, không phải ý chấm điểm. | Không cần sửa; người duyệt có thể đối chiếu trang Kustomize trên kubernetes.io nếu muốn. |

**Kiểm chứng:**
- `supported` ConfigMap dùng làm biến môi trường không tự cập nhật, phải restart Pod
  > ConfigMaps consumed as environment variables are not updated automatically and require a pod restart.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/configmap.md
  _kubernetes.io trả về toàn menu qua WebFetch; dùng file nguồn chính thức của trang trong repo kubernetes/website._
- `supported` ConfigMap mount qua volume được cập nhật 'eventually'; kubelet kiểm tra mỗi periodic sync, độ trễ tới sync period + cache propagation delay
  > The kubelet checks whether the mounted ConfigMap is fresh on every periodic sync.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/configmap.md
  _Cùng trang: "When a ConfigMap currently consumed in a volume is updated, projected keys are eventually updated as well."_
- `supported` subPath mount không bao giờ nhận cập nhật
  > A container using a ConfigMap as a subPath volume mount will not receive ConfigMap updates.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/configmap.md
- `supported` ConfigMap immutable không đảo lại được, chỉ xóa và tạo lại
  > You can only delete and recreate the ConfigMap.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/configmap.md
- `supported` Immutable giảm tải kube-apiserver vì kubelet đóng watch
  > significantly reducing load on kube-apiserver, by closing watches for ConfigMaps marked as immutable.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/configmap.md
- `supported` Helm: annotation checksum của config trong pod template để Deployment rollout khi config đổi
  > The `sha256sum` function can be used to ensure a deployment's annotation section is updated if another file changes:  
  > — https://helm.sh/docs/howto/charts_tips_and_tricks/

**Độ khó:** hard thật · hợp level middle, senior — Phải giải thích được triệu chứng lệch thời điểm theo node và thiết kế rollout có rollback, không chỉ biết ConfigMap là gì.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích cơ chế + đề xuất rollout; 4–5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu ConfigMap đi vào Pod theo từng cách (env, volume, subPath) với hành vi cập nhật khác nhau, và biết biến thay đổi config thành một rollout có thể rollback.
- Ý bắt buộc: env/envFrom chỉ đọc lúc khởi động, không tự cập nhật; Volume cập nhật eventually theo periodic sync của kubelet, mỗi node một thời điểm; subPath không bao giờ cập nhật; File đổi nhưng app vẫn phải tự reload; Sửa ConfigMap tại chỗ không có rollout/readiness/rollback; Version hóa ConfigMap (tên có hash) và đổi reference trong pod template để có rolling update và `rollout undo`
- Dấu hiệu trả lời sai: Cho rằng `kubectl apply` ConfigMap sẽ restart Pod; Nghĩ env var cũng tự cập nhật như volume; Dùng annotation checksum và tin rằng rollback sẽ khôi phục config cũ
- Câu hỏi nối tiếp: Với Secret version hóa theo hash, bạn dọn các object cũ thế nào mà không xóa nhầm cái Pod đang dùng?

### de-qa-1203 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Kubernetes: các object cơ bản (`devops.k8s.core-objects`) · ~806 token · hard của topic: 2

**Câu hỏi:** Service `payments` trong Kubernetes thỉnh thoảng lỗi với một phần nhỏ request (connection refused, hoặc nhận response từ phiên bản cũ), trong khi `kubectl get pods` cho thấy mọi Pod đều Running. Trình bày quy trình debug từ Service xuống Pod, các nguyên nhân thường gặp và cách xác nhận từng nguyên nhân bằng kubectl.

**Kết luận:** Các bước debug và lệnh kubectl đều đúng theo tài liệu Kubernetes. Cần sửa vì đáp án liệt kê 8 nguyên nhân (khó chấm, quá 5 phút) và ~806 token nên bước 'cô lập lỗi bằng cách gọi thẳng PodIP' bị cắt khỏi snippet. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì length.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | ~806 token; điểm cắt 600 token rơi giữa nguyên nhân 7. Mất NetworkPolicy, bước 'cô lập lỗi: gọi thẳng PodIP:port từ Pod khác' (ý quan trọng nhất của quy trình) và phần phòng ngừa. | Đưa bước 'cô lập lỗi' lên ngay sau 'Đường đi của request'; bỏ chi tiết `kubectl debug --copy-to`; gộp nguyên nhân 5–8 thành một dòng. |
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (quy trình debug, nguyên nhân và cách xác nhận là một bài chẩn đoán); v1 đếm 3 ý. Còn lại là gợi ý: Đáp án có 8 nguyên nhân ngang hàng, không có thứ tự ưu tiên; khó chấm và vượt 5 phút. Câu hỏi gộp 3 yêu cầu (quy trình, nguyên nhân, cách xác nhận). | Giữ 4 nguyên nhân khớp triệu chứng nhất (selector quá rộng → response bản cũ; targetPort sai, thiếu readiness, rollout/SIGTERM → refused) và nêu rõ đó là các ý chấm điểm. |
| minor | factual | Ý 'port khai báo dạng chuỗi "9376" thay vì số' chưa tìm được câu nguồn tương ứng. | Bỏ ví dụ này, giữ 'named port hoặc số port khác giữa các phiên bản'. |

**Kiểm chứng:**
- `supported` EndpointSlice là kết quả của control loop đánh giá selector của Service
  > Inside the Kubernetes system is a control loop which evaluates the selector of every Service  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/debug/debug-application/debug-service.md
  _kubernetes.io trả về toàn menu qua WebFetch; dùng file nguồn chính thức trong repo kubernetes/website._
- `supported` Xem endpoint thật bằng `kubectl get endpointslices -l kubernetes.io/service-name=...`
  > kubectl get endpointslices -l kubernetes.io/service-name=hostnames  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/debug/debug-application/debug-service.md
- `supported` targetPort/named port không khớp với một nhóm Pod gây lỗi trên đúng các Pod đó
  > Is the `targetPort` correct for your Pods (some Pods use a different port than the Service)?  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/debug/debug-application/debug-service.md
- `supported` Readiness fail thì Pod bị gỡ khỏi EndpointSlice của Service
  > controller removes the Pod's IP address from the EndpointSlices of all Services that match the Pod.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
- `supported` Kiểm kube-proxy trên node bằng `iptables-save` / `ipvsadm -ln` và đọc log kube-proxy
  > If this still fails, look at the `kube-proxy` logs for specific lines like:  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/debug/debug-application/debug-service.md
  _Trang có ví dụ `iptables-save | grep hostnames` và `ipvsadm -ln`._
- `supported` `kubectl debug --target` thêm ephemeral container dùng chung process namespace; `--copy-to --share-processes` debug trên bản sao
  > The `--target` parameter targets the process namespace of another container.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/debug/debug-application/debug-running-pod.md
  _Ví dụ trên trang: "kubectl debug myapp -it --image=ubuntu --share-processes --copy-to=myapp-debug"_

**Độ khó:** hard thật · hợp level middle, senior — Debug lỗi ngắt quãng qua nhiều lớp (DNS, kube-proxy, EndpointSlice, Pod) là kỹ năng vận hành thật, không phải định nghĩa.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, khó chấm — Rubric v2: quy trình debug, nguyên nhân và cách xác nhận là một bài chẩn đoán. 8 nguyên nhân + nhiều lệnh, quá dài và khó chọn ý chấm.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết request đi từ Service tới Pod thế nào và debug lỗi chỉ xảy ra với một phần request bằng cách nhìn EndpointSlice thay vì chỉ nhìn `kubectl get pods`.
- Ý bắt buộc: Running không có nghĩa là Ready; Service route theo EndpointSlice; Xem EndpointSlice thật và so với Pod mong đợi (số lượng, ready, terminating); Selector quá rộng làm traffic lọt vào Pod cũ/canary → response từ phiên bản cũ; targetPort sai hoặc thiếu readiness/SIGTERM xử lý kém → connection refused; Cô lập: gọi thẳng PodIP:port từ một Pod khác để tách lỗi Service khỏi lỗi Pod
- Dấu hiệu trả lời sai: Dừng ở `kubectl get pods` thấy Running là kết luận Pod ổn; Restart toàn bộ Pod trước khi tìm nguyên nhân; Không biết Service chọn Pod bằng label selector
- Câu hỏi nối tiếp: Nếu lỗi chỉ xảy ra với client nằm trên một node cụ thể, bạn nghi ngờ thành phần nào và kiểm tra ra sao?

**Đề xuất sửa:**
- Đáp án: Rút còn khoảng 550 token: giữ đường đi request, bước xem EndpointSlice, 4 nguyên nhân khớp triệu chứng, bước cô lập bằng PodIP (đưa lên trước), một dòng cho kube-proxy/NetworkPolicy. Bỏ chi tiết `--copy-to` và ví dụ port dạng chuỗi.

### de-qa-1204 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Scale và độ tin cậy trên Kubernetes (`devops.k8s.scaling-reliability`) · ~751 token · hard của topic: 2 · golden: g10

**Câu hỏi:** Mỗi lần rolling update Deployment `checkout`, dashboard ghi nhận vài giây lỗi 502/connection reset ở ingress, dù readiness probe đã cấu hình và đã có PodDisruptionBudget `minAvailable: 80%`. Giải thích vì sao lỗi vẫn xảy ra, và thiết kế graceful shutdown cùng chiến lược rollout không lỗi.

**Kết luận:** Đúng trọng tâm: PDB không giới hạn rolling update, race giữa SIGTERM và việc gỡ endpoint, preStop + grace period + maxUnavailable 0. Mọi ý chính có nguồn Kubernetes; cặp có golden label g10 nên chỉ nên rút gọn nhẹ.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~751 token, cắt giữa mục rollout strategy; mất phần ingress/LB draining, 'vẫn giữ PDB', kiểm chứng và đánh đổi. Các ý bắt buộc (PDB, race, preStop, xử lý SIGTERM, grace period, maxUnavailable 0) đều trước điểm cắt. | Gộp 'Nguyên nhân phụ' thành một dòng và rút 'Đánh đổi'; không đổi cách diễn đạt các ý chính vì cặp có golden label g10. |

**Kiểm chứng:**
- `supported` Deployment/StatefulSet không bị PDB giới hạn khi rolling upgrade
  > workload resources (such as Deployment and StatefulSet) are not limited by PDBs when doing rolling upgrades.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/disruptions.md
  _kubernetes.io trả về toàn menu qua WebFetch; dùng file nguồn chính thức trong repo kubernetes/website._
- `supported` PDB áp dụng cho disruption đi qua Eviction API
  > respect PodDisruptionBudgets by calling the Eviction API instead of directly deleting pods or deployments.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/disruptions.md
- `supported` Kubelet chạy preStop rồi gửi SIGTERM tới PID 1
  > The kubelet triggers the container runtime to send a TERM signal to process 1 inside each container.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
- `supported` Endpoint của Pod đang terminate chuyển sang ready: false, không bị gỡ ngay
  > Any endpoints that represent the terminating Pods are not immediately removed from EndpointSlices,  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
  _Cùng trang: "Terminating endpoints always have their `ready` status as `false`"_
- `supported` terminationGracePeriodSeconds mặc định 30s; preStop còn chạy khi hết hạn thì gia hạn một lần 2 giây
  > the kubelet requests a small, one-off grace period extension of 2 seconds.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
  _Cùng trang: "The default `terminationGracePeriodSeconds` setting is 30 seconds."_
- `supported` maxUnavailable/maxSurge giới hạn số Pod thiếu/dư trong rollout; minReadySeconds là thời gian Pod phải ready mới tính available
  > `.spec.minReadySeconds` is an optional field that specifies the minimum number of seconds for which a newly created Pod should be ready without any of its containers crashing, for it to be considered available.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/controllers/deployment.md

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu luồng terminate của Pod và tính bất đồng bộ giữa kubelet và các tầng định tuyến; middle hay dừng ở 'đã có readiness'.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Giải thích + thiết kế (graceful shutdown và rollout là một thiết kế liền nhau); 5 ý chấm rõ. Có golden label g10.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao Pod bị tắt trong rolling update vẫn nhận request, và cách cấu hình để tắt Pod mà không rớt request.
- Ý bắt buộc: PDB chỉ giới hạn eviction (drain, autoscaler), không giới hạn rolling update; SIGTERM và việc gỡ endpoint diễn ra song song, các tầng định tuyến cập nhật trễ; preStop sleep vài giây để endpoint kịp gỡ trước khi app nhận SIGTERM; App bắt SIGTERM: ngừng nhận mới, xử lý xong request đang chạy; grace period đủ dài; maxUnavailable: 0, maxSurge > 0 để luôn đủ capacity
- Dấu hiệu trả lời sai: Tăng minAvailable của PDB để chữa lỗi rollout; Cho rằng readiness probe fail sẽ chặn traffic ngay lập tức trên mọi node; Đặt grace period rất dài mà app không xử lý SIGTERM (PID 1 là shell)
- Câu hỏi nối tiếp: Nếu container chạy app qua một shell script làm PID 1, chuyện gì xảy ra với SIGTERM và bạn sửa thế nào?

### de-qa-1205 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Scale và độ tin cậy trên Kubernetes (`devops.k8s.scaling-reliability`) · ~709 token · hard của topic: 2

**Câu hỏi:** Service `search` có p99 latency tăng vọt giờ cao điểm, trong khi dashboard cho thấy CPU trung bình chỉ khoảng 40% và HPA (target CPU utilization 70%) không scale thêm. Container đặt `requests.cpu: 1`, `limits.cpu: 1`. Phân tích nguyên nhân và cách cấu hình lại.

**Kết luận:** Phân tích đúng: CPU limit gây throttling theo chu kỳ CFS làm tăng p99 dù CPU trung bình thấp, và HPA tính theo % request nên không scale. Mọi ý chính có nguồn chính thức (Kubernetes, kernel, cAdvisor).

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~709 token, cắt giữa mục HPA; mất `behavior`/stabilization window và đoạn so sánh memory. Các ý bắt buộc (throttling theo chu kỳ, HPA theo % request, metric xác nhận, nâng/bỏ CPU limit) nằm trước điểm cắt. | Bỏ dòng tolerance/Pod chưa ready và rút đoạn memory còn một câu. |

**Kiểm chứng:**
- `supported` CPU limit được thực thi bằng throttling
  > `cpu` limits are enforced by CPU throttling.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/manage-resources-containers.md
  _kubernetes.io trả về toàn menu qua WebFetch; dùng file nguồn chính thức trong repo kubernetes/website._
- `supported` Quota CPU tính theo từng period; dùng hết quota thì bị throttle tới period sau
  > Throttled threads will not be able to run again until the next period when the quota is replenished.  
  > — https://docs.kernel.org/scheduler/sched-bwc.html
  _Cùng trang: "Within each given “period” (microseconds), a task group is allocated up to “quota” microseconds of CPU time."_
- `supported` HPA tính utilization theo % của resource request
  > calculates the utilization value as a percentage of the equivalent resource request on the containers in each Pod  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale.md
  _Công thức trên trang: desiredReplicas = ceil(currentReplicas × currentMetricValue / desiredMetricValue)._
- `supported` HPA có tolerance mặc định 10% và xử lý bảo thủ Pod chưa ready
  > the default cluster-wide tolerance of 10%  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale.md
  _Cùng trang: "the controller conservatively assumes that the not-yet-ready pods are consuming 0%"_
- `supported` Xác nhận bằng metric cAdvisor container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total
  > `container_cpu_cfs_throttled_periods_total` \| Counter \| Number of throttled period intervals  
  > — https://raw.githubusercontent.com/google/cadvisor/master/docs/storage/prometheus.md
- `supported` Container được dùng vượt request khi node còn tài nguyên
  > it's possible (and allowed) for a container to use more resource than its `request` for that resource specifies.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/manage-resources-containers.md
- `supported` Scale down có stabilization window mặc định 300 giây
  > For scaling down the stabilization window is _300_ seconds  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale.md
- `supported` Vượt memory limit dẫn tới OOM kill, thực thi kiểu phản ứng
  > `memory` limits are enforced by the kernel with out of memory (OOM) kills.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/configuration/manage-resources-containers.md

**Độ khó:** hard thật · hợp level middle, senior — Phải nối được hiện tượng (p99 cao, CPU trung bình thấp) với cơ chế CFS quota và cách HPA tính toán; điển hình cho câu hỏi senior.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + cấu hình lại; 4–5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu khác biệt giữa CPU request và limit, cơ chế throttling, và cách HPA quyết định scale.
- Ý bắt buộc: CPU limit = throttling theo chu kỳ ngắn; burst dùng hết quota rồi phải chờ → tail latency tăng; CPU trung bình theo phút làm phẳng burst nên nhìn vẫn thấp; HPA tính % theo request, 40% < 70% nên không scale (HPA đúng); Xác nhận bằng tỉ lệ throttled periods / periods của cAdvisor; Nâng/bỏ CPU limit cho service nhạy latency, khớp số thread với CPU, scale theo metric sát SLO
- Dấu hiệu trả lời sai: Cho rằng HPA tính theo % của limit; Đề xuất tăng limit memory hoặc thêm node mà không chứng minh throttling; Nói CPU vượt limit sẽ bị OOM kill
- Câu hỏi nối tiếp: Bỏ CPU limit thì Pod đổi QoS class thế nào, và rủi ro gì cho các Pod khác trên node?

### de-qa-1206 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Infrastructure as Code (`devops.iac.terraform`) · ~701 token · hard của topic: 2

**Câu hỏi:** Một repo Terraform quản lý toàn bộ hạ tầng production trong một state duy nhất: `terraform plan` mất hơn 15 phút, thường xuyên kẹt lock, và lần nào plan cũng thấy thay đổi lạ vì có người sửa tay trên console. Bạn tái cấu trúc state và xây quy trình phát hiện, xử lý drift như thế nào?

**Kết luận:** Phần phát hiện và xử lý drift đúng, có nguồn Terraform. Cần sửa ý 'dùng `terraform state mv` để chuyển resource sang state khác': tùy chọn `-state-out` là legacy, chỉ dùng cho local state, không hợp với backend remote của team.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | outdated | Đáp án đưa `terraform state mv` làm cách chính để chuyển resource sang state khác. Trên backend remote (S3, HCP Terraform) cách này không áp dụng trực tiếp; option sang file khác là legacy, chỉ cho local state. Ứng viên trả lời theo cách hiện đại có thể bị chấm lệch. | Đổi thành: 'Sang state khác: khai báo `import` block ở stack mới, rồi bỏ khỏi stack cũ bằng `removed` block (hoặc `terraform state rm`); plan cả hai phía phải là No changes'. |
| minor | factual | Đáp án gợi ý `terraform_remote_state` nhưng tài liệu Terraform khuyến nghị publish output ra nơi riêng (hoặc data source tra theo tag), vì data source này cần quyền đọc toàn bộ state, mâu thuẫn với lo ngại 'ai đọc được state là đọc được secret' nêu ở đầu đáp án. | Ưu tiên data source tra theo tag/tên hoặc output publish ra SSM/Consul; nhắc rủi ro quyền đọc state khi dùng `terraform_remote_state`. |
| minor | length | ~701 token, cắt ở dòng `-target` và mất phần 'Đánh đổi'. Ý bắt buộc nằm trước điểm cắt. | Rút 'Vấn đề của state nguyên khối' còn 2 dòng. |
| minor | interview_fit | Script đếm 6 sub-question do dấu phẩy trong phần mô tả; thực tế có 2 yêu cầu (tách state, quy trình drift), vẫn vừa 5 phút. | Không cần sửa. |

**Kiểm chứng:**
- `supported` `moved` block đổi địa chỉ resource mà không destroy
  > You can use a `moved` block to update a resource address without destroying it.  
  > — https://developer.hashicorp.com/terraform/language/modules/develop/refactoring
- `outdated` Chuyển resource sang state khác bằng `terraform state mv`
  > For configurations using the `local` state mv only, `terraform state mv` also accepts the legacy options  
  > — https://developer.hashicorp.com/terraform/cli/commands/state/mv
  _Các option chuyển sang file state khác (`-state`, `-state-out`) là legacy và chỉ cho local state. Với backend remote nên dùng `import` (block từ Terraform 1.5) ở state mới rồi bỏ khỏi state cũ (`removed` block hoặc `terraform state rm`)._
- `supported` Nối các state qua output + `terraform_remote_state`
  > uses the latest state snapshot from a specified state backend to retrieve the root module output values  
  > — https://developer.hashicorp.com/terraform/language/state/remote-state-data
  _Trang khuyến nghị ưu tiên publish dữ liệu ra nơi riêng vì người dùng data source này phải đọc được toàn bộ state snapshot (thường chứa giá trị nhạy cảm)._
- `supported` `plan -detailed-exitcode`: 0 không đổi, 1 lỗi, 2 có thay đổi
  > 2 = Succeeded with non-empty diff (changes present)  
  > — https://developer.hashicorp.com/terraform/cli/commands/plan
  _Cùng trang: "0 = Succeeded with empty diff (no changes)", "1 = Error"._
- `supported` `-refresh-only` chỉ cập nhật state cho khớp thay đổi ngoài Terraform
  > creates a plan whose goal is only to update the Terraform state and any root module output values  
  > — https://developer.hashicorp.com/terraform/cli/commands/plan
- `supported` `ignore_changes` cho thuộc tính do hệ thống khác quản lý
  > In some rare cases, a remote object's settings are modified by processes outside of Terraform  
  > — https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- `supported` `-target` chỉ dùng cho trường hợp ngoại lệ
  > Use `-target=ADDRESS` in exceptional circumstances only, such as recovering from mistakes  
  > — https://developer.hashicorp.com/terraform/cli/commands/plan

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế ranh giới state, di chuyển resource không downtime và quy trình drift là việc của người đã vận hành Terraform ở quy mô team.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Tách state + quy trình drift; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu rủi ro của state nguyên khối, cách tách state an toàn và quy trình xử lý drift có kỷ luật.
- Ý bắt buộc: State nguyên khối: blast radius lớn, plan chậm, tranh lock, lộ secret; Tách theo vòng đời/ownership và môi trường; nối qua output/data source, tránh phụ thuộc vòng; Di chuyển không tạo lại: `moved` trong cùng config; sang state khác dùng import + removed/state rm, plan hai phía 'No changes'; Phát hiện drift: job định kỳ `plan -detailed-exitcode`, mã 2 thì alert; Xử lý drift theo trường hợp: apply về code, cập nhật code (`-refresh-only`), hoặc `ignore_changes` có chủ đích
- Dấu hiệu trả lời sai: Xóa resource khỏi state rồi để Terraform tạo lại; Dùng `-target` làm cách vận hành thường ngày; Tắt state locking để hết kẹt lock
- Câu hỏi nối tiếp: Stack app phụ thuộc output của stack network; bạn điều phối thứ tự apply giữa hai pipeline thế nào?

**Đề xuất sửa:**
- Đáp án: Thay dòng 'Sang state khác: `terraform state mv`, hoặc import vào state mới rồi `state rm` ở state cũ' bằng 'Sang state khác: `import` block ở state mới, rồi `removed` block hoặc `terraform state rm` ở state cũ (`state mv -state-out` chỉ dùng cho local state)'. Thêm nửa câu: ưu tiên data source/output publish riêng thay cho `terraform_remote_state` vì nó cần quyền đọc toàn bộ state.

### de-qa-1207 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Infrastructure as Code (`devops.iac.terraform`) · ~733 token · hard của topic: 2

**Câu hỏi:** Một PR Terraform chỉ "đổi tên" vài thứ, nhưng `terraform plan` báo database production `must be replaced` (`-/+`), và reviewer suýt approve. Bạn đọc plan và xử lý thế nào để không mất dữ liệu? Về lâu dài, dùng những cơ chế nào để chặn loại sự cố này?

**Kết luận:** Đúng và thực tế: đọc `-/+`, phân loại nguyên nhân, `moved`, `prevent_destroy` kèm giới hạn, policy trên plan JSON. Mọi ý chính có câu trích từ tài liệu Terraform.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~733 token, cắt giữa ý policy-as-code; mất 'apply đúng plan file', `-replace` và 'Đánh đổi'. Ý bắt buộc (đọc `-/+`, moved, migration DB, prevent_destroy + giới hạn) nằm trước điểm cắt. | Rút đoạn `create_before_destroy` còn một câu và đưa 'apply đúng plan file đã review' lên cạnh policy-as-code. |

**Kiểm chứng:**
- `supported` Mặc định Terraform hiểu thay đổi địa chỉ là xóa resource cũ và tạo mới
  > By default, Terraform interprets a change as an instruction to destroy the existing resource and create a new resource  
  > — https://developer.hashicorp.com/terraform/language/modules/develop/refactoring
- `supported` `moved` block cập nhật địa chỉ mà không destroy
  > You can use a `moved` block to update a resource address without destroying it.  
  > — https://developer.hashicorp.com/terraform/language/modules/develop/refactoring
- `supported` `create_before_destroy` là opt-in vì nhiều object yêu cầu tên duy nhất
  > This is an opt-in behavior because many remote object types have unique name requirements or other constraints  
  > — https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- `supported` `prevent_destroy` làm plan có destroy bị từ chối kèm lỗi
  > Terraform rejects plans that would destroy the infrastructure object associated with the resource and returns an error.  
  > — https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- `supported` `prevent_destroy` không bảo vệ khi xóa block resource khỏi cấu hình
  > This rule doesn't prevent Terraform from destroying a resource if you remove its configuration.  
  > — https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- `supported` `-replace=ADDRESS` làm hành động thay thế hiện tường minh trong plan
  > Instructs Terraform to plan to replace the resource instance with the given address.  
  > — https://developer.hashicorp.com/terraform/cli/commands/plan

**Độ khó:** hard thật · hợp level middle, senior — Đọc plan, phân loại nguyên nhân replace và thiết kế rào chắn là kinh nghiệm vận hành thật, không phải học thuộc.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Xử lý ngay + rào chắn lâu dài; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết đọc plan Terraform để phát hiện replace nguy hiểm và biết các cơ chế chặn mất dữ liệu.
- Ý bắt buộc: `-/+` + 'forces replacement' = destroy rồi create, với DB là mất dữ liệu; Đổi tên/chuyển module là đổi địa chỉ → dùng `moved` block; Nếu thật sự phải replace DB: migration riêng (DB mới, replicate, cutover, xóa sau); `prevent_destroy` cho resource stateful, nhưng không chặn khi xóa block → thêm deletion protection + backup; Policy-as-code trên plan JSON chặn delete/replace resource stateful
- Dấu hiệu trả lời sai: Approve vì 'chỉ đổi tên'; Tin `create_before_destroy` giữ được dữ liệu DB; Cho rằng `prevent_destroy` bảo vệ cả khi xóa block resource
- Câu hỏi nối tiếp: Bạn viết rule policy thế nào để phân biệt replace của launch template (chấp nhận) với replace của RDS (chặn)?

### de-qa-1208 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Dịch vụ cloud cơ bản (`devops.cloud.core-services`) · ~654 token · hard của topic: 2

**Câu hỏi:** Workload trên private subnet ở 3 AZ của AWS đi ra Internet và S3 qua một NAT gateway duy nhất đặt ở AZ-a. Hóa đơn NAT tăng mạnh (phần lớn traffic là đọc/ghi S3), và trong một sự cố ở AZ-a, workload ở AZ-b và AZ-c mất kết nối ra ngoài. Phân tích và thiết kế lại egress.

**Kết luận:** Phân tích availability và chi phí NAT đúng, giải pháp gateway endpoint cho S3 và NAT theo AZ/regional NAT đều khớp tài liệu AWS hiện hành (kể cả giới hạn của regional NAT). Vài chi tiết phụ chưa có câu trích.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | factual | Vài chi tiết phụ chưa có câu trích: phí data transfer liên AZ (trang pricing chỉ khuyên đặt NAT cùng AZ), endpoint policy giới hạn bucket, và 'chỉ một route chung' của regional NAT (trang nói AWS tự tạo route table cho NAT). | Giữ ý liên AZ (đúng theo bảng giá EC2 data transfer) nhưng người duyệt nên đối chiếu; đổi 'chỉ một route chung' thành 'không cần route table riêng cho mỗi AZ'. |
| minor | length | ~654 token, cắt ở giới hạn của regional NAT và 'Đánh đổi'. Các ý bắt buộc nằm trước điểm cắt. | Rút bullet security group/endpoint policy còn một dòng. |

**Kiểm chứng:**
- `supported` NAT gateway (zonal) được tạo trong một AZ và chỉ có dư thừa trong AZ đó
  > Each NAT gateway is created in a specific Availability Zone and implemented with redundancy in that zone.  
  > — https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html
  _Cùng trang khuyến nghị: "create a NAT gateway in each Availability Zone, and configure your routing to ensure that resources use the NAT gateway in the same Availability Zone."_
- `supported` NAT tính phí theo giờ và theo GB dữ liệu xử lý
  > When you provision a NAT gateway, you are charged for each hour that your NAT gateway is available and each gigabyte of data that it processes.  
  > — https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
- `supported` Gateway endpoint cho S3/DynamoDB không cần IGW/NAT và không tính thêm phí
  > There is no additional charge for using gateway endpoints.  
  > — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
  _Cùng trang: "Gateway VPC endpoints provide reliable connectivity to Amazon S3 and DynamoDB without requiring an internet gateway or a NAT device for your VPC."_
- `supported` Route tới prefix list của dịch vụ; longest prefix match nên traffic S3 đi qua endpoint dù có route 0.0.0.0/0
  > We use the most specific route that matches the traffic to determine how to route the traffic (longest prefix match).  
  > — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- `supported` Gateway endpoint chỉ có tác dụng với dịch vụ cùng region vì prefix list gắn với region
  > Traffic that's destined for the service (Amazon S3 or DynamoDB) in a different Region goes to the internet gateway because prefix lists are specific to a Region.  
  > — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- `supported` Regional NAT gateway tự mở rộng theo AZ có workload, không cần public subnet
  > A regional NAT gateway automatically expands across Availability Zones based on your workload presence.  
  > — https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html
  _Cùng trang: "Enhanced security – No public subnets required."_
- `supported` Regional NAT không hỗ trợ private NAT; mở rộng sang AZ mới có thể mất tới 60 phút, trong lúc đó xử lý chéo zone
  > It may take your regional NAT Gateway up to 60 minutes to expand to a new Availability Zone after a resource is instantiated there.  
  > — https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html
  _Cùng trang: "Regional NAT gateways do not support private NAT."_

**Độ khó:** hard thật · hợp level middle, senior — Kết hợp availability theo AZ, cơ chế định tuyến và chi phí; cần hiểu chứ không chỉ biết tên dịch vụ.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + thiết kế lại; 4–5 ý chấm rõ. Phụ thuộc AWS nhưng topic là cloud core services nên chấp nhận được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu NAT gateway là tài nguyên theo AZ, cách tính phí NAT, và dùng VPC endpoint để traffic tới dịch vụ AWS không đi qua NAT.
- Ý bắt buộc: Một NAT ở AZ-a là single point of failure theo AZ; NAT tính phí giờ + mỗi GB xử lý; traffic S3 qua NAT tốn phí xử lý (cộng phí liên AZ); Gateway endpoint cho S3/DynamoDB: miễn phí, route theo prefix list, longest prefix match; Internet egress còn lại: NAT mỗi AZ với route table riêng, hoặc regional NAT gateway; Interface endpoint có phí, cần tính điểm hòa vốn
- Dấu hiệu trả lời sai: Thêm NAT thứ hai ở AZ-a để 'dự phòng'; Cho rằng gateway endpoint dùng được cho S3 ở region khác; Đặt instance vào public subnet để khỏi trả phí NAT
- Câu hỏi nối tiếp: Làm sao chặn workload ghi dữ liệu ra một S3 bucket lạ thuộc account khác qua chính gateway endpoint này?

### de-qa-1209 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Dịch vụ cloud cơ bản (`devops.cloud.core-services`) · ~755 token · hard của topic: 2

**Câu hỏi:** Trong AWS Organizations có nhiều account, role CI ở account `tooling` assume role sang account `prod` để ghi file vào S3 bucket mã hóa bằng KMS key, và nhận `AccessDenied` dù policy của role đã có `Allow s3:PutObject`. Trình bày logic đánh giá policy của AWS và quy trình tìm ra lớp nào đang chặn.

**Kết luận:** Logic đánh giá policy (implicit deny, explicit deny thắng, cross-account cần cả hai phía Allow, key policy KMS là ngoại lệ) đúng theo tài liệu AWS, và phân tích đúng ba chặng AssumeRole → S3 → KMS.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~755 token, cắt giữa bước CloudTrail của quy trình; mất bước 'kiểm tra theo thứ tự chặng' và phần least privilege. Thứ tự chặng vẫn còn ở mục 'Ba chặng' phía trước nên ý bắt buộc không mất. | Bỏ mục 'Nguyên tắc least privilege' (lệch câu hỏi) và rút danh sách loại policy còn một dòng. |

**Kiểm chứng:**
- `supported` Mặc định mọi request bị implicit deny
  > By default, all requests are implicitly denied with the exception of the AWS account root user, which has full access.  
  > — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html
- `supported` Explicit Deny ở bất kỳ policy nào thắng mọi Allow
  > An explicit deny overrides an explicit allow.  
  > — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html
- `supported` SCP/RCP, permissions boundary chỉ giới hạn: action phải được mọi loại policy liên quan cho phép
  > This means that an action must be allowed by all three policy types.  
  > — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
  _Câu này nằm trong mục identity-based + SCP/RCP; trang không có câu nguyên văn 'SCP không cấp quyền'._
- `supported` Cross-account: request chỉ được Allow khi cả hai account cùng Allow
  > AWS allows the request only if both account policy evaluations allow the request.  
  > — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html
- `supported` Trust policy của role và key policy KMS là ngoại lệ: phải cho phép principal tường minh
  > IAM role trust policies and KMS key policies are exceptions to this logic, because they must explicitly allow access for principals.  
  > — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html
- `supported` Không có key policy cho phép thì IAM policy không có tác dụng với KMS key
  > Without permission from the key policy, IAM policies that allow permissions have no effect.  
  > — https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu nhiều lớp policy và luồng cross-account + KMS; debug AccessDenied có hệ thống là kỹ năng senior.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Logic đánh giá + quy trình tìm lớp chặn; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cách AWS gộp nhiều loại policy để ra Allow/Deny, đặc biệt cross-account và KMS, và biết debug AccessDenied theo từng lớp.
- Ý bắt buộc: Mặc định implicit deny; explicit Deny ở đâu cũng thắng; SCP/RCP, boundary, session policy chỉ thu hẹp; cần Allow từ identity hoặc resource policy; Cross-account cần cả hai phía Allow (trust policy + quyền sts:AssumeRole); SSE-KMS cần quyền trên key; key policy phải cho phép tường minh hoặc ủy quyền cho IAM; Debug: đọc lỗi, CloudTrail để thấy principal/action/resource thật, rồi kiểm từng lớp
- Dấu hiệu trả lời sai: Thêm `s3:*`/`kms:*` để 'chạy được'; Chỉ nhìn identity policy của role và bỏ qua bucket policy/key policy; Không biết SCP có thể chặn dù role có Allow
- Câu hỏi nối tiếp: Bucket policy bắt buộc dùng đúng KMS key qua condition; request của CI phải gửi header gì để qua được?

### de-qa-1210 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Reverse proxy, load balancer và HTTPS (`devops.net.reverse-proxy-tls`) · ~736 token · hard của topic: 2

**Câu hỏi:** Sau khi đặt API phía sau ALB và một tầng nginx, rate limiting theo IP của ứng dụng chặn nhầm hàng loạt người dùng vì mọi request đều có "cùng một IP". Team sửa bằng cách đọc phần tử đầu tiên của `X-Forwarded-For`, và kẻ tấn công lập tức vượt qua rate limit. Giải thích chuỗi tin cậy của client IP qua các tầng proxy và cách cấu hình đúng.

**Kết luận:** Giải thích đúng chuỗi tin cậy X-Forwarded-For (ALB append vào cuối, phần tử đầu do client tự khai) và cấu hình realip của nginx; khớp tài liệu AWS và nginx.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~736 token, cắt giữa đoạn TLS re-encrypt/passthrough; mất phần thiết kế rate limit (NAT/CGNAT). Ý bắt buộc (vì sao cùng IP, XFF append, đọc phải sang trái, realip, chặn đường vòng) nằm trước điểm cắt. | Rút đoạn TLS termination còn 1–2 dòng hoặc chuyển sang cặp riêng về TLS. |

**Kiểm chứng:**
- `supported` ALB mặc định ở chế độ append: nối IP client vào cuối X-Forwarded-For có sẵn
  > Otherwise, the load balancer appends the client IP address to the existing header and then passes the header to your server.  
  > — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html
  _Cùng trang: "The default value for this attribute is `append`."_
- `supported` XFF chỉ đáng tin khi được thêm bởi hệ thống được bảo vệ trong mạng
  > The entries can only be considered trustworthy if added by systems that are properly secured within the network.  
  > — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html
- `supported` `set_real_ip_from` khai báo địa chỉ proxy tin cậy
  > Defines trusted addresses that are known to send correct replacement addresses.  
  > — https://nginx.org/en/docs/http/ngx_http_realip_module.html
- `supported` `real_ip_recursive on` lấy địa chỉ không tin cậy cuối cùng trong header (đọc từ phải sang trái)
  > If recursive search is enabled, the original client address that matches one of the trusted addresses is replaced by the last non-trusted address sent in the request header field.  
  > — https://nginx.org/en/docs/http/ngx_http_realip_module.html
- `supported` Với PROXY protocol dùng `real_ip_header proxy_protocol`
  > The `proxy_protocol` parameter (1.5.12) changes the client address to the one from the PROXY protocol header.  
  > — https://nginx.org/en/docs/http/ngx_http_realip_module.html
- `supported` X-Forwarded-Proto cho app biết scheme client dùng tới load balancer
  > The `X-Forwarded-Proto` request header helps you identify the protocol (HTTP or HTTPS) that a client used to connect to your load balancer.  
  > — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu mô hình tin cậy của header qua nhiều proxy và lỗ hổng bảo mật đi kèm, không phải tra cứu.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích chuỗi tin cậy + cấu hình đúng; 4–5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu client IP thật đi qua nhiều proxy thế nào và vì sao không được tin phần tử đầu của X-Forwarded-For.
- Ý bắt buộc: Mỗi proxy mở TCP mới nên app chỉ thấy IP proxy liền trước; ALB append IP vào cuối XFF; phần tử đầu do client tự gửi, giả mạo được; Đọc từ phải sang trái, bỏ qua proxy tin cậy (nginx: set_real_ip_from + real_ip_recursive on); Backend chỉ nhận kết nối từ proxy, nếu không header giả đi vòng được; Rate limit nên dùng khóa đáng tin (IP đã chuẩn hóa, user id/API key)
- Dấu hiệu trả lời sai: Lấy phần tử đầu tiên của XFF làm client IP; Tin mọi XFF mà không giới hạn proxy tin cậy; Rate limit chỉ theo IP mà không nghĩ tới NAT/CGNAT
- Câu hỏi nối tiếp: Nếu phía trước ALB còn thêm CloudFront, cấu hình trusted proxy phải đổi thế nào?

### de-qa-1211 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Reverse proxy, load balancer và HTTPS (`devops.net.reverse-proxy-tls`) · ~736 token · hard của topic: 2

**Câu hỏi:** Endpoint `/health` dùng cho load balancer kiểm tra luôn kết nối tới DB và Redis. Một lần DB chậm vài phút, mọi target bị đánh unhealthy và hệ thống sập hẳn, kể cả các endpoint không cần DB. Phân tích failure mode này và thiết kế lại health check ở tầng load balancer/proxy.

**Kết luận:** Thiết kế lại health check (nông cho LB, dependency đưa vào metric) đúng và có nguồn. Cần sửa vì đáp án tự mâu thuẫn với đề: đề nói mọi target bị rút nên sập hẳn, nhưng đáp án lại nêu ALB fail open (vẫn route tới mọi target) mà không nói rõ LB nào bị rút thật.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Đề không nêu loại load balancer và kể kết quả 'mọi target bị đánh unhealthy, hệ thống sập hẳn'. Đáp án lại chỉ đưa ví dụ ALB, vốn fail open nên sẽ không rút hết target. Ứng viên nêu fail open có thể bị chấm là mâu thuẫn với đề, còn ứng viên nói 'LB rút hết' thì sai với ALB. | Ghi rõ trong đề tầng nào rút instance (ví dụ nginx upstream hoặc readiness probe của Kubernetes: mọi Pod NotReady thì Service không còn endpoint), và giữ ALB fail open như một ví dụ đối chiếu. |
| minor | factual | 'proxy_next_upstream chỉ retry request idempotent' chưa chính xác: nginx vẫn chuyển request non-idempotent sang server khác nếu request chưa được gửi tới upstream. | Đổi thành: 'mặc định không retry request non-idempotent đã gửi tới upstream'. |
| minor | length | ~736 token, cắt giữa ý passive check của nginx; mất ý retry và câu hỏi kiểm tra 'rút instance có giúp gì không'. Ý bắt buộc nằm trước điểm cắt. | Đưa câu 'rút instance này ra có giúp gì không?' lên ngay sau failure mode; rút mục tham số mặc định. |

**Kiểm chứng:**
- `supported` ALB fail open: target group chỉ còn target unhealthy thì route tới tất cả
  > If a target group contains only unhealthy registered targets, the load balancer routes requests to all those targets, regardless of their health status.  
  > — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- `supported` Mặc định ALB (instance/ip): interval 30s, timeout 5s, healthy 5, unhealthy 2
  > The default is 30 seconds if the target type is `instance` or `ip` and 35 seconds if the target type is `lambda`.  
  > — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
  _Timeout: "The default is 5 seconds if the target type is `instance` or `ip`"; HealthyThresholdCount "The default is 5."; UnhealthyThresholdCount "The default is 2."_
- `supported` nginx passive check mặc định max_fails=1, fail_timeout=10s
  > By default, the number of unsuccessful attempts is set to 1.  
  > — https://nginx.org/en/docs/http/ngx_http_upstream_module.html
  _fail_timeout: "By default, the parameter is set to 10 seconds."_
- `supported` proxy_next_upstream không gửi lại request non-idempotent đã gửi tới upstream, trừ khi bật
  > normally, requests with a non-idempotent method (POST, LOCK, PATCH) are not passed to the next server if a request has been sent to an upstream server (1.9.13)  
  > — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  _Đáp án viết 'chỉ retry request idempotent' là đơn giản hóa: request non-idempotent vẫn được retry nếu chưa gửi đi._

**Độ khó:** hard thật · hợp level middle, senior — Đòi hỏi tư duy failure mode (cascading failure) và phân biệt loại tín hiệu health, không phải tra cứu.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + thiết kế; ý chấm rõ nhưng tiền đề đề bài cần chỉnh.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao health check phụ thuộc dependency dùng chung biến lỗi một phần thành outage toàn phần, và cách tách tín hiệu health.
- Ý bắt buộc: Health check sâu làm lỗi dependency chung thành lỗi của mọi instance → LB rút hết; Liveness sâu còn gây restart storm dồn tải lên DB; Tách: health/liveness nông, readiness theo trạng thái instance, dependency health vào metric/alert; Xử lý lỗi dependency trong request path: timeout, circuit breaker, degrade; Chỉ lỗi cục bộ (đĩa đầy, deadlock) mới nên làm instance unhealthy
- Dấu hiệu trả lời sai: Thêm nhiều dependency hơn vào /health cho 'chắc chắn'; Tăng timeout health check để che lỗi DB chậm; Không phân biệt liveness và readiness
- Câu hỏi nối tiếp: ALB fail open khi mọi target unhealthy; điều đó thay đổi thiết kế health check của bạn thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: Endpoint `/health` của API kiểm tra luôn kết nối tới DB và Redis, và được dùng cho cả readiness probe trên Kubernetes lẫn health check của nginx upstream. Một lần DB chậm vài phút, mọi Pod bị đánh NotReady và hệ thống sập hẳn, kể cả các endpoint không cần DB. Phân tích failure mode này và thiết kế lại health check.
- Đáp án: Giữ phần thiết kế lại. Trong 'Hành vi khác nhau giữa các load balancer', nói rõ: Service Kubernetes và nginx sẽ rút hết endpoint (không fail open), còn ALB fail open. Sửa câu proxy_next_upstream như issue minor.

### de-qa-1212 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Logging, monitoring và alerting (`devops.observability.monitoring`) · ~657 token · hard của topic: 2

**Câu hỏi:** On-call nhận hơn trăm alert mỗi tuần từ các rule kiểu "error rate > 1% trong 5 phút" hay "CPU > 80%", phần lớn không cần hành động gì; trong khi một sự cố suy giảm chậm kéo dài nhiều giờ lại không ai được báo. Bạn thiết kế lại alerting dựa trên SLO như thế nào?

**Kết luận:** Bám sát SRE Workbook: burn rate, multiwindow multi-burn-rate với đúng các ngưỡng 14,4/6/1 và cửa sổ ngắn. Chỉ phần 'Đánh đổi' bị cắt ở 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~657 token, chỉ phần 'Đánh đổi' bị cắt. Mọi ý bắt buộc nằm trước điểm cắt. | Có thể rút mục 'Vệ sinh alert' để chunk dưới 600 token. |

**Kiểm chứng:**
- `supported` Burn rate là tốc độ tiêu error budget so với SLO; burn rate 1 tiêu vừa hết budget đúng cuối chu kỳ
  > Burn rate is how fast, relative to the SLO, the service consumes the error budget.  
  > — https://sre.google/workbook/alerting-on-slos/
- `supported` Alert theo ngưỡng thô có precision thấp: 0,1% lỗi trong 10 phút chỉ tiêu ~0,02% budget tháng
  > A 0.1% error rate for 10 minutes would alert, while consuming only 0.02% of the monthly error budget.  
  > — https://sre.google/workbook/alerting-on-slos/
- `supported` Page khi tiêu 2% budget trong 1 giờ hoặc 5% trong 6 giờ; ticket khi 10% trong 3 ngày
  > We recommend 2% budget consumption in one hour and 5% budget consumption in six hours as reasonable starting numbers for paging, and 10% budget consumption in three days as a good baseline for ticket alerts.  
  > — https://sre.google/workbook/alerting-on-slos/
  _Bảng 5-6: burn rate tương ứng 14,4 / 6 / 1._
- `supported` Cửa sổ ngắn đi kèm cửa sổ dài (khoảng 1/12, ví dụ 5 phút cho 1 giờ)
  > A good guideline is to make the short window 1/12 the duration of the long window  
  > — https://sre.google/workbook/alerting-on-slos/
- `supported` Service traffic thấp: bổ sung synthetic traffic
  > Generate artificial traffic to compensate for the lack of signal from real users.  
  > — https://sre.google/workbook/alerting-on-slos/
  _Ý 'đặt số request tối thiểu' không có câu nguyên văn trên trang; là ý phụ._

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế alerting theo SLO và burn rate là kiến thức SRE thực hành, cần lập luận về precision/recall.
**Dùng trong phỏng vấn:** ~4 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế; 5 ý chấm rõ. Không cần ứng viên nhớ đúng 14,4, chỉ cần hiểu cơ chế.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu alert nên gắn với ảnh hưởng tới người dùng (SLO) và cách burn rate cân bằng giữa báo nhầm và bỏ sót.
- Ý bắt buộc: Alert theo nguyên nhân (CPU) và ngưỡng thô: nhiều nhiễu, lại bỏ sót lỗi nhỏ kéo dài; SLI đo ở gần người dùng, SLO sinh ra error budget; Burn rate: tốc độ tiêu budget; 1 = hết budget đúng cuối chu kỳ; Multiwindow multi-burn-rate: page khi cháy nhanh, ticket khi cháy chậm; cửa sổ ngắn để reset nhanh; Mỗi alert có owner/runbook; không hành động được thì xóa hoặc hạ cấp
- Dấu hiệu trả lời sai: Chỉ hạ/tăng ngưỡng CPU hoặc error rate; Page cho mọi vi phạm ngưỡng, kể cả không ảnh hưởng người dùng; Nhầm SLO với SLA hoặc không biết error budget
- Câu hỏi nối tiếp: Một service chỉ có vài chục request mỗi giờ; bạn điều chỉnh alert burn rate thế nào để không page vì một request lỗi?

### de-qa-1213 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Logging, monitoring và alerting (`devops.observability.monitoring`) · ~737 token · hard của topic: 2 · golden: g18

**Câu hỏi:** Sau khi team thêm label `user_id` và `path` (URL đầy đủ) vào metric `http_request_duration_seconds`, RAM của Prometheus tăng liên tục rồi OOM. Cùng lúc, dashboard "p99 latency toàn hệ thống" đang được tính bằng cách lấy trung bình p99 từ summary của từng pod. Phân tích hai vấn đề này và cách instrument lại metric latency cho đúng.

**Kết luận:** Cả hai vấn đề (bùng nổ cardinality, lấy trung bình quantile của summary) và cách sửa bằng histogram đều khớp nguyên văn tài liệu Prometheus, kể cả khuyến nghị native histogram. Cặp có golden label g18.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~737 token, cắt ở ý SLO 'x% request dưới 300 ms'; mất cách tính tỉ lệ trực tiếp, native histogram và 'Đánh đổi'. Ý bắt buộc (cardinality, route template, summary không aggregate, histogram + sum by le) nằm trước điểm cắt. | Rút mục 'Phòng ngừa' (TSDB status, sample_limit) còn nửa dòng; không đổi các ý chính vì cặp có golden label g18. |

**Kiểm chứng:**
- `supported` Mỗi tổ hợp giá trị label là một time series; không dùng label cardinality cao như user ID
  > Do not use labels to store dimensions with high cardinality (many different label values), such as user IDs, email addresses, or other unbounded sets of values.  
  > — https://prometheus.io/docs/practices/naming/
- `supported` Mỗi labelset tốn RAM, CPU, disk, network; giữ cardinality dưới 10, xem xét giải pháp khác khi vượt 100
  > Each labelset is an additional time series that has RAM, CPU, disk, and network costs.  
  > — https://prometheus.io/docs/practices/instrumentation/
  _Cùng trang: "As a general guideline, try to keep the cardinality of your metrics below 10"._
- `supported` Quantile của summary không aggregate được; lấy trung bình là vô nghĩa thống kê
  > In this particular case, averaging the quantiles yields statistically nonsensical values.  
  > — https://prometheus.io/docs/practices/histograms/
- `supported` Dùng histogram: sum by (le) rồi histogram_quantile
  > histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m]))) // GOOD.  
  > — https://prometheus.io/docs/practices/histograms/
- `supported` Sai số ước lượng nằm trong độ rộng bucket chứa quantile
  > Error is limited by the width of the bucket the quantile is located in.  
  > — https://prometheus.io/docs/practices/histograms/
- `supported` Prometheus khuyến nghị native histogram hơn classic histogram và summary
  > If you can, use native histograms and prefer them over both classic histograms and summaries.  
  > — https://prometheus.io/docs/practices/histograms/

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu mô hình dữ liệu Prometheus và tính chất thống kê của quantile, lỗi thường gặp ngay cả ở middle.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai vấn đề + cách instrument lại; 5 ý chấm rõ. Có golden label g18.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu chi phí của label trong Prometheus và vì sao percentile phải tính từ histogram gộp, không lấy trung bình p99.
- Ý bắt buộc: Mỗi tổ hợp label là một series; user_id và URL đầy đủ là tập không giới hạn → OOM; Bỏ user_id, dùng route template thay URL; phân tích theo user chuyển sang log/trace; Quantile của summary tính ở client, không aggregate được; trung bình p99 là vô nghĩa; Dùng histogram: sum by (le) các bucket rồi histogram_quantile; Đặt bucket dày quanh ngưỡng SLO; sai số nằm trong độ rộng bucket
- Dấu hiệu trả lời sai: Tăng RAM cho Prometheus để giải quyết cardinality; Cho rằng trung bình p99 của các pod là p99 toàn hệ thống; Thêm rất nhiều bucket mà không nghĩ tới số series
- Câu hỏi nối tiếp: Với SLO '99% request dưới 300 ms', bạn viết PromQL nào chính xác hơn việc ước lượng p99?

### de-qa-1214 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Bảo mật hạ tầng và quản lý secret (`devops.security.secrets-hardening`) · ~647 token · hard của topic: 2

**Câu hỏi:** Một developer vô tình push access key AWS dài hạn lên repo GitHub, 20 phút sau mới phát hiện; key này cũng đang được CI sử dụng. Trình bày quy trình xử lý sự cố theo thứ tự ưu tiên, và những thay đổi kiến trúc để loại bỏ cả lớp rủi ro này.

**Kết luận:** Thứ tự xử lý đúng (rotate trước, điều tra, rồi mới dọn lịch sử) và kiến trúc OIDC + push protection khớp tài liệu GitHub. Chỉ câu cuối của 'Đánh đổi' bị cắt.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | ~647 token, chỉ phần cuối 'Đánh đổi' (rủi ro trust policy OIDC quá lỏng) bị cắt. Ý bắt buộc nằm trước điểm cắt. | Đưa ý 'trust condition không dùng wildcard repo/branch' vào bullet OIDC để không bị cắt. |
| minor | outdated | Trang OIDC của GitHub ghi định dạng claim `sub` đã đổi cho repo tạo sau 15/07/2026; trust condition viết theo định dạng cũ có thể không khớp. Đáp án không sai nhưng nên nhắc kiểm định dạng `sub` khi viết trust policy. | Thêm nửa câu: 'kiểm định dạng claim `sub` hiện hành của GitHub khi viết điều kiện'. |
| minor | factual | Ý bypass push protection đúng cho push protection mức repo; với push protection mức user, bypass không tạo alert trừ khi repo cũng bật. | Ghi 'push protection của repo/org'. |

**Kiểm chứng:**
- `supported` Secret lộ: bước đầu tiên là thu hồi/rotate
  > as a first step you need to revoke and/or rotate that secret  
  > — https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- `supported` Viết lại lịch sử bằng git-filter-repo không xóa được secret khỏi clone, fork, cached view theo SHA, pull request
  > Directly via their SHA-1 hashes in cached views on GitHub  
  > — https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
  _Danh sách trên trang còn có "In any clones or forks of your repository" và "Through any pull requests that reference them"._
- `supported` OIDC bỏ được credential dài hạn lưu dưới dạng secret
  > You won't need to duplicate your cloud credentials as long-lived GitHub secrets.  
  > — https://docs.github.com/en/actions/concepts/security/openid-connect
- `supported` Cloud kiểm claim của token rồi cấp token ngắn hạn chỉ hợp lệ cho một job và tự hết hạn
  > your cloud provider issues a short-lived access token that is only valid for a single job, and then automatically expires.  
  > — https://docs.github.com/en/actions/concepts/security/openid-connect
- `supported` Push protection chặn push chứa secret trước khi vào repo
  > blocks pushes that contain secrets before they reach your repository.  
  > — https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection
- `supported` Người có quyền ghi bypass được, mỗi lần bypass tạo alert và audit log
  > anyone with write access to the repository can bypass push protection by specifying a bypass reason.  
  > — https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection
  _Mỗi bypass "Adds the bypass event to the audit log" và "Creates an alert". Có thể giới hạn bằng delegated bypass._

**Độ khó:** hard thật · hợp level middle, senior — Cần ưu tiên đúng trong sự cố và đề xuất thay đổi kiến trúc loại bỏ cả lớp rủi ro, không chỉ 'xóa commit'.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Quy trình sự cố + thay đổi kiến trúc; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết xử lý secret bị lộ theo đúng thứ tự ưu tiên và biết loại bỏ credential dài hạn khỏi CI.
- Ý bắt buộc: Coi secret đã lộ là đã bị khai thác: vô hiệu hóa/rotate key ngay; Điều tra CloudTrail từ thời điểm push: API call lạ, user/key/role mới; Viết lại lịch sử chỉ giảm phơi nhiễm, secret vẫn còn ở clone/fork/PR/cached view; CI chuyển sang OIDC: token ngắn hạn cho từng job, không còn secret dài hạn; Push protection + pre-commit hook để chặn từ gốc
- Dấu hiệu trả lời sai: Xóa commit/force-push trước rồi mới tính rotate; Cho rằng repo private thì không cần rotate; Chỉ rotate mà không điều tra tài nguyên/credential kẻ tấn công đã tạo
- Câu hỏi nối tiếp: Trust policy OIDC của role production nên ràng buộc những claim nào để workflow từ PR fork không assume được?

### de-qa-1215 · Đạt · tin cậy medium · Có thể chấp nhận

**Topic:** Bảo mật hạ tầng và quản lý secret (`devops.security.secrets-hardening`) · ~665 token · hard của topic: 2

**Câu hỏi:** Image production của team bị scanner báo hàng trăm CVE, trong đó vài chục mức Critical. Developer phàn nàn rằng chặn pipeline theo mọi CVE thì không deploy được gì, còn bỏ chặn thì không ai xử lý. Thiết kế quy trình quét lỗ hổng và vá image bền vững.

**Kết luận:** Các ý kỹ thuật về image (base nhỏ, multi-stage, rebuild với --pull, pin digest + bot cập nhật, gate theo CVE đã có fix) khớp tài liệu Docker. Confidence medium vì các ý quy trình (triage theo khả năng khai thác, SBOM, admission control) chưa có nguồn chính thức và một grounding URL là repo cộng đồng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | factual | Các ý quy trình (chỉ chặn CVE mới so với baseline, quét lại định kỳ image đang chạy, admission control chỉ cho image đã ký, triage theo khả năng khai thác thay vì chỉ CVSS, SBOM) là thực hành tốt nhưng chưa có câu trích từ nguồn chính thức trong giới hạn fetch. | Thêm grounding URL chính thức cho phần triage/SBOM (ví dụ tài liệu Docker Scout hoặc CISA KEV) để người chấm có căn cứ. |
| minor | format | Một grounding URL là repo cộng đồng (bregman-arie/devops-exercises), không phải nguồn chính thức. | Thay bằng trang chính thức về image scanning/supply chain. |
| minor | length | ~665 token, chỉ phần đo lường và 'Đánh đổi' bị cắt. Ý bắt buộc nằm trước điểm cắt. | Rút mục 5 (dependency của ứng dụng) còn nửa dòng. |

**Kiểm chứng:**
- `supported` Chọn base image nhỏ từ nguồn tin cậy
  > When choosing an image, ensure it's built from a trusted source and keep it small.  
  > — https://docs.docker.com/build/building/best-practices/
- `supported` Multi-stage build để image cuối chỉ chứa thứ cần chạy
  > Multi-stage builds let you reduce the size of your final image  
  > — https://docs.docker.com/build/building/best-practices/
- `supported` Rebuild định kỳ với `--pull` (lấy base mới) và `--no-cache`
  > rebuild your images regularly with updated dependencies  
  > — https://docs.docker.com/build/building/best-practices/
  _Trang giải thích `--pull` "forces Docker to check for and download a newer version of the base image"._
- `supported` Pin digest đồng nghĩa từ chối bản vá tự động, cần bot (Dependabot) mở PR cập nhật
  > And you're opting out of automated security fixes, which is likely something you want to get.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/building/best-practices.md
  _Cùng mục: "Dependabot raises pull requests to update your base image tags and digests on a schedule." Trang HTML bị cắt trước mục này nên dùng file nguồn trong repo docker/docs._
- `supported` Gate trong CI chặn CVE Critical/High đã có bản fix
  > By default, it flags critical and high severity vulnerabilities where a fix version is available.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/scout/policy/_index.md
  _Đây là policy mặc định của Docker Scout, ủng hộ cách gate theo CVE có fix._

**Độ khó:** hard thật · hợp level middle, senior — Đòi hỏi cân bằng giữa an toàn và tốc độ giao hàng, thiết kế chính sách chứ không chỉ chạy scanner.
**Dùng trong phỏng vấn:** ~4 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế quy trình; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết giảm và quản lý lỗ hổng trong container image một cách bền vững, không chặn mù quáng cũng không bỏ mặc.
- Ý bắt buộc: Giảm bề mặt: base nhỏ, tin cậy, multi-stage; Rebuild định kỳ với base mới; pin digest kèm bot cập nhật; Gate trong CI chỉ chặn CVE Critical/High đã có fix (và mới phát sinh); Quét lại image đang chạy vì CVE mới được công bố liên tục; Ngoại lệ có thời hạn, owner, lý do
- Dấu hiệu trả lời sai: Chặn pipeline theo mọi CVE kể cả chưa có fix; Pin digest mà không có cơ chế cập nhật; Chỉ quét lúc build rồi không bao giờ quét lại
- Câu hỏi nối tiếp: Một CVE Critical nằm trong package không được load lúc chạy; bạn ghi nhận và theo dõi ngoại lệ này thế nào?

### de-qa-1216 · Đạt · tin cậy medium · Có thể chấp nhận

**Topic:** CI/CD pipeline (`devops.cicd.pipelines`) · ~737 token · hard của topic: 2

**Câu hỏi:** Team chạy canary 10% traffic cho phiên bản mới của một service, nhưng phiên bản này đổi tên cột `fullname` thành `display_name` trong database dùng chung. Migration chạy trước deploy làm phiên bản cũ (đang nhận 90% traffic) lỗi hàng loạt, và rollback app cũng không cứu được vì schema đã đổi. Bạn thiết kế lại quy trình release để canary và rollback vẫn an toàn khi có thay đổi schema như thế nào?

**Kết luận:** Lời giải expand/contract (parallel change) và việc tách migration thành bước tương thích ngược là đúng và là đáp án chuẩn. Confidence medium vì nguồn chính cho pattern là bliki của Martin Fowler (nguồn thứ cấp) và grounding URL duy nhất của cặp là repo cộng đồng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | format | Grounding URL duy nhất là repo cộng đồng (bregman-arie/devops-exercises), không chứa nội dung về expand/contract. | Thay bằng martinfowler.com/bliki/ParallelChange.html và sre.google/workbook/canarying-releases/. |
| minor | length | ~737 token, cắt giữa ý canary analysis; mất 'build once, promote' và 'Đánh đổi'. Ý bắt buộc (vì sao rollback không cứu được, 6 bước expand/contract, migration tương thích N-1) nằm trước điểm cắt. | Rút đoạn 'Vấn đề' còn 2 câu (bỏ định nghĩa blue-green). |

**Kiểm chứng:**
- `supported` Canary là triển khai một phần, có thời hạn, rồi đánh giá
  > We define canarying as a partial and time-limited deployment of a change in a service and its evaluation.  
  > — https://sre.google/workbook/canarying-releases/
- `supported` Expand/contract (parallel change) tách thay đổi phá vỡ tương thích thành các pha an toàn
  > Parallel change, also known as expand and contract, is a pattern to implement backward-incompatible changes to an interface in a safe manner, by breaking the change into three distinct phases: expand, migrate, and contract.  
  > — https://martinfowler.com/bliki/ParallelChange.html
  _Nguồn thứ cấp (bliki), được trích rộng rãi._
- `supported` Refactor database theo parallel change: có giai đoạn chuyển tiếp giữa schema cũ và mới cho tới khi mọi code truy cập đã cập nhật
  > Most database refactorings follow the parallel change pattern, where the migrate phase is the transition period between the original and the new schema, until all database access code has been updated to work with the new schema.  
  > — https://martinfowler.com/bliki/ParallelChange.html
- `supported` Canary có phân tích tự động: so metric của canary với control, lệch quá thì coi là bad
  > If the error rate of the canary metric is too far from the control error rate, this signals the canary deployment is "bad."  
  > — https://sre.google/workbook/canarying-releases/

**Độ khó:** hard thật · hợp level middle, senior — Kết hợp chiến lược release với thay đổi schema dùng chung; phải lập luận về tương thích giữa các phiên bản chạy song song.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế; 4–5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao canary/rollback giả định hai phiên bản chạy song song, và cách đổi schema mà cả hai phiên bản vẫn chạy được.
- Ý bắt buộc: DB là trạng thái dùng chung; migration phá tương thích làm hỏng bản cũ ngay, rollback app không rollback schema; Expand/contract: thêm cột mới, dual-write, backfill, chuyển đọc, ngừng ghi cũ, xóa cột cũ ở release sau; Mỗi bước tương thích với cả phiên bản trước và sau; Pipeline: migration là stage riêng, test bản N-1 trên schema mới, lint chặn DROP/RENAME; Canary phân tích tự động so với baseline, tự rollback app
- Dấu hiệu trả lời sai: Đề xuất 'chạy migration sau deploy' mà vẫn đổi tên cột một lần; Viết down-migration và tin rằng rollback schema là an toàn với dữ liệu mới; Tắt canary cho release có migration
- Câu hỏi nối tiếp: Backfill trên bảng hàng trăm triệu dòng; bạn làm thế nào để không khóa bảng và không làm lag replica?

### de-qa-1217 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** CI/CD pipeline (`devops.cicd.pipelines`) · ~685 token · hard của topic: 2

**Câu hỏi:** Pipeline CI của một monorepo (nhiều service Node.js, mỗi service build một Docker image) mất khoảng 40 phút cho mỗi PR. Runner là máy tạm (ephemeral) nên lần nào cũng cài lại dependency và build image từ đầu. Bạn tối ưu thế nào mà vẫn giữ build đúng và an toàn?

**Kết luận:** Nội dung đúng và có nguồn (phạm vi cache GitHub Actions, 7 ngày, 10 GB mặc định, cache mode min/max). Cần sửa vì phần 'giữ build đúng và an toàn', vế thứ hai của câu hỏi, nằm sau điểm cắt 600 token nên Planner không thấy.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | ~685 token; điểm cắt rơi ngay đầu mục 'Giữ build đúng và an toàn' (build phải đúng khi cache miss, chống cache poisoning từ PR không tin cậy). Đây là vế thứ hai của câu hỏi nên snippet của Planner thiếu ý bắt buộc. | Đưa mục 'Giữ build đúng và an toàn' lên ngay sau 'Đo trước khi tối ưu', hoặc rút mục 4–5 (song song hóa, build once) còn một dòng. |
| minor | factual | Giới hạn 10 GB nay có thể tăng (admin repo/org/enterprise). Đáp án ghi 'mặc định' nên không sai. | Thêm '(có thể tăng)' sau 10 GB. |

**Kiểm chứng:**
- `supported` Run chỉ restore được cache của branch hiện tại hoặc default branch (PR thêm base branch)
  > Workflow runs can restore caches created in either the current branch or the default branch (usually `main`).  
  > — https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
  _Cùng trang: PR "can also restore caches created in the base branch"._
- `supported` Cache không được truy cập quá 7 ngày bị xóa; giới hạn mặc định 10 GB mỗi repo
  > By default, the limit is 10 GB per repository, but this limit can be increased by enterprise owners, organization owners, or repository administrators.  
  > — https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
  _Cùng trang: "GitHub will remove any cache entries that have not been accessed in over 7 days." Đáp án ghi 'mặc định' nên vẫn đúng; giới hạn nay tăng được._
- `supported` Không lưu thông tin nhạy cảm trong cache
  > We recommend that you don't store any sensitive information, such as access tokens or login credentials,  
  > — https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- `supported` Một layer đổi thì mọi layer sau phải build lại
  > Once a layer changes, then all downstream layers need to be rebuilt as well.  
  > — https://docs.docker.com/build/cache/
- `supported` Cache mode min (mặc định) chỉ cache layer của image cuối; max cache cả stage trung gian; có backend registry và gha
  > In `min` cache mode (the default), only layers that are exported into the resulting image are cached,  
  > — https://docs.docker.com/build/cache/backends/
  _Cùng trang: "in `max` cache mode, all layers are cached, even those of intermediate steps."_

**Độ khó:** hard thật · hợp level middle, senior — Tối ưu CI có ràng buộc đúng đắn và bảo mật (cache poisoning) là mức middle/senior.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Tối ưu + giữ đúng/an toàn; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết tăng tốc CI trên runner tạm bằng build có chọn lọc và cache, mà không đánh đổi tính đúng và an toàn của build.
- Ý bắt buộc: Đo trước, tối ưu stage tốn nhất; Chỉ build/test service bị ảnh hưởng theo đồ thị phụ thuộc; Cache dependency theo hash lockfile; hiểu phạm vi cache theo branch; Sắp xếp Dockerfile (lockfile trước source) + external layer cache (registry/gha); Build phải đúng khi cache miss; cache từ PR không tin cậy không dùng cho build release
- Dấu hiệu trả lời sai: Dùng runner cố định chia sẻ cache cho mọi PR, kể cả từ fork; COPY toàn bộ source trước khi cài dependency; Bỏ bớt test để nhanh hơn
- Câu hỏi nối tiếp: Vì sao PR từ fork có thể đọc cache của base branch, và bạn ngăn cache độc hại đi vào build release thế nào?

**Đề xuất sửa:**
- Đáp án: Đưa mục 'Giữ build đúng và an toàn' (đúng khi cache miss, định kỳ build không cache, chống cache poisoning) lên trước mục 'Song song hóa'; rút 'Song song hóa' và 'Build once, promote' còn một dòng mỗi mục để chunk dưới 600 token.

