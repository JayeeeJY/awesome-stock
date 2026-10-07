# Awesome Stock Community · 原生源码安装

本次正式首发支持 **macOS Apple Silicon（arm64）**，需要Python 3.10+。发行包自带已编译界面，应用运行只使用Python标准库，无需Node、数据库服务或Docker。当前仍为待公开发行的本地候选；Docker安装暂缓，Windows、Linux和Intel Mac不列入首发正式支持范围。

没有默认账号、统一模型Key或代付服务；首次使用创建自己的账号。不配置模型或行情服务也可记账和手工研究。

## 安装与启动

解压源码包后进入`awesome-stock-owner`目录。首次使用：

```sh
python3 --version
python3 start_owner.py --open-browser
```

访问 http://127.0.0.1:4322/ledger ，按页面创建本地账号。默认数据位于程序目录的`.owner-state`。只在自己的电脑运行，端口绑定127.0.0.1。

建议为数据指定独立目录；以下路径由你选择，首次启动时会创建：

```sh
python3 start_owner.py --data-dir "$HOME/Awesome-Stock-Data" --open-browser
```

再次启动和升级时继续使用相同`--data-dir`，避免误用空账本。端口被占用时可加`--port 4324`。终端按Ctrl+C停止服务，数据目录保留。不要同时启动两个服务写同一个账本，也不要删除数据目录解决登录问题。

可选本地模型使用127.0.0.1:11434的Ollama，由用户自行安装、启动和配置模型。云端API Key仅在当前进程内存，退出、改密或重启后需重新配置，见[可选连接](docs/OPTIONAL_PROVIDERS.md)。

## 备份与恢复

设置页创建完整备份，包含口令摘要与业务历史，未加密。页面提供数据目录和备份名称；将相应`backups/备份名称`目录完整复制到独立保管位置。目录中的各文件一起保留，不单独复制正在运行的SQLite文件。

恢复到**不存在的新目录**，不覆盖原账本：

```sh
python3 start_owner.py --restore-from ./保管的备份 --data-dir ./restored-owner
python3 start_owner.py --data-dir ./restored-owner
```

先检查恢复后的记录和历史，再决定切换。旧版本回退使用升级前备份和对应旧源码，在新目录核验，不将新库直接交给旧程序。

## 升级

1. 在设置页创建备份并复制到独立位置，保留原源码包。
2. Ctrl+C停止服务，解压新源码到另一目录。
3. 从新目录启动，并用`--data-dir`指向原数据目录。
4. 登录核对账本及历史。首次打开schema 1/2/3/4会先备份后事务升级到5；备份或程序错误时保留原数据，按错误提示处理。

旧账户保留加权平均，新账户可选择FIFO或加权平均；保存后不可直接切换。

## 发行内容与验证

`python3 tools/package_owner.py --output 新文件名.tar.gz`生成可复现源码包及逐文件哈希清单。包含Python源码、Vue源码与已编译界面、安装说明、合成展示截图、正式LICENSE和第三方通知材料。数据库、备份、.env、私有Git历史、API Key、Docker入口和部署文件不进入包。应用启动无需Node；修改界面后的重新构建需要Node及锁定依赖。模型权重和Python解释器不随包提供。

开发测试与CI材料位于单独的GitHub审阅树，用户运行无需安装这些工具。[验证说明](docs/VALIDATION.md)、[首发安全范围](docs/RELEASE_SECURITY_REVIEW.md)和OWNER_SUPPLY_CHAIN.json记录当前范围；旧容器扫描只作历史，不代表原生安装无风险或已经公开发布。
