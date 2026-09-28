# ADR-003: TCP cho NestJS internal, REST cho AI service

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted

## Bối cảnh

Starter repo sử dụng **gRPC** cho giao tiếp nội bộ (auth → user, auth → notification). gRPC yêu cầu `.proto` files, build step copy proto, và runtime proto resolution — phức tạp cho team 3 người trong đồ án tốt nghiệp.

AI service tương lai là **Python FastAPI**, không nối gRPC transport của NestJS.

## Quyết định

1. **NestJS ↔ NestJS:** chuyển từ gRPC sang **NestJS TCP transport**
2. **NestJS ↔ AI service:** giao tiếp qua **REST** (HTTP)
3. gRPC là hướng nâng cấp sau (stretch goal)

## Lý do

### TCP thay gRPC (NestJS internal)

| Tiêu chí | TCP | gRPC |
|---|---|---|
| Setup | Zero config, NestJS-native | Cần .proto, loader, build step |
| Contract | TypeScript interface | .proto + generated types |
| Performance | Đủ nhanh cho đồ án | Nhanh hơn ~10-20% |
| Learning curve | Thấp | Trung bình-cao |
| Maintenance | Không cần sync proto | Proto drift risk |

Với team 3 người và 3 tháng, **tốc độ iteration** quan trọng hơn performance tuyệt đối. TypeScript interfaces vẫn đảm bảo type safety ở compile time.

### REST cho AI service

- FastAPI nói REST tự nhiên (OpenAPI auto-generated)
- Không cần gRPC Python stub, reduce complexity
- Debug dễ dàng bằng curl/Postman
- Upgrade lên gRPC sau nếu cần, chỉ đổi transport layer

## Hệ quả

- Xóa thư mục `libs/common/src/grpc/proto/`
- Đổi `@GrpcMethod()` sang `@MessagePattern()`
- Đổi client từ gRPC stub sang `ClientProxy` với TCP transport
- `interview-service` expose REST endpoint gọi `ai-service` qua `HttpModule`
- Update `libs/core/src/microservice/` factory cho TCP default
