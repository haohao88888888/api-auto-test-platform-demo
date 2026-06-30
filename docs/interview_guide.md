# 接口自动化测试平台 Demo 面试讲解稿

## 1. 一句话介绍

这是我从 0 写的一个轻量接口自动化测试项目。它包含一个 FastAPI 被测服务，以及一个 requests 驱动的 JSON 用例执行器，支持变量提取、变量注入、断言校验、HTML/JSON 报告、pytest 单测和 GitHub Actions CI。

## 2. 为什么做这个项目

我想证明自己不只是会用 Postman 点接口，而是理解接口自动化框架的基本组成：

- 用例怎么设计成数据。
- 请求怎么批量执行。
- 登录 token 怎么在用例之间传递。
- 断言失败怎么定位。
- 报告怎么生成。
- 框架自身怎么通过 pytest 和 CI 保证稳定。

## 3. 从 0 实现步骤

1. 先写被测服务 `app/main.py`，提供 `/health`、`/login`、`/users/{user_id}`、`/orders`。
2. 设计 JSON 用例格式，把 method、path、headers、params、json、assertions 都放到 `cases/api_cases.json`。
3. 写执行器 `runner/executor.py`，读取 JSON，用 `requests.Session` 发送请求。
4. 写断言模块 `runner/assertions.py`，支持状态码、JSON Path、文本包含、响应时间。
5. 写报告模块 `runner/report.py`，输出 JSON 和 HTML。
6. 补变量提取和注入：登录成功后提取 `data.token`，后续用例用 `${token}`。
7. 补负向用例：错误密码、缺少 token、错误 token、越权访问、缺少参数、schema 错误。
8. 补 pytest，测试断言逻辑、变量替换、鉴权边界。
9. 补 GitHub Actions，让提交后自动跑单测。

## 4. 核心流程

```text
JSON case file
  -> schema validation
  -> variable substitution
  -> requests.Session sends request
  -> assertions evaluate response
  -> extract variables if all checks pass
  -> collect results
  -> write HTML/JSON report
```

## 5. 关键模块怎么讲

`app/main.py`

被测服务。这里不是为了做业务系统，而是模拟真实接口场景：登录、鉴权、用户查询、订单查询。后来我发现并修复了一个越权访问问题。

`runner/executor.py`

执行器核心。负责读取用例、替换变量、发送请求、调用断言、提取变量、维护依赖关系。

`runner/schema.py`

用例校验。它会拦截空用例、重复 id、非法断言类型等问题，防止生成“看起来正常但实际没测东西”的报告。

`runner/assertions.py`

断言模块。把状态码、JSON Path、文本包含、响应时间做成可复用能力，避免每个用例写重复逻辑。

`runner/report.py`

报告模块。统计 total、passed、failed、skipped、pass_rate、avg_elapsed_ms，并输出 HTML/JSON。

## 6. 我遇到的问题、解决方式和结果

### 问题 1：接口存在越权访问风险

最开始 `/users/{user_id}` 和 `/orders?user_id=` 只判断 token 是否有效，没有判断 token 属于谁。这样 Alice 的 token 可以查 Bob 的资料和订单。

解决方式：

- 增加 token subject 校验。
- 当 token 用户和请求用户不一致时返回 `403` 和错误码 `1004`。
- 增加 JSON 负向用例和 pytest，防止后续改代码时回归。

结果：

- Alice 查 Bob 用户资料返回 403。
- Alice 查 Bob 订单返回 403。
- `pytest -q` 13 个测试通过，端到端用例 11/11 通过。

### 问题 2：token 写死，无法体现真实接口链路

第一版后续接口直接写死 `Bearer demo-token-alice`。这种写法不符合真实自动化，因为登录接口坏了，后续接口仍可能看起来正常。

解决方式：

- 登录用例通过 `extract` 提取 `data.token`。
- 后续用例使用 `Authorization: Bearer ${token}`。
- 用 `depends_on` 表示后续接口依赖登录成功。

结果：

- 用例形成“登录 -> 提取 token -> 访问鉴权接口”的真实链路。
- 登录失败时，依赖用例会跳过或失败，不会假通过。

### 问题 3：失败用例可能污染后续变量

执行器早期会先提取变量并写入全局上下文，然后才判断 checks 是否全部通过。如果断言失败但提取成功，错误变量可能污染后续用例。

解决方式：

- 先收集断言和提取结果。
- 只有全部 checks 通过时，才把 extracted 变量写入共享上下文。
- 增加单元测试验证失败用例不会更新 variables。

结果：

- 变量上下文更可靠，失败链路不会污染后续执行。

### 问题 4：变量替换会把所有值变成字符串

第一版变量替换用 `str(value)`，适合 header 和 URL，但如果以后 JSON body 要传数字或布尔值，会把 `1` 变成 `"1"`。

解决方式：

- 如果字段完整等于 `${user_id}`，保留原始类型。
- 如果是 `/users/${user_id}` 或 `Bearer ${token}` 这种拼接字符串，才转成字符串片段。

结果：

- 查询参数、JSON body、headers 都能兼容。
- 框架扩展性更好。

## 7. 面试追问怎么答

问：为什么不用 Postman？

答：Postman 是成熟工具，但这个项目是为了证明我理解接口自动化内部机制。比如用例数据结构、请求执行、断言、变量提取、报告、CI 这些我都自己实现了一遍。

问：JSON 用例有什么好处？

答：把测试数据和执行逻辑分开。新增接口场景时，只改 JSON，不需要改执行器代码，适合维护批量接口用例。

问：怎么保证用例文件没写错？

答：我加了 `runner/schema.py`，会校验用例非空、id 唯一、path 必填、assertions 非空、断言类型合法。校验失败 CLI 返回 2，和接口断言失败区分开。

问：JSON Path 是怎么做的？

答：我实现了一个轻量 `resolve_json_path`，支持用点号访问字典字段和列表下标，例如 `data.0.title`。

问：失败怎么定位？

答：每个 assertion 都会输出 type、passed、message。报告里能看到期望值、实际值、失败路径、响应时间和错误信息。

问：为什么要有 pytest？

答：接口自动化项目本身也是代码，不能只靠手工跑。pytest 测了断言、变量替换、用例校验和鉴权边界，防止框架自身出错。

问：如果要继续升级，你会做什么？

答：我会加环境配置、重试策略、并发执行、历史趋势、更多断言类型、OpenAPI 自动生成用例，以及把报告接入 CI artifact。

## 8. 你要记住的真实结果

- pytest：13 passed。
- 接口用例：11/11 通过。
- 覆盖场景：登录、鉴权、用户查询、订单查询、越权访问、参数异常、schema 异常。
- 关键亮点：变量提取/注入、越权修复、schema 校验、失败不污染变量、类型保留、CI。
