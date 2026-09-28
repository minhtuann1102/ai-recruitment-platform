# Frontend Wireframes & Design Spec

> Tài liệu thiết kế UI cho `apps/web` (Next.js). Frontend dev đọc file này + [api-contracts.md](../architecture/api-contracts.md) là đủ để code.

## 1. Design System

### Tech Stack

| Tool | Mục đích |
|---|---|
| Next.js 14+ (App Router) | Framework |
| TypeScript | Language |
| Tailwind CSS | Styling |
| shadcn/ui | Component library |
| Lucide Icons | Icon set |
| React Hook Form + Zod | Form + validation |
| TanStack Query | Data fetching + cache |
| nuqs | URL search params state |

### Color Palette

```
Primary:    #2563EB (blue-600)    — CTA, links, active states
Secondary:  #0F172A (slate-900)   — headings, strong text
Accent:     #10B981 (emerald-500) — success, positive scores
Warning:    #F59E0B (amber-500)   — warnings, pending status
Danger:     #EF4444 (red-500)     — errors, rejected
Background: #F8FAFC (slate-50)    — page background
Surface:    #FFFFFF               — cards, modals
Border:     #E2E8F0 (slate-200)   — dividers, card borders
Muted:      #64748B (slate-500)   — secondary text
```

### Typography

```
Font:     Inter (Google Fonts)
Heading:  font-semibold
  h1:     text-3xl (30px)   — page titles
  h2:     text-2xl (24px)   — section titles
  h3:     text-lg (18px)    — card titles
Body:     text-sm (14px)     — default
Small:    text-xs (12px)     — labels, meta
```

### Spacing

```
Page padding:     px-6 py-8 (desktop), px-4 py-6 (mobile)
Card padding:     p-6
Gap between cards: gap-4 hoặc gap-6
Sidebar width:    w-64 (256px)
Max content:      max-w-7xl (1280px)
```

### Status Badges

| Status | Color | Dùng cho |
|---|---|---|
| `open` / `active` | green (emerald) | Job status, user active |
| `draft` | gray (slate) | Job draft |
| `closed` | red | Job closed |
| `pending` | yellow (amber) | Application pending |
| `reviewing` | blue | Application reviewing |
| `interview` | purple | Application interview stage |
| `accepted` | green | Application accepted |
| `rejected` | red | Application rejected |
| `in_progress` | blue | Interview session |
| `completed` | green | Interview completed |

---

## 2. Routing Table

### Public (không cần auth)

| URL | Page | API Calls | Component chính |
|---|---|---|---|
| `/` | Landing + Job Search | `GET /job/api/jobs`, `GET /job/api/skills` | Hero, SearchBar, JobCardGrid |
| `/jobs` | Job Listing | `GET /job/api/jobs?...` | SearchBar, FilterSidebar, JobCardGrid, Pagination |
| `/jobs/:id` | Job Detail | `GET /job/api/jobs/:id` | JobDetail, CompanyCard, ApplyButton |
| `/login` | Login | `POST /auth/api/login` | LoginForm |
| `/register` | Register | `POST /auth/api/sign-up` | RegisterForm (role select) |
| `/forgot-password` | Forgot Password | `POST /auth/api/forgot-password` | ForgotPasswordForm |

### Candidate (auth required, role=Candidate)

| URL | Page | API Calls |
|---|---|---|
| `/candidate/dashboard` | Dashboard | `GET /user/api/users/me`, `GET /job/api/applications/my?limit=5`, `GET /interview/api/sessions?limit=5` |
| `/candidate/profile` | Edit Profile | `GET /user/api/candidate-profile`, `POST /user/api/candidate-profile` |
| `/candidate/applications` | My Applications | `GET /job/api/applications/my` |
| `/candidate/saved-jobs` | Saved Jobs | `GET /job/api/saved-jobs` |
| `/candidate/interviews` | Interview History | `GET /interview/api/sessions` |
| `/candidate/interviews/new` | Start Interview | `POST /interview/api/sessions` |
| `/candidate/interviews/:id` | Interview Session | `POST /interview/api/sessions/:id/answer`, `GET /interview/api/sessions/:id` |
| `/candidate/interviews/:id/result` | Interview Result | `GET /interview/api/sessions/:id` |

### Employer (auth required, role=Employer)

| URL | Page | API Calls |
|---|---|---|
| `/employer/dashboard` | Dashboard | `GET /job/api/jobs/my?limit=5`, stats từ các API |
| `/employer/company` | Company Profile | `GET /user/api/company-profile`, `POST /user/api/company-profile` |
| `/employer/jobs` | My Jobs | `GET /job/api/jobs/my` |
| `/employer/jobs/new` | Create Job | `POST /job/api/jobs`, `GET /job/api/skills`, `GET /job/api/experience-levels` |
| `/employer/jobs/:id/edit` | Edit Job | `PUT /job/api/jobs/:id` |
| `/employer/jobs/:id/applicants` | Applicants | `GET /job/api/applications/job/:id` |
| `/employer/applicants/:id` | Applicant Detail | Application data + `GET /interview/api/sessions/candidate/:candidateId` |

### Admin (auth required, role=Admin)

| URL | Page | API Calls |
|---|---|---|
| `/admin/users` | User Management | `GET /user/api/users` |
| `/admin/jobs` | Job Moderation | `GET /job/api/jobs?status=open` |
| `/admin/skills` | Skills Management | `GET /job/api/skills`, `POST /job/api/skills` |
| `/admin/questions` | Question Bank | `GET /interview/api/question-bank` |

---

## 3. Layouts

### 3.1 Public Layout

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
│ ┌─────┐  Home  Jobs  |           [Login] [Register]     │
│ │Logo │                                                 │
│ └─────┘                                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                     MAIN CONTENT                        │
│                     (max-w-7xl)                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ FOOTER                                                  │
│ © 2026 AI Recruitment Platform                          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Authenticated Layout (Candidate/Employer/Admin)

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
│ ┌─────┐  Home  Jobs  |     🔔 Notif  [Avatar ▾ Menu]   │
│ │Logo │                                                 │
│ └─────┘                                                 │
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │                                              │
│ (w-64)   │         MAIN CONTENT                         │
│          │         (flex-1)                              │
│ Dashboard│                                              │
│ Profile  │                                              │
│ Jobs     │                                              │
│ Apps     │                                              │
│ Interview│                                              │
│          │                                              │
│          │                                              │
├──────────┴──────────────────────────────────────────────┤
│ (không có footer trong dashboard)                       │
└─────────────────────────────────────────────────────────┘
```

### Sidebar Items by Role

**Candidate:**
- Dashboard
- Hồ sơ của tôi
- Việc đã ứng tuyển
- Việc đã lưu
- Luyện phỏng vấn
- Lịch sử phỏng vấn

**Employer:**
- Dashboard
- Hồ sơ công ty
- Tin tuyển dụng
- Đăng tin mới

**Admin:**
- Dashboard
- Quản lý người dùng
- Quản lý tin tuyển dụng
- Quản lý kỹ năng
- Ngân hàng câu hỏi

---

## 4. Page Wireframes — Public

### 4.1 Landing Page (/)

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│         Tìm việc IT phù hợp với bạn                     │
│         ~~~~~~~~~~~~~~~~~~~~~~~~                        │
│    ┌────────────────────────────────────┐  ┌────────┐   │
│    │ 🔍  Tìm theo vị trí, kỹ năng...   │  │Tìm kiếm│   │
│    └────────────────────────────────────┘  └────────┘   │
│                                                         │
│    Tags nhanh: [React] [Node.js] [Python] [DevOps]     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Việc làm mới nhất                          [Xem tất cả]│
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ 🏢 FPT       │ │ 🏢 VNG       │ │ 🏢 Tiki      │    │
│  │              │ │              │ │              │    │
│  │ Backend Dev  │ │ React Dev    │ │ DevOps Eng   │    │
│  │ HCM • Remote │ │ HN • Onsite  │ │ HCM • Hybrid │    │
│  │ 15-25tr VND  │ │ 20-35tr VND  │ │ 25-40tr VND  │    │
│  │              │ │              │ │              │    │
│  │ [Node.js]    │ │ [React]      │ │ [AWS]        │    │
│  │ [TypeScript] │ │ [TypeScript] │ │ [Docker]     │    │
│  │     [Lưu ♡]  │ │     [Lưu ♡]  │ │     [Lưu ♡]  │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Thống kê                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  500+    │  │  100+    │  │  50+     │              │
│  │ Việc làm │  │ Công ty  │  │ Kỹ năng  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ FOOTER                                                  │
└─────────────────────────────────────────────────────────┘
```

**Components:** Hero section, SearchBar, SkillTagCloud, JobCardGrid (3 columns), StatsRow

### 4.2 Job Listing (/jobs)

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
├──────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────┐  ┌────────┐   │
│  │ 🔍 Tìm theo vị trí, kỹ năng...      │  │ Tìm    │   │
│  └──────────────────────────────────────┘  └────────┘   │
│                                                         │
├──────────┬──────────────────────────────────────────────┤
│ FILTERS  │ Tìm thấy 245 việc làm          Sắp xếp: [▾] │
│ (w-64)   │                                              │
│          │ ┌────────────────────────────────────────┐   │
│ Kỹ năng  │ │ 🏢 FPT Software                       │   │
│ ☑ React  │ │                                        │   │
│ ☑ Node   │ │ Senior Backend Developer               │   │
│ ☐ Python │ │ HCM • Remote • Senior                  │   │
│ ☐ Java   │ │ 25-40tr VND                            │   │
│ [+Xem thêm]│ │                                        │   │
│          │ │ [Node.js] [TypeScript] [PostgreSQL]    │   │
│ Cấp bậc  │ │                                [Lưu ♡] │   │
│ ○ Intern │ └────────────────────────────────────────┘   │
│ ○ Junior │                                              │
│ ● Senior │ ┌────────────────────────────────────────┐   │
│ ○ Lead   │ │ 🏢 VNG Corporation                     │   │
│          │ │                                        │   │
│ Hình thức│ │ Frontend Developer (React)             │   │
│ ☑ Remote │ │ HN • Onsite • Mid                      │   │
│ ☐ Onsite │ │ 18-28tr VND                            │   │
│ ☑ Hybrid │ │                                        │   │
│          │ │ [React] [Next.js] [Tailwind]           │   │
│ Lương    │ │                                [Lưu ♡] │   │
│ Min [___]│ └────────────────────────────────────────┘   │
│ Max [___]│                                              │
│          │ ┌────────────────────────────────────────┐   │
│ Địa điểm │ │ ...                                    │   │
│ [HCM  ▾] │ └────────────────────────────────────────┘   │
│          │                                              │
│ [Xóa lọc]│  « 1  2  3  4  5 ... 13 »                   │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Components:** SearchBar, FilterSidebar (checkbox groups, range input, select), JobCard (horizontal), Pagination

**API:** `GET /job/api/jobs?keyword=&skills=react,node&experienceLevelId=&location=HCM&workType=remote,hybrid&salaryMin=&page=1&limit=20`

**UX Notes:**
- Filter thay đổi → update URL params → re-fetch (dùng `nuqs`)
- Job card click → navigate to `/jobs/:id`
- Save button toggle → `POST/DELETE /job/api/saved-jobs/:jobId`
- Mobile: filter là slide-over panel

### 4.3 Job Detail (/jobs/:id)

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ← Quay lại                                             │
│                                                         │
│  ┌─────────────────────────────────┐ ┌────────────────┐ │
│  │                                 │ │ 🏢 CÔNG TY     │ │
│  │ Senior Backend Developer        │ │                │ │
│  │ 🏢 FPT Software                 │ │ FPT Software   │ │
│  │                                 │ │ Công nghệ      │ │
│  │ 📍 HCM  •  🏠 Remote  •  Senior │ │ 10,000+ nv    │ │
│  │ 💰 25-40 triệu VND              │ │ fpt.com.vn     │ │
│  │ ⏰ Hạn: 30/11/2026              │ │                │ │
│  │                                 │ │ [Xem công ty]  │ │
│  │ [Ứng tuyển] [Lưu ♡] [Chia sẻ]  │ │                │ │
│  │                                 │ └────────────────┘ │
│  ├─────────────────────────────────┤                    │
│  │ Kỹ năng yêu cầu                 │                    │
│  │ [Node.js] [TypeScript]          │                    │
│  │ [PostgreSQL] [Docker]           │                    │
│  │                                 │                    │
│  │ Mô tả công việc                 │                    │
│  │ ─────────────                   │                    │
│  │ Lorem ipsum dolor sit amet...   │                    │
│  │ • Thiết kế và phát triển API    │                    │
│  │ • Review code và mentor junior  │                    │
│  │ • ...                           │                    │
│  │                                 │                    │
│  │ Yêu cầu                         │                    │
│  │ ────────                        │                    │
│  │ • 3+ năm kinh nghiệm backend    │                    │
│  │ • Thành thạo Node.js/NestJS     │                    │
│  │ • ...                           │                    │
│  └─────────────────────────────────┘                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Khi nhấn "Ứng tuyển" → Modal:**

```
┌──────────────────────────────────┐
│ Ứng tuyển: Senior Backend Dev    │  ✕
├──────────────────────────────────┤
│                                  │
│ Thư giới thiệu (không bắt buộc)  │
│ ┌──────────────────────────────┐ │
│ │                              │ │
│ │ Textarea...                  │ │
│ │                              │ │
│ └──────────────────────────────┘ │
│                                  │
│ CV (bắt buộc, PDF/DOCX, <10MB)   │
│ ┌──────────────────────────────┐ │
│ │  📄 Kéo thả file vào đây    │ │
│ │     hoặc [Chọn file]        │ │
│ └──────────────────────────────┘ │
│                                  │
│          [Hủy]  [Gửi ứng tuyển]  │
└──────────────────────────────────┘
```

### 4.4 Login (/login)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              ┌──────────────────────┐                   │
│              │       🧠 Logo        │                   │
│              │                      │                   │
│              │   Đăng nhập          │                   │
│              │                      │                   │
│              │   Email              │                   │
│              │   ┌────────────────┐ │                   │
│              │   │                │ │                   │
│              │   └────────────────┘ │                   │
│              │                      │                   │
│              │   Mật khẩu           │                   │
│              │   ┌────────────────┐ │                   │
│              │   │            👁  │ │                   │
│              │   └────────────────┘ │                   │
│              │                      │                   │
│              │   [Quên mật khẩu?]   │                   │
│              │                      │                   │
│              │   [  Đăng nhập    ]  │                   │
│              │                      │                   │
│              │   ──── hoặc ────     │                   │
│              │                      │                   │
│              │   Chưa có tài khoản? │                   │
│              │   [Đăng ký ngay]     │                   │
│              └──────────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.5 Register (/register)

```
┌──────────────────────────────────────┐
│           🧠 Logo                    │
│                                      │
│     Tạo tài khoản                    │
│                                      │
│     Bạn là:                          │
│     ┌─────────────┐ ┌─────────────┐ │
│     │ 👤 Ứng viên │ │ 🏢 Nhà TD   │ │
│     │  (selected) │ │             │ │
│     └─────────────┘ └─────────────┘ │
│                                      │
│     Email *                          │
│     ┌──────────────────────────────┐ │
│     │                              │ │
│     └──────────────────────────────┘ │
│                                      │
│     Mật khẩu *                       │
│     ┌──────────────────────────────┐ │
│     │                          👁  │ │
│     └──────────────────────────────┘ │
│     Min 8 ký tự, 1 hoa, 1 số, 1 đc  │
│                                      │
│     Xác nhận mật khẩu *              │
│     ┌──────────────────────────────┐ │
│     │                              │ │
│     └──────────────────────────────┘ │
│                                      │
│     [      Đăng ký        ]          │
│                                      │
│     Đã có tài khoản? [Đăng nhập]     │
└──────────────────────────────────────┘
```

**UX:** Radio card cho role selection. Visual khác nhau giữa Candidate và Employer.

---

## 5. Page Wireframes — Candidate

### 5.1 Candidate Dashboard

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │  Xin chào, Nguyen Van A 👋                   │
│ ● Dashboard                                             │
│   Hồ sơ  │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│   Ứng tuyển│  │    3     │ │    12    │ │   2      │     │
│   Đã lưu │  │ Đang chờ  │ │ Đã ứng   │ │ Phỏng vấn│     │
│   Phỏng vấn│  │ phản hồi  │ │ tuyển    │ │ đã làm   │     │
│          │  └──────────┘ └──────────┘ └──────────┘     │
│          │                                              │
│          │  Ứng tuyển gần đây                           │
│          │  ┌───────────────────────────────────────┐   │
│          │  │ Backend Dev • FPT    │ Pending │ 2d ago│   │
│          │  │ React Dev • VNG     │ Review  │ 5d ago│   │
│          │  │ DevOps • Tiki       │ Rejected│ 1w ago│   │
│          │  └───────────────────────────────────────┘   │
│          │  [Xem tất cả →]                              │
│          │                                              │
│          │  Phỏng vấn gần đây                           │
│          │  ┌───────────────────────────────────────┐   │
│          │  │ Backend • Medium │ 7.5/10 │ Completed │   │
│          │  │ Frontend • Easy  │ 8.2/10 │ Completed │   │
│          │  └───────────────────────────────────────┘   │
│          │  [Luyện phỏng vấn mới →]                     │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Components:** StatCards (3), RecentApplicationsTable, RecentInterviewsTable

### 5.2 My Applications (/candidate/applications)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │ Việc đã ứng tuyển                             │
│          │                                              │
│          │ [Tất cả ▾] [Sắp xếp: Mới nhất ▾]            │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ 🏢 FPT Software                       │   │
│          │ │ Senior Backend Developer               │   │
│          │ │ Ứng tuyển: 26/09/2026                  │   │
│          │ │                                        │   │
│          │ │ Trạng thái: [🟡 Pending]               │   │
│          │ │                                        │   │
│          │ │ [Xem chi tiết] [Rút ứng tuyển]         │   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ 🏢 VNG Corporation                     │   │
│          │ │ React Developer                        │   │
│          │ │ Ứng tuyển: 20/09/2026                  │   │
│          │ │                                        │   │
│          │ │ Trạng thái: [🔵 Reviewing]             │   │
│          │ │                                        │   │
│          │ │ [Xem chi tiết]                         │   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
│          │  « 1  2  3 »                                 │
└──────────┴──────────────────────────────────────────────┘
```

### 5.3 Interview Practice — Start (/candidate/interviews/new)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │  Bắt đầu phỏng vấn luyện tập                  │
│          │                                              │
│          │  ┌──────────────────────────────────────┐    │
│          │  │                                      │    │
│          │  │  Chọn lĩnh vực:                      │    │
│          │  │  ┌──────────┐ ┌──────────┐ ┌──────┐ │    │
│          │  │  │ Backend  │ │ Frontend │ │System│ │    │
│          │  │  │(selected)│ │          │ │Design│ │    │
│          │  │  └──────────┘ └──────────┘ └──────┘ │    │
│          │  │  ┌──────────┐ ┌──────────┐          │    │
│          │  │  │ Database │ │  DevOps  │          │    │
│          │  │  └──────────┘ └──────────┘          │    │
│          │  │                                      │    │
│          │  │  Chọn độ khó:                        │    │
│          │  │  ○ Dễ (Easy)                         │    │
│          │  │  ● Trung bình (Medium)               │    │
│          │  │  ○ Khó (Hard)                        │    │
│          │  │                                      │    │
│          │  │  Liên kết với tin tuyển dụng (tùy chọn)│   │
│          │  │  [Chọn job ▾]                        │    │
│          │  │                                      │    │
│          │  │           [Bắt đầu phỏng vấn →]       │    │
│          │  │                                      │    │
│          │  └──────────────────────────────────────┘    │
│          │                                              │
│          │  💡 Mẹo: AI sẽ hỏi 5-10 câu hỏi, điểm theo  │
│          │  4 tiêu chí. Kết quả là tín hiệu tham khảo   │
│          │  cho nhà tuyển dụng.                         │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 5.4 Interview Session — Q&A (/candidate/interviews/:id)

```
┌──────────────────────────────────────────────────────────┐
│ ← Quay lại          Phỏng vấn #12          Câu 3/10     │
│                      Backend • Medium       ⏱ 12:34      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ LỊCH SỬ ────────────────────────────────────────┐   │
│  │                                                    │   │
│  │  🤖 Câu 1: HTTP methods nào bạn biết? Giải thích  │   │
│  │     công dụng của từng method.                     │   │
│  │                                                    │   │
│  │  👤 GET để lấy data, POST để tạo mới, PUT để cập   │   │
│  │     nhật toàn bộ, PATCH để cập nhật 1 phần,        │   │
│  │     DELETE để xóa...                               │   │
│  │                                                    │   │
│  │  📊 Điểm: KT 8.0 | LQ 9.0 | DD 7.0 | MR 6.0     │   │
│  │  ──────────────────────────────────────────────    │   │
│  │                                                    │   │
│  │  🤖 Câu 2: Giải thích REST và GraphQL khác nhau    │   │
│  │     thế nào? Khi nào nên dùng cái nào?             │   │
│  │                                                    │   │
│  │  👤 REST dùng HTTP methods, mỗi endpoint là 1      │   │
│  │     resource. GraphQL có 1 endpoint, client query   │   │
│  │     chính xác data cần...                          │   │
│  │                                                    │   │
│  │  📊 Điểm: KT 7.5 | LQ 8.0 | DD 6.5 | MR 7.0     │   │
│  │  ──────────────────────────────────────────────    │   │
│  │                                                    │   │
│  │  🤖 Câu 3: Bạn đã nói về REST endpoints. Vậy làm   │   │
│  │     sao để thiết kế API versioning tốt?             │   │
│  │     [Agent: đào sâu hơn về API design]              │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Câu trả lời của bạn...                             │   │
│  │                                                    │   │
│  │                                                    │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│               [Kết thúc phỏng vấn]  [Gửi trả lời →]      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**UX Notes:**
- Chat-style layout: AI hỏi (trái, icon 🤖), Candidate trả lời (phải, icon 👤)
- Sau mỗi trả lời: hiện scores bar chart nhỏ (4 tiêu chí)
- Agent decision hiện như tag nhỏ: `[đào sâu]` / `[chuyển chủ đề]` / `[giữ độ khó]`
- "Gửi trả lời" → loading spinner → hiện scores → hiện câu tiếp
- "Kết thúc" → navigate to result page
- Progress bar trên cùng: câu X/10

**Viết tắt điểm:** KT = Kỹ thuật, LQ = Liên quan, DD = Đầy đủ, MR = Mở rộng

### 5.5 Interview Result (/candidate/interviews/:id/result)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │  Kết quả phỏng vấn #12                       │
│          │  Backend • Medium • 10 câu • 25 phút          │
│          │                                              │
│          │  ┌──────────────────────┐ ┌───────────────┐  │
│          │  │                      │ │  Điểm tổng:   │  │
│          │  │   BIỂU ĐỒ RADAR      │ │               │  │
│          │  │   4 tiêu chí         │ │   7.3 / 10    │  │
│          │  │                      │ │               │  │
│          │  │  KT: ████████░░ 8.0  │ │  ⭐⭐⭐⭐      │  │
│          │  │  LQ: ████████░░ 8.2  │ │               │  │
│          │  │  DD: ██████░░░░ 6.5  │ │               │  │
│          │  │  MR: ██████░░░░ 6.5  │ └───────────────┘  │
│          │  │                      │                    │
│          │  └──────────────────────┘                    │
│          │                                              │
│          │  ✅ Điểm mạnh                                │
│          │  • Hiểu biết tốt về REST API và HTTP         │
│          │  • Giải thích rõ ràng, có ví dụ cụ thể       │
│          │                                              │
│          │  📈 Cần cải thiện                            │
│          │  • Chưa đề cập đến API versioning strategy   │
│          │  • Thiếu kiến thức về caching và rate limit  │
│          │                                              │
│          │  [Xem chi tiết từng câu]  [Luyện lại →]      │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Components:** RadarChart (4 criteria), ScoreBar, StrengthsList, ImprovementsList

---

## 6. Page Wireframes — Employer

### 6.1 Employer Dashboard

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │  Dashboard                      [+ Đăng tin] │
│          │                                              │
│          │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│          │  │    5     │ │    23    │ │    8     │     │
│          │  │ Tin đăng │ │ Hồ sơ   │ │ Chờ      │     │
│          │  │ tuyển    │ │ nhận được│ │ phản hồi │     │
│          │  └──────────┘ └──────────┘ └──────────┘     │
│          │                                              │
│          │  Tin tuyển dụng                              │
│          │  ┌──────────────────────────────────────┐    │
│          │  │ Job Title          │ Ứng viên│ Status │    │
│          │  │─────────────────────────────────────│    │
│          │  │ Backend Developer  │    12   │ 🟢Open │    │
│          │  │ React Developer    │     8   │ 🟢Open │    │
│          │  │ DevOps Engineer    │     3   │ ⚪Draft│    │
│          │  └──────────────────────────────────────┘    │
│          │  [Xem tất cả →]                              │
│          │                                              │
│          │  Hồ sơ mới nhất                              │
│          │  ┌──────────────────────────────────────┐    │
│          │  │ Nguyen A  │ Backend Dev │ 🟡 Pending │    │
│          │  │ Tran B    │ React Dev   │ 🟡 Pending │    │
│          │  │ Le C      │ Backend Dev │ 🔵 Review  │    │
│          │  └──────────────────────────────────────┘    │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 6.2 Create/Edit Job (/employer/jobs/new)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │  Đăng tin tuyển dụng mới                      │
│          │                                              │
│          │  Tiêu đề *                                    │
│          │  ┌──────────────────────────────────────┐    │
│          │  │ VD: Senior Backend Developer          │    │
│          │  └──────────────────────────────────────┘    │
│          │                                              │
│          │  Mô tả công việc *              [Markdown]    │
│          │  ┌──────────────────────────────────────┐    │
│          │  │                                      │    │
│          │  │  Rich text editor / textarea         │    │
│          │  │                                      │    │
│          │  └──────────────────────────────────────┘    │
│          │                                              │
│          │  Yêu cầu                                     │
│          │  ┌──────────────────────────────────────┐    │
│          │  │  Textarea                            │    │
│          │  └──────────────────────────────────────┘    │
│          │                                              │
│          │  ┌─────────────────┐ ┌─────────────────┐    │
│          │  │ Kỹ năng *       │ │ Cấp bậc *       │    │
│          │  │ [React      ✕] │ │ [Senior    ▾]   │    │
│          │  │ [Node.js    ✕] │ │                 │    │
│          │  │ [+ Thêm     ▾] │ └─────────────────┘    │
│          │  └─────────────────┘                        │
│          │                                              │
│          │  ┌─────────────────┐ ┌─────────────────┐    │
│          │  │ Lương min       │ │ Lương max       │    │
│          │  │ [15,000,000   ] │ │ [25,000,000   ] │    │
│          │  └─────────────────┘ └─────────────────┘    │
│          │  Đơn vị: [VND ▾]                             │
│          │                                              │
│          │  ┌─────────────────┐ ┌─────────────────┐    │
│          │  │ Địa điểm        │ │ Hình thức       │    │
│          │  │ [HCM         ▾] │ │ [Remote      ▾] │    │
│          │  └─────────────────┘ └─────────────────┘    │
│          │                                              │
│          │  Hạn nộp: [📅 30/11/2026]                    │
│          │                                              │
│          │     [Lưu nháp]  [Đăng tin →]                 │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 6.3 Applicants List (/employer/jobs/:id/applicants)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │ Ứng viên — Senior Backend Developer           │
│          │ 12 hồ sơ  [Tất cả ▾]                         │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ ┌────┐                                 │   │
│          │ │ │ AV │ Nguyen Van A                    │   │
│          │ │ └────┘ 3 năm KN • Backend Developer    │   │
│          │ │        [Node.js] [TypeScript] [Postgres]│   │
│          │ │                                        │   │
│          │ │  📄 CV  │  🎤 Phỏng vấn: 7.5/10        │   │
│          │ │                                        │   │
│          │ │  Trạng thái: [🟡 Pending ▾]            │   │
│          │ │                    ┌──────────────┐    │   │
│          │ │                    │ Pending      │    │   │
│          │ │                    │ Reviewing  ✓ │    │   │
│          │ │                    │ Interview    │    │   │
│          │ │                    │ Accepted     │    │   │
│          │ │                    │ Rejected     │    │   │
│          │ │                    └──────────────┘    │   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ ┌────┐                                 │   │
│          │ │ │ AV │ Tran Thi B                     │   │
│          │ │ └────┘ 1 năm KN • Frontend Developer   │   │
│          │ │        [React] [JavaScript]            │   │
│          │ │                                        │   │
│          │ │  📄 CV  │  🎤 Chưa phỏng vấn           │   │
│          │ │                                        │   │
│          │ │  Trạng thái: [🟡 Pending ▾]            │   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**UX Notes:**
- Click vào tên ứng viên → xem chi tiết profile + CV + kết quả phỏng vấn
- Dropdown đổi trạng thái trực tiếp trên card
- "Phỏng vấn: 7.5/10" — link tới kết quả phỏng vấn của ứng viên
- Filter theo status

---

## 7. Page Wireframes — Admin

### 7.1 User Management (/admin/users)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │ Quản lý người dùng                            │
│          │                                              │
│          │ ┌────────────────────┐  [Role ▾] [Status ▾]  │
│          │ │ 🔍 Tìm email, tên  │                       │
│          │ └────────────────────┘                       │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ Email       │ Ten    │ Role   │ Status │   │
│          │ │─────────────────────────────────────── │   │
│          │ │ a@test.com  │ Ng. A  │ Cand.  │ 🟢 Act │   │
│          │ │ b@test.com  │ Tr. B  │ Emp.   │ 🟢 Act │   │
│          │ │ c@test.com  │ Le C   │ Cand.  │ 🔴 Deact│   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
│          │  « 1  2  3 ... 10 »                          │
└──────────┴──────────────────────────────────────────────┘
```

### 7.2 Question Bank (/admin/questions)

```
┌──────────┬──────────────────────────────────────────────┐
│ SIDEBAR  │                                              │
│          │ Ngân hàng câu hỏi               [+ Thêm câu] │
│          │                                              │
│          │ [Category ▾] [Difficulty ▾] [🔍 Tìm kiếm   ] │
│          │                                              │
│          │ ┌────────────────────────────────────────┐   │
│          │ │ Category │ Câu hỏi (rút gọn) │ Diff.  │   │
│          │ │───────────────────────────────────────  │   │
│          │ │ Backend  │ HTTP methods nào.. │ Medium │   │
│          │ │ Backend  │ REST và GraphQL..  │ Medium │   │
│          │ │ Frontend │ Virtual DOM là gì..│ Easy   │   │
│          │ │ Database │ Index trong SQL..  │ Hard   │   │
│          │ │ DevOps   │ Docker và VM..     │ Easy   │   │
│          │ └────────────────────────────────────────┘   │
│          │                                              │
│          │  Click row → modal edit:                      │
│          │  ┌──────────────────────────────────┐        │
│          │  │ Sửa câu hỏi                    ✕ │        │
│          │  │                                  │        │
│          │  │ Category: [Backend ▾]            │        │
│          │  │ Subcategory: [Node.js ▾]         │        │
│          │  │ Difficulty: ○E ●M ○H             │        │
│          │  │ Câu hỏi:                         │        │
│          │  │ ┌──────────────────────────────┐ │        │
│          │  │ │ Giải thích HTTP methods...   │ │        │
│          │  │ └──────────────────────────────┘ │        │
│          │  │ Expected topics:                 │        │
│          │  │ [GET] [POST] [PUT] [+ Thêm]      │        │
│          │  │                                  │        │
│          │  │        [Xóa]  [Hủy]  [Lưu]       │        │
│          │  └──────────────────────────────────┘        │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

---

## 8. Responsive Breakpoints

| Breakpoint | Width | Layout |
|---|---|---|
| Mobile | < 768px | Sidebar ẩn, hamburger menu. Job cards 1 column. Filter là slide-over |
| Tablet | 768-1024px | Sidebar collapse (icons only). Job cards 2 columns |
| Desktop | > 1024px | Full sidebar. Job cards tuỳ page (grid 3 hoặc list) |

**Mobile-first:** Ưu tiên mobile layout cho Candidate (tìm việc trên điện thoại). Employer/Admin có thể chỉ support desktop.

---

## 9. Component Inventory (shadcn/ui)

| Component | shadcn/ui | Dùng tại |
|---|---|---|
| Button | `Button` | CTA, submit, actions |
| Input | `Input` | Form fields |
| Textarea | `Textarea` | Mô tả, trả lời phỏng vấn |
| Select | `Select` | Dropdowns (role, status, category) |
| Badge | `Badge` | Status tags, skill tags |
| Card | `Card` | Job cards, stat cards |
| Dialog | `Dialog` | Apply modal, edit modal |
| Table | `Table` | Admin lists, applicant lists |
| Tabs | `Tabs` | Dashboard sections |
| Avatar | `Avatar` | User profile |
| DropdownMenu | `DropdownMenu` | User menu, status change |
| Command | `Command` | Skill search/select (multi) |
| Pagination | `Pagination` | List pagination |
| Skeleton | `Skeleton` | Loading states |
| Toast | `Toast` (sonner) | Success/error notifications |
| Sheet | `Sheet` | Mobile sidebar, filter panel |
| Progress | `Progress` | Interview progress bar |

---

## 10. State Management

```
TanStack Query (server state)
├── useJobs(filters)           → GET /job/api/jobs
├── useJob(id)                 → GET /job/api/jobs/:id
├── useMyApplications()        → GET /job/api/applications/my
├── useSavedJobs()             → GET /job/api/saved-jobs
├── useInterviewSessions()     → GET /interview/api/sessions
├── useInterviewSession(id)    → GET /interview/api/sessions/:id
├── useQuestionBank(filters)   → GET /interview/api/question-bank
└── useMe()                    → GET /user/api/users/me

Mutations
├── useLogin()                 → POST /auth/api/login
├── useRegister()              → POST /auth/api/sign-up
├── useCreateJob()             → POST /job/api/jobs
├── useApply()                 → POST /job/api/applications
├── useToggleSaveJob()         → POST/DELETE /job/api/saved-jobs/:id
├── useSubmitAnswer()          → POST /interview/api/sessions/:id/answer
├── useStartInterview()        → POST /interview/api/sessions
└── useUpdateApplicationStatus() → PATCH /job/api/applications/:id/status

Context (client state)
├── AuthContext                → user, tokens, login(), logout()
└── SidebarContext             → isOpen, toggle()
```
