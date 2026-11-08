# Obsidian 7-Repo Board — 一键装进现有 vault

把图里的「7 REPO BOARD」Canvas 桌面复制进你**已经在用**的 Obsidian 库。

## macOS（推荐）

1. 打开本目录  
2. 双击 `install.command`  
3. 粘贴你的 vault 路径（含 `.obsidian` 的那个文件夹）  
4. 在 Obsidian 打开 `7-Repo-Board/7-Repo-Board.canvas`

若提示无法打开：终端执行一次  
`chmod +x install.command install.sh`  
再双击。

## Windows

1. 右键 `install.ps1` → 使用 PowerShell 运行  
   （若被拦截：先 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`）  
2. 输入 vault 路径  
3. 打开 `7-Repo-Board/7-Repo-Board.canvas`

也可：

```powershell
.\install.ps1 "D:\Path\To\YourVault"
```

## Linux

```bash
chmod +x install.sh
./install.sh "/path/to/YourVault"
```

## 装完做什么

| 步骤 | 操作 |
|---|---|
| 必做 | 打开 `7-Repo-Board/7-Repo-Board.canvas` |
| 建议 | 设置 → 外观 → CSS 片段 → 勾选 **7-repo-board**（脚本一般已勾） |
| 可选 | 装 **Minimal** 主题 + **Flexoki** 配色，更像截图 |

## 脚本会改什么

**会写：**

- `YourVault/7-Repo-Board/**`
- `YourVault/.obsidian/snippets/7-repo-board.css`
- 在 `appearance.json` 的 `enabledCssSnippets` 里加入 `7-repo-board`

**不会动：**主题、社区插件列表、其它笔记。

重复运行会覆盖 `7-Repo-Board/` 与该 CSS 文件（方便更新），其它内容仍安全。

## 包内结构

```
obsidian-7-repo-board/
  START-HERE.md          ← 你在看的说明
  install.command        ← macOS 双击
  install.ps1            ← Windows
  install.sh             ← macOS/Linux CLI
  vault-files/           ← 真正复制进 vault 的内容
```
