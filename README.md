# 接口自动化测试平台 Demo

一个基于 Python / FastAPI / requests / pytest 的轻量接口自动化测试项目。项目包含被测 API 服务、JSON 用例管理、批量执行器、断言引擎、变量提取与注入、HTML/JSON 报告、单元测试和 GitHub Actions CI。

定位：不是完整商业测试平台，而是一个可从 0 讲清楚设计思路、问题排查和工程闭环的微型接口自动化项目。

## 当前运行结果

- `pytest -q`：17 个测试全部通过。
- `python run_tests.py`：接口用例 `11/11` 通过，失败 0，跳过 0，通过率 100%。
- 本地报告：`reports/report.html`、`reports/report.json`。
- 最近一次端到端执行平均接口耗时约 `1.54 ms`。

## 能力点

- 使用 FastAPI 构建被测服务，模拟登录、用户查询、订单查询等接口。
- 使用 JSON 描述测试用例，支持状态码、JSON Path、文本包含、响应时间断言。
- 支持从响应中提取变量，例如从登录接口提取 `data.token`。
- 支持 `${token}`、`${alice_user_id}` 形式的变量注入，串联登录后的鉴权请求。
- 当整个字段就是 `${alice_user_id}` 时保留原始类型，例如 `int` 不会被强制转成字符串。
- 只有断言和变量提取全部通过后，才会把变量写入共享上下文，避免失败用例污染后续链路。
- 覆盖成功路径、错误密码、缺少 token、错误 token、越权访问、缺少参数、请求 schema 错误等场景。
- 对用例文件做 schema 校验，避免空用例、非法断言、缺失 expected/path、错误依赖导致“假通过”。
- 报告默认脱敏，遮盖 token、Authorization、password、邮箱、手机号、身份证号等敏感内容。
- 使用 pytest 覆盖断言逻辑、用例加载、变量替换和鉴权边界。
- 使用 GitHub Actions 在 push / pull request 时自动执行 pytest，并启动 FastAPI 跑端到端 JSON 用例，上传报告 artifact。

## 关键升级

### 1. 修复越权访问漏洞

早期版本只校验 token 是否有效，没有校验 token 所属用户是否等于请求中的 `user_id`。这会导致 Alice 的 token 可以查询 Bob 的资料和订单，属于典型 IDOR / 越权访问问题。

解决方式：

- 在 `/users/{user_id}` 和 `/orders?user_id=` 中增加 subject 校验。
- token 用户和请求用户不一致时返回 `403`，错误码 `1004`。
- 新增 pytest 和 JSON 负向用例，防止后续回归。

### 2. 增加变量提取和依赖链路

接口自动化不能每条用例都写死 token，否则登录接口坏了也可能看起来后续接口正常。当前执行器支持：

```json
"extract": [
  {"name": "token", "path": "data.token"}
]
```

后续用例可以这样使用：

```json
"headers": {"Authorization": "Bearer ${token}"}
```

执行器还有两个工程细节：

- 如果字段完整等于 `${alice_user_id}`，替换结果保留 `int` 类型；如果是 `/users/${alice_user_id}` 这种拼接字符串，则替换为字符串片段。
- 只有当前用例所有断言和提取动作都成功，变量才会进入共享上下文，避免失败登录接口提取出的错误 token 影响后续用例。

### 3. 增加用例校验和 CI

`runner/schema.py` 会校验用例必须包含 `id`、`path`、非空 `assertions`，并校验断言类型是否合法。它还会检查：

- `depends_on` 必须引用前面已经出现过的用例，不能拼错或依赖后面的用例。
- `status_code` 必须有整数 `expected`。
- `json_equals/json_contains` 必须有 `path` 和 `expected`。
- `json_exists` 必须有 `path`。
- `response_time_lt_ms` 必须有正数阈值。

项目还补充了 `.github/workflows/python-tests.yml`，用于在 GitHub 上自动跑 pytest、启动 FastAPI、执行 `run_tests.py`，并上传 HTML/JSON 报告。

### 4. 增加报告脱敏

报告会被发给面试官或保存在 CI artifact 中，因此不能把 token、Authorization、password、邮箱、手机号、身份证号直接写出去。`runner/redaction.py` 会在写入 HTML/JSON 报告前统一脱敏，既保护页面报告，也保护机器可读报告。

## 项目结构

```text
api-auto-test-platform-demo/
  app/
    main.py
  cases/
    api_cases.json
  docs/
    interview_guide.md
  runner/
    assertions.py
    executor.py
    report.py
    schema.py
  tests/
    test_app_auth.py
    test_assertions.py
    test_executor.py
  .github/workflows/
    python-tests.yml
  run_tests.py
  requirements.txt
```

## 快速运行

```powershell
cd D:\PycharmProjects\api-auto-test-platform-demo
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

启动被测服务：

```powershell
uvicorn app.main:app --reload --port 8001
```

另开一个终端执行接口用例：

```powershell
cd D:\PycharmProjects\api-auto-test-platform-demo
python run_tests.py --base-url http://127.0.0.1:8001
```

执行单元测试：

```powershell
pytest -q
```
