# 接口自动化测试平台 Demo 面试讲解稿

## 1. 一句话介绍

这是我从 0 写的一个轻量接口自动化测试项目。它包含一个 FastAPI 被测服务，以及一个 requests 驱动的 JSON 用例执行器，支持用例 schema 校验、变量提取、变量注入、依赖控制、状态码/JSON Path/响应时间断言、HTML/JSON 脱敏报告、pytest 单测和 GitHub Actions 端到端 CI。

面试时不要说它是完整测试平台。更准确的说法是：这是一个可展示、可追问、可跑通的小型接口自动化工程项目。

## 2. 为什么做这个项目

我做这个项目是为了证明自己不只是会用 Postman 点接口，而是理解接口自动化框架的内部机制：

- 被测服务怎么模拟。
- 用例怎么设计成结构化数据。
- 请求怎么批量执行。
- 登录 token 怎么在用例之间传递。
- 断言失败怎么定位。
- 报告怎么生成和脱敏。
- 框架自身怎么通过 pytest 和 CI 保证稳定。

## 3. 从 0 实现步骤

1. 先写 `app/main.py`，用 FastAPI 模拟 `/health`、`/login`、`/users/{user_id}`、`/orders`。
2. 设计 `cases/api_cases.json`，把 method、path、headers、params、json、assertions、extract、depends_on 都配置化。
3. 写 `runner/assertions.py`，实现状态码、JSON Path、文本包含、响应时间断言。
4. 写 `runner/schema.py`，在执行前校验用例格式，避免空用例、错误断言、拼错依赖导致假通过。
5. 写 `runner/executor.py`，用 `requests.Session` 批量执行用例，处理变量替换、依赖关系和变量提取。
6. 写 `runner/report.py`，统计执行结果并输出 HTML/JSON 报告。
7. 写 `runner/redaction.py`，报告写入前统一遮盖 token、Authorization、password、邮箱、手机号、身份证号。
8. 补 pytest，覆盖断言逻辑、变量替换、schema 校验、鉴权边界、报告脱敏。
9. 补 GitHub Actions，自动跑 pytest，启动 FastAPI，执行 `run_tests.py`，上传报告 artifact。

## 4. 核心执行流程

```text
api_cases.json
  -> validate_cases()
  -> dependency check
  -> variable substitution
  -> requests.Session sends request
  -> assertion checks
  -> extract variables
  -> commit variables only when all checks pass
  -> redact report data
  -> write HTML/JSON reports
```

## 5. 关键模块怎么讲

`app/main.py`

被测服务。它不是业务系统，而是为了模拟接口测试常见场景：登录、鉴权、用户查询、订单查询、参数校验和越权访问。

`runner/schema.py`

用例校验层。它会校验：

- 用例不能为空。
- `id` 必须唯一。
- `path` 必填。
- `depends_on` 必须引用前面已经出现过的用例。
- `status_code` 必须有整数 `expected`。
- `json_equals/json_contains` 必须有 `path` 和 `expected`。
- `json_exists` 必须有 `path`。
- `response_time_lt_ms` 必须有正数阈值。

`runner/executor.py`

执行器核心。它负责加载用例、替换变量、发送 HTTP 请求、执行断言、提取变量、维护上下文和依赖关系。

`runner/assertions.py`

断言模块。把状态码、JSON Path、文本包含、响应时间这些能力做成可复用函数。

`runner/redaction.py`

报告脱敏模块。报告可能被上传到 CI artifact 或发给面试官，所以不能保留 token、手机号、邮箱等敏感内容。

`runner/report.py`

报告模块。统计 total、passed、failed、skipped、pass_rate、avg_elapsed_ms，并输出 HTML/JSON。

## 6. 遇到的问题、解决方式和结果

### 问题 1：接口存在越权访问风险

第一版 `/users/{user_id}` 和 `/orders?user_id=` 只校验 token 是否有效，没有校验 token 属于哪个用户。这样 Alice 的 token 可以查 Bob 的用户资料和订单。

解决方式：

- 增加 token subject 校验。
- token 用户和请求用户不一致时返回 `403`，错误码 `1004`。
- 新增越权负向用例和 pytest 回归测试。

结果：

- Alice 查 Bob 用户资料返回 403。
- Alice 查 Bob 订单返回 403。
- 端到端接口用例 11/11 通过。

### 问题 2：token 写死，接口链路不真实

早期后续接口直接写 `Bearer demo-token-alice`。这样登录接口坏了，后续接口仍然可能通过，不符合真实接口自动化。

解决方式：

- 登录用例通过 `extract` 提取 `data.token`。
- 后续用例用 `Authorization: Bearer ${token}`。
- 通过 `depends_on` 表示后续接口依赖登录成功。

结果：

- 用例形成“登录 -> 提取 token -> 鉴权接口”的真实链路。
- 登录失败时后续依赖用例不会假通过。

### 问题 3：失败用例可能污染后续变量

第一版执行器会先提取变量并更新全局上下文，然后才判断所有 checks 是否通过。如果断言失败但提取成功，错误变量可能污染后续用例。

解决方式：

- 先收集断言和提取结果。
- 只有全部 checks 通过时，才把 extracted 变量写入共享上下文。
- 增加单元测试验证失败用例不会更新 variables。

结果：

- 失败链路不会污染后续执行。
- 执行器行为更接近工业测试框架。

### 问题 4：变量替换会把所有值转成字符串

第一版变量替换用 `str(value)`，适合 header 和 URL，但如果 JSON body 里要传数字或布尔值，会把 `1` 变成 `"1"`。

解决方式：

- 如果字段完整等于 `${user_id}`，保留原始类型。
- 如果是 `/users/${user_id}` 或 `Bearer ${token}` 这种拼接字符串，才转成字符串片段。

结果：

- 查询参数、JSON body、headers 都能兼容。
- 后续扩展请求体场景更稳。

### 问题 5：报告可能泄露敏感内容

接口报告里可能出现 token、Authorization、手机号、邮箱等内容。如果报告作为 CI artifact 或面试材料传出去，这是质量工程里的审查风险。

解决方式：

- 新增 `runner/redaction.py`。
- 写入 HTML/JSON 报告前递归脱敏。
- 对 token/password/Authorization 这类 key 的值直接遮盖。
- 对邮箱、手机号、身份证号、Bearer token 做正则遮盖。

结果：

- HTML 和 JSON 报告都不再保留敏感明文。
- 用 `rg` 检查报告目录，没有搜到 demo token、邮箱和手机号。

### 问题 6：CI 只跑 pytest，不证明端到端链路可用

早期 GitHub Actions 只跑 `pytest -q`。这只能证明单测通过，不能证明 FastAPI 被测服务、JSON runner 和报告生成整条链路能跑。

解决方式：

- CI 中启动 `uvicorn app.main:app`。
- 等待 `/health` ready。
- 执行 `python run_tests.py --base-url http://127.0.0.1:8001`。
- 上传 `reports/report.html`、`reports/report.json` 和 `uvicorn.log`。

结果：

- CI 能验证“被测服务 + JSON 用例执行器 + 报告”完整链路。

## 7. 面试追问怎么答

问：为什么不用 Postman？

答：Postman 是成熟工具，但这个项目是为了证明我理解接口自动化内部机制。我自己实现了用例结构、请求执行、断言、变量提取、报告、脱敏和 CI。

问：JSON 用例有什么好处？

答：它把测试数据和执行逻辑分开。新增接口场景时，主要改 JSON，不需要改执行器代码。

问：怎么保证用例文件没写错？

答：我做了 schema 校验。比如断言类型是否合法、`status_code` 有没有 expected、`json_equals` 有没有 path/expected、depends_on 是否引用已存在且在前面的 case。

问：JSON Path 怎么实现？

答：我写了一个轻量 `resolve_json_path`，支持用点号访问 dict 字段和 list 下标，例如 `data.0.title`。

问：变量怎么提取和注入？

答：登录成功后通过 `extract` 从响应 JSON 里取 `data.token`，存到上下文；后续用例通过 `${token}` 替换。只有当前用例所有断言和提取都通过，变量才会写入上下文。

问：为什么报告要脱敏？

答：报告可能会被上传到 CI 或发给别人。如果保留 token、Authorization、手机号、邮箱，就是安全风险。所以我在报告写入前做统一 redaction。

问：失败怎么定位？

答：每个 assertion 都记录 type、passed、message。报告里可以看到失败路径、期望值、实际值、响应时间和错误信息。

问：如果继续升级，你会做什么？

答：我会加环境配置、重试策略、并发执行、OpenAPI 自动生成用例、历史趋势、更多断言类型和报告对比。

## 8. 真实结果

- pytest：17 passed。
- 端到端接口用例：11/11 passed。
- 最近一次平均接口耗时：约 1.54 ms。
- 覆盖场景：登录、鉴权、用户查询、订单查询、越权访问、参数异常、schema 异常。
- 关键亮点：越权修复、变量提取/注入、依赖校验、失败不污染变量、类型保留、报告脱敏、端到端 CI。
