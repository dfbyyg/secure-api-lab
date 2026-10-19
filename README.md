# 实验 1: Secure REST API Development with CI/CD and CVE Analysis

## 1. 项目描述与 API 端点
本项目使用 Python/Flask 构建了一个安全的 REST API，并使用 SQLite 作为数据存储。API 包含以下三个端点：
- `POST /auth/login`：用户身份验证端点。接收 JSON 格式的 `username` 和 `password`，校验成功后返回 JWT Token。
- `GET /api/data`：受保护的数据获取端点。必须携带有效的 Bearer Token 才能访问，返回示例数据（包含防 XSS 转义测试）。
- `GET /api/me`：自定义端点。受 JWT 保护，返回当前登录用户的 ID 和用户名信息。

### 测试截图：
<img width="692" height="349" alt="image" src="https://github.com/user-attachments/assets/986f2a19-9ff6-4267-8ba3-38bb4a26f8c0" />

<img width="692" height="378" alt="image" src="https://github.com/user-attachments/assets/eac42362-c30a-4e7c-aad5-6fee861d00d4" />

<img width="692" height="513" alt="image" src="https://github.com/user-attachments/assets/ac71de2e-ac73-40a6-aa41-02203a051f3a" />

<img width="693" height="340" alt="image" src="https://github.com/user-attachments/assets/31f01ffe-be21-4b51-84ae-cf8face6784e" />

<img width="692" height="275" alt="image" src="https://github.com/user-attachments/assets/93e6da35-5fb8-4bdd-99e1-7bb406ae15c9" />


## 2. 安全措施详细说明
- **防护 SQL 注入 (SQLi)**：所有数据库操作均使用参数化查询（Prepared Statements），例如 `c.execute("SELECT * FROM users WHERE username = ?", (username,))`，拒绝直接拼接 SQL 字符串，防止注入攻击。
- **防护 跨站脚本 (XSS)**：在返回用户生成的数据时，使用 `html.escape()` 对所有字符串进行 HTML 实体编码，确保 `<script>` 被转化为 `&lt;script&gt;`，阻止浏览器执行恶意脚本。
- **身份验证安全 (Broken Authentication)**：
  - **密码哈希**：用户密码绝不使用明文存储，而是使用 `bcrypt` 算法加盐哈希后存入数据库。
  - **JWT 认证**：登录成功后签发 JWT Token。受保护接口使用 `@jwt_required()` 中间件进行拦截，无 Token、伪造 Token 或过期 Token 均会被拒绝（返回 401）。

## 3. CI/CD 安全扫描报告
在项目的 `.github/workflows/security.yml` 中配置了 GitHub Actions 自动化安全扫描：
- **SAST (静态应用安全测试)**：配置了 `bandit` 工具扫描代码。修复了最初扫描出的 `debug=True` 高危漏洞，现在流水线已通过。
- **SCA (软件成分分析)**：配置了 `pip-audit` 工具扫描依赖。修复了依赖版本冲突和无版本锁定的问题。
<img width="693" height="486" alt="image" src="https://github.com/user-attachments/assets/1c98dc77-1dc3-4210-bb38-a751349ade78" />


## 4. CVE 漏洞分析与复现 (CVE-2018-1000656)
- **漏洞名称**：Flask 拒绝服务漏洞 (CVE-2018-1000656)
- **漏洞描述**：Flask 0.12.2 及更早版本在解析 JSON 数据时存在输入验证不当的问题。攻击者提供错误编码的 JSON 数据，会导致底层解析器分配极大的内存并崩溃，从而引发拒绝服务（DoS）。
- **复现步骤**：
  1. 编写 Dockerfile 和 `requirements.txt`，锁定安装存在漏洞的 `Flask==0.12.2`。
  2. 启动容器后，使用 `curl` 向服务端发送带有 `\xff\xfe` 错误编码的恶意 POST 请求。
<img width="692" height="429" alt="image" src="https://github.com/user-attachments/assets/8b6dc0af-cc7f-4118-9c26-e6d921812844" />

- **根因分析**：Flask 在处理 HTTP 请求体时，没有对非法编码的边界长度进行合理限制。当解析器遇到不符合规范的 UTF-8 字符流时，分配了失控的内存空间，抛出未处理的异常，导致服务端崩溃（CWE-20 输入验证不当）。
- **修复方案**：将 `requirements.txt` 中的 Flask 版本升级到包含补丁的 `Flask==0.12.3`。该版本严格校验了 JSON 编码格式。

## 5. 修复验证 (Proof of Vulnerability Elimination)
- **验证步骤**：使用修复后的 `Flask==0.12.3` 重新构建并启动 Docker 容器。
- **验证结果**：再次执行与复现阶段完全相同的恶意 `curl` 请求。服务器成功识别并拦截了畸形数据，返回了安全的 `HTTP/1.0 400 BAD REQUEST`。通过 `docker stats` 观察，内存占用稳定在 20MB 左右，未发生飙升，服务保持正常，证明漏洞已被有效修复。
<img width="692" height="636" alt="image" src="https://github.com/user-attachments/assets/a4744d86-e33c-4994-ad91-e562762afb0e" />


## 6. 修复代码文件夹
所有针对漏洞的修复文件（包括修改后的 `Dockerfile`、`docker-compose.yml`、`requirements.txt` 及 `app.py`）均已放置在仓库的 `fix/CVE-2018-1000656/` 目录下。
