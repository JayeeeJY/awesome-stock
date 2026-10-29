# 验证与验收说明

适用：Community v1.1.0；沿用 v1.0.x 的原生安装范围；更新 2026-10-29。实际公开版本、提交和发布日期见 [GitHub Releases](https://github.com/JayeeeJY/awesome-stock/releases)。本文说明验证口径，不替代发行授权或安全认证。

## 正式首发标准

所有者已完成T01–T21及前序研究/计划功能签收。正式标准为「本人已完成的全功能验收＋最终工程验证」；不要求重复签收，不宣称做过长期交易日或受邀多人试用。

原生安装目前在 macOS Apple Silicon（arm64）上验证。v1.1.0 另有实验性 Docker 镜像（见 README）。v1.0.0、v1.0.1 和 v1.1.0 的源码包都不包含 Dockerfile，也不把 Windows、Linux 或 Intel Mac 的原生安装标成正式支持。Yahoo 免 Key 接口按所有者决定暂缓，保留手工价格、成交 CSV 和用户自有 API。详见[支持范围](../OWNER_INSTALL.md)和[安全范围](RELEASE_SECURITY_REVIEW.md)。

## 工程证据

- P229范围639项本地Owner/安装/发行回归通过；对应98c3b3c的[GitHub完整检查](https://github.com/JayeeeJY/awesome-stock/actions/runs/37570846813)成功。
- P230配置指引与通知披露：Vue类型/生产构建、9项包/树验证、原模型配置/明确测试浏览器与1440/768/390/320指引展开、自有行情查询预览/确认保存流程通过。过期披露会阻断归档，原有上游许可正文不改写。
- 最终源码包在macOS arm64、Python3.10.20和3.14.3完成隔离安装、重启持久化、备份恢复与确定性重复打包。数据是合成记录，没有迁移用户真实数据库。
- 发行包逐文件SHA清单/归档审计、白名单干净树及解码Git内容对象秘密检查分别记录，结果不互相代替。实际最终提交的CI链接、包SHA和安装核验绑定在Release证据中；请核对[GitHub Actions](https://github.com/JayeeeJY/awesome-stock/actions)的对应提交，不能只看曾经出现过绿色结果。

[开发检查](DEVELOPMENT.md)提供可复现命令。包带Vue源码和编译产物；运行无需Node。构建/测试依赖不随用户运行环境安装。

## 验证的边界

浏览器自动化使用离线供应商固定样例；测试通过不证明每个真实服务账号、市场权限、模型模式或设备均可用。所有者实际模型/行情签收仅代表其所测流程。新用户按[配置指南](OPTIONAL_PROVIDERS.md)用自己的凭据主动测试，不需要把Key或真实持仓交给维护者。

项目许可选择和两包缺失通知处理已获所有者批准，见[许可说明](../LICENSING.md)和[透明披露](OWNER_UI_NOTICE_DISCLOSURES.txt)。披露不是恢复了不存在的上游正文，也不是独立法律认证；工具清单默认不签发法律或公开授权。

依赖审计和秘密扫描均有覆盖限制，不能保证绝对安全。历史排除的容器44项HIGH未宣称修复/无害或接受风险，不属于首发交付。完整备份未加密，用户须妥善保管自己的数据与解释器。未提供支持SLA、签名保证或公网多用户部署。

## v1.0.1 登录视觉与首页补丁

仅更新登录页视觉/粒子组件与产品图文，不改账本与本地账号协议。新增隔离浏览器检查覆盖粒子画面实际变化、减少动效静态星光、首次创建/口令错误/再次登录、路由离开清理、桌面与320/390宽度。全部展示记录为合成数据。锁定原Personal所用tsParticles 3.9.1（上游已将此系列标为deprecated），当前npm审计无已知漏洞；这不等于长期维护保证。粒子从本地包加载，失败时静态背景与登录可继续。完整检查与精确包的安装/恢复证据绑定到v1.0.1对应CI与Release。v1.0.0不覆盖。

## v1.1.0 首屏、社区文件与实验性 Docker

不改账本协议和已编译界面。变更是 README 首屏、Discussions/Issue 入口、贡献说明、路线图，以及实验性容器。源码包仍是 macOS Apple Silicon 的原生源码，不含 Dockerfile。镜像由 `v*` 标签的 GitHub Actions 用 `GITHUB_TOKEN` 推到 GHCR，本次没有新的镜像漏洞扫描。Linux 上做过容器冒烟：页面能打开，数据目录权限为 700。没有在 Windows 或 macOS 的 Docker Desktop 上复测，也没有重做 v1.0.1 的 macOS 隔离安装。对应提交的 CI 以 GitHub Actions 上该提交的 `Owner checks` 为准。
