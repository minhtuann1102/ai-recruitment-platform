# Service Communication

Cách các service giao tiếp, port sử dụng, và cách thêm service mới.

> **Lưu ý:** Tài liệu này đã được cập nhật theo [ADR-003](architecture/adr/adr-003-tcp-rest-transport.md) — chuyển từ gRPC sang **TCP transport** cho NestJS internal, và **REST** cho AI service.

---

## Overview

External traffic (client) đi qua **HTTP**, route bởi Apache APISIX. Internal service-to-service dùng **NestJS TCP transport**. AI service (FastAPI) giao tiếp qua **REST/HTTP**.

```
                 ┌──────────────┐
   client ─────▶ │   APISIX     │  HTTP (JWT auth)
                 └──────┬───────┘
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
┌────────────┐  ┌────────────┐  ┌──────────────┐
│auth-service│  │user-service│  │job-service   │
│ (TCP client)│  │(TCP server)│  │(TCP client)  │
└─────┬──────┘  └─────▲──────┘  └──────┬───────┘
      │  TCP          │               │ TCP
      └───────────────┘               │
      └───────────────────────────────┘

┌───────────────────┐         ┌──────────────────┐
│interview-service  │  REST   │ai-service        │
│(REST client)      │────────▶│(FastAPI mock)     │
└───────────────────┘         └──────────────────┘

┌──────────────────────┐
│notification-service  │
│(TCP server)          │◀── TCP ── auth-service
└──────────────────────┘
```

- **auth-service** — HTTP + TCP *client* của user-service và notification-service. Không có TCP listener.
- **user-service** — HTTP + TCP *server*. Sở hữu User entity.
- **job-service** — HTTP + TCP *client* của user-service. Sở hữu Job, Application entities.
- **interview-service** — HTTP + REST *client* của ai-service. Không dùng TCP.
- **notification-service** — HTTP + TCP *server*. Nhận lệnh gửi email.
- **ai-service** — HTTP only (FastAPI). Không nối TCP transport của NestJS.

---

## Ports

| Service | HTTP | TCP | Env vars |
|---|---|---|---|
| auth-service | 3300 | — (client only) | `AUTH_SERVICE_APP_PORT` |
| user-service | 3301 | **3411** | `USER_SERVICE_APP_PORT`, `TCP_USER_SERVICE_HOST/PORT` |
| job-service | 3302 | — (client only) | `JOB_SERVICE_APP_PORT` |
| interview-service | 3304 | — | `INTERVIEW_SERVICE_APP_PORT` |
| notification-service | 3303 | **3413** | `NOTIFICATION_SERVICE_APP_PORT`, `TCP_NOTIFICATION_SERVICE_HOST/PORT` |
| ai-service | 8000 | — | `AI_SERVICE_PORT` |

> **Lưu ý:** Mỗi env var mới phải thêm vào `globalEnv` trong `turbo.json`.

---

## TCP Transport

### Tổng quan

NestJS TCP transport đơn giản hơn gRPC: không cần `.proto` files, không cần build step, dùng `@MessagePattern()` thay vì `@GrpcMethod()`.

### Server (listener)

Trong `main.ts` của service có TCP server:

```typescript
// apps/user-service/src/main.ts
const app = await NestFactory.create(AppModule);

// TCP microservice listener
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.TCP,
  options: {
    host: configService.get('TCP_USER_SERVICE_HOST', '0.0.0.0'),
    port: configService.get('TCP_USER_SERVICE_PORT', 3411),
  },
});

await app.startAllMicroservices();
await app.listen(configService.get('USER_SERVICE_APP_PORT', 3301));
```

### Handler (server side)

```typescript
// apps/user-service/src/modules/user/user.consumer.ts
@Controller()
export class UserConsumer {
  constructor(private readonly userService: UserService) {}

  @MessagePattern('user.getById')
  async getById(data: { id: string }): Promise<UserResponse> {
    return this.userService.findById(data.id);
  }

  @MessagePattern('user.findByEmail')
  async findByEmail(data: { email: string }): Promise<UserWithPasswordResponse> {
    return this.userService.findByEmail(data.email);
  }

  @MessagePattern('user.create')
  async create(data: CreateUserMessage): Promise<UserResponse> {
    return this.userService.create(data);
  }
}
```

### Client (caller side)

Đăng ký trong module:

```typescript
// apps/auth-service/src/modules/app.module.ts
@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'USER_SERVICE',
        transport: Transport.TCP,
        options: {
          host: process.env.TCP_USER_SERVICE_HOST || '0.0.0.0',
          port: parseInt(process.env.TCP_USER_SERVICE_PORT || '3411'),
        },
      },
    ]),
  ],
})
```

Gọi trong service:

```typescript
// apps/auth-service/src/modules/auth/auth.service.ts
@Injectable()
export class AuthService {
  constructor(
    @Inject('USER_SERVICE') private readonly userClient: ClientProxy,
  ) {}

  async login(dto: LoginRequest) {
    const user = await firstValueFrom(
      this.userClient.send<UserWithPasswordResponse>('user.findByEmail', { email: dto.email }),
    );
    // verify password...
  }
}
```

### Tất cả message patterns

Xem chi tiết request/response tại [api-contracts.md](architecture/api-contracts.md#2-tcp-message-patterns-inter-service).

| Pattern | Server | Client(s) | Mô tả |
|---|---|---|---|
| `user.create` | user-service | auth-service | Tạo user khi sign-up |
| `user.findByEmail` | user-service | auth-service | Tìm user khi login |
| `user.getById` | user-service | job-service, auth-service | Lấy user theo ID |
| `user.getByIds` | user-service | job-service | Batch get users |
| `user.update` | user-service | auth-service | Cập nhật user |
| `notification.sendEmail` | notification-service | auth-service | Gửi email (fire-and-forget) |

---

## REST — AI Service

Interview-service gọi ai-service qua REST/HTTP (không dùng TCP vì FastAPI không nối NestJS TCP).

```typescript
// apps/interview-service/src/modules/ai-client/real-ai-interview-client.ts
@Injectable()
export class RealAiInterviewClient implements AiInterviewClient {
  constructor(private readonly httpService: HttpService) {}

  async evaluateAnswer(req: EvaluateAnswerRequest): Promise<EvaluateAnswerResponse> {
    const { data } = await firstValueFrom(
      this.httpService.post(`${this.aiServiceUrl}/api/evaluate`, req),
    );
    return data;
  }
}
```

Chi tiết OpenAPI contract: [ai-integration.md](architecture/ai-integration.md#4-hop-dong-openapi--ai-service).

---

## Error Handling

Lỗi từ TCP call được xử lý qua `RpcException` và `ExceptionFilter`:

1. Handler throw `RpcException` với payload `{ statusCode, message, errorCode }`
2. Client nhận error qua Observable, parse và throw lại `HttpException` tương ứng
3. Client nên set timeout (default 30s qua `CALL_SERVICE_TIMEOUT`)

```typescript
// Server side — throw error
throw new RpcException({
  statusCode: 404,
  message: 'User not found',
  errorCode: 'NOT_FOUND',
});

// Client side — handle error
try {
  const user = await firstValueFrom(
    this.userClient.send('user.getById', { id }).pipe(
      timeout(30000),
    ),
  );
} catch (error) {
  if (error instanceof RpcException) {
    const detail = error.getError();
    throw new HttpException(detail, detail.statusCode);
  }
  throw new HttpException('Service unavailable', 503);
}
```

---

## Thêm service mới

1. Tạo `apps/new-service/` (copy scaffold)
2. Nếu cần TCP **server**: thêm `app.connectMicroservice()` trong `main.ts`, chọn port chưa dùng
3. Nếu cần TCP **client**: thêm `ClientsModule.register()` trong `app.module.ts`
4. Nếu cần gọi AI service: dùng `HttpModule` + REST
5. Thêm env vars vào `.env.example` và `turbo.json` > `globalEnv`
6. Thêm APISIX route trong `config/apisix/conf/apisix-dev.yaml`
7. Thêm message patterns vào [api-contracts.md](architecture/api-contracts.md)

---

## Related Files

| Concern | Path |
|---|---|
| TCP config | `libs/common/src/config/tcp.config.ts` |
| Microservice factory | `libs/core/src/microservice/` |
| Error handling | `libs/common/src/exceptions/`, `libs/core/src/base/base.service.ts` |
| APISIX config | `config/apisix/conf/apisix-dev.yaml` |
| API contracts | `docs/architecture/api-contracts.md` |
| AI integration | `docs/architecture/ai-integration.md` |
