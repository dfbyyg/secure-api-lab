# 实验 1: Secure REST API Development with CI/CD and Real CVE Vulnerability Analysis

## 1. 项目描述与 API 端点
本项目使用 Python/Flask 构建了一个安全的 REST API，并使用 SQLite 作为数据存储。API 包含以下三个端点：
- `POST /auth/login`：用户身份验证端点。接收 JSON 格式的 `username` 和 `password`，校验成功后返回 JWT Token。
- `GET /api/data`：受保护的数据获取端点。必须携带有效的 Bearer Token 才能访问，返回示例数据（包含防 XSS 转义测试）。
- `GET /api/me`：自定义端点。受 JWT 保护，返回当前登录用户的 ID 和用户名信息。

### API 测试截图：
<img width="692" height="349" alt="image" src="https://github.com/user-attachments/assets/986f2a19-9ff6-4267-8ba3-38bb4a26f8c0" />
<img width="692" height="378" alt="image" src="https://github.com/user-attachments/assets/eac42362-c30a-4e7c-aad5-6fee861d00d4" />
<img width="692" height="513" alt="image" src="https://github.com/user-attachments/assets/ac71de2e-ac73-40a6-aa41-02203a051f3a" />
<img width="693" height="340" alt="image" src="https://github.com/user-attachments/assets/31f01ffe-be21-4b51-84ae-cf8face6784e" />
<img width="692" height="275" alt="image" src="https://github.com/user-attachments/assets/93e6da35-5fb8-4bdd-99e1-7bb406ae15c9" />

## 2. 安全措施详细说明
- **防护 SQL 注入 (SQLi)**：所有数据库操作均使用参数化查询（Prepared Statements），例如 `c.execute("SELECT * FROM users WHERE username = ?", (username,))`，拒绝直接拼接 SQL 字符串，从根本上防止注入攻击。
- **防护 跨站脚本 (XSS)**：在返回用户生成的数据时，使用 `html.escape()` 对所有字符串进行 HTML 实体编码，确保 `<script>` 被转化为 `&lt;script&gt;`，阻止浏览器执行恶意脚本。
- **身份验证安全 (Broken Authentication)**：
  - **密码哈希**：用户密码绝不使用明文存储，而是使用 `bcrypt` 算法加盐哈希后存入数据库。
  - **JWT 认证**：登录成功后签发 JWT Token。受保护接口使用 `@jwt_required()` 中间件进行拦截，无 Token、伪造 Token 或过期 Token 均会被拒绝（返回 401）。

## 3. CI/CD 安全扫描报告
在项目的 `.github/workflows/security.yml` 中配置了 GitHub Actions 自动化安全扫描：
- **SAST (静态应用安全测试)**：配置了 `bandit` 工具扫描代码。修复了最初扫描出的 `debug=True` 高危漏洞，现在流水线已通过。
- **SCA (软件成分分析)**：配置了 `pip-audit` 工具扫描依赖。修复了依赖版本冲突和无版本锁定的问题，流水线已通过。
<img width="693" height="486" alt="image" src="https://github.com/user-attachments/assets/1c98dc77-1dc3-4210-bb38-a751349ade78" />

## 4. CVE 漏洞分析与复现 (CVE-2020-1957)
- **漏洞名称**：Apache Shiro 认证绕过漏洞 (CVE-2020-1957)
- **漏洞描述**：在使用 Spring 动态控制器时，Apache Shiro 1.5.2 之前的版本存在路径解析逻辑不一致的问题。攻击者可以通过构造特殊的恶意请求路径（如带有 `..;`），绕过 Shiro 的认证过滤器，从而未授权访问受保护的系统资源。
- **复现步骤**：
  1. 使用 Docker 启动基于 Shiro 1.5.1 的漏洞环境。
  2. 使用 `curl` 正常访问受保护页面 `/admin/`，结果返回 HTTP 302（重定向至登录页，证明防护存在）。
  3. 使用 `curl` 向 `/xxx/..;/admin/` 发送包含路径遍历字符的恶意请求。
- **复现结果**：恶意请求成功绕过了过滤器，返回了 `HTTP/1.1 200 OK`，并成功获取了受保护的管理员页面内容（Account Info 页面）。

<img width="693" height="230" alt="image" src="https://github.com/user-attachments/assets/62c32660-4348-4f9b-b57d-080b66dbc00b" />
<img width="543" height="545" alt="image" src="https://github.com/user-attachments/assets/c2c70e3d-da2e-452f-b802-9ea820dee9dc" />
<img width="531" height="563" alt="image" src="https://github.com/user-attachments/assets/36478143-04ed-4ab7-9fb2-c2e26ebd8393" />


- **根因分析**：该漏洞属于“路径解析不一致”（CWE-288）。Shiro 的权限过滤器与底层的 Servlet 容器（如 Tomcat/Spring）在解析 URL 路径时使用了不同的算法。攻击者通过注入 `..;`，让 Shiro 认为当前路径是 `/xxx/..`（不在保护范围内），但底层容器却将其规范化为了 `/admin/`，最终导致越权访问。

## 5. 修复方案与验证
- **修复策略**：在真实场景中，直接升级底层 JAR 包常常会面临组件兼容性问题。因此，本实验采用了企业级安全防御方案：在应用前端部署 **Nginx 反向代理（WAF）** 来拦截恶意请求。
- **修复实施**：编写了 `nginx.conf` 配置文件，利用正则表达式严格过滤请求的 URI。任何包含路径遍历字符（`..;`）的请求都会被立即拦截并重定向至登录页，而正常的业务请求则被反向代理到后端的 Shiro 应用。
- **验证结果**：重新构建 Docker 环境后，再次发送完全相同的恶意请求（`/xxx/..;/admin/`）。Nginx 成功拦截了该请求，并返回了 `HTTP/1.1 302 Moved Temporarily`（重定向至 `/login.html`），证明漏洞已被成功缓解/修复。

<img width="530" height="533" alt="image" src="https://github.com/user-attachments/assets/e6ba42de-7228-4f0d-abce-5f00fa611f98" />


## 6. 修复代码文件夹
针对该漏洞的修复文件（包括修改后的 `docker-compose.yml` 和 `nginx.conf`）均已放置在仓库的 `fix/CVE-2020-1957/` 目录下。
