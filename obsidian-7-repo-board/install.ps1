# Install 7-Repo Board into an existing Obsidian vault (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src = Join-Path $Root "vault-files"
$State = Join-Path $Root ".vault-path"

function Get-VaultPath {
    param([string]$ArgPath)
    if ($ArgPath -and (Test-Path -LiteralPath $ArgPath)) {
        return (Resolve-Path -LiteralPath $ArgPath).Path
    }
    if (Test-Path -LiteralPath $State) {
        $saved = (Get-Content -LiteralPath $State -Raw).Trim()
        if ($saved -and (Test-Path -LiteralPath (Join-Path $saved ".obsidian"))) {
            return $saved
        }
    }
    $path = Read-Host "请输入你的 Obsidian vault 绝对路径（目录内应有 .obsidian）"
    if (-not $path) { throw "未提供 vault 路径" }
    return $path.Trim().Trim('"')
}

function Merge-Snippet {
    param([string]$AppearancePath)
    $map = [ordered]@{}
    if (Test-Path -LiteralPath $AppearancePath) {
        $raw = Get-Content -LiteralPath $AppearancePath -Raw -Encoding UTF8
        if ($raw.Trim()) {
            $obj = $raw | ConvertFrom-Json
            foreach ($p in $obj.PSObject.Properties) {
                $map[$p.Name] = $p.Value
            }
        }
    }
    $list = @()
    if ($map.Contains("enabledCssSnippets") -and $null -ne $map["enabledCssSnippets"]) {
        $list = @($map["enabledCssSnippets"])
    }
    if ($list -notcontains "7-repo-board") {
        $list += "7-repo-board"
    }
    $map["enabledCssSnippets"] = $list
    $json = ($map | ConvertTo-Json -Depth 20)
    [System.IO.File]::WriteAllText($AppearancePath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
}

$vault = Get-VaultPath -ArgPath $args[0]
if (-not (Test-Path -LiteralPath $vault)) { throw "目录不存在: $vault" }
$obs = Join-Path $vault ".obsidian"
if (-not (Test-Path -LiteralPath $obs)) { throw "看起来不像 vault（缺少 .obsidian）: $vault" }
$boardSrc = Join-Path $Src "7-Repo-Board"
if (-not (Test-Path -LiteralPath $boardSrc)) { throw "安装包不完整，缺少 vault-files/7-Repo-Board" }

Write-Host "→ 目标 vault: $vault"
$snippets = Join-Path $obs "snippets"
New-Item -ItemType Directory -Force -Path $snippets | Out-Null

$destBoard = Join-Path $vault "7-Repo-Board"
if (Test-Path -LiteralPath $destBoard) {
    Remove-Item -LiteralPath $destBoard -Recurse -Force
}
Write-Host "→ 复制 7-Repo-Board/ …"
Copy-Item -LiteralPath $boardSrc -Destination $destBoard -Recurse

Write-Host "→ 安装 CSS snippet …"
Copy-Item -LiteralPath (Join-Path $Src ".obsidian\snippets\7-repo-board.css") `
    -Destination (Join-Path $snippets "7-repo-board.css") -Force

Write-Host "→ 启用 snippet（合并 appearance.json）…"
Merge-Snippet -AppearancePath (Join-Path $obs "appearance.json")

Set-Content -LiteralPath $State -Value $vault -Encoding UTF8

Write-Host ""
Write-Host "完成。"
Write-Host "下一步："
Write-Host "  1. 打开 Obsidian → 打开文件  7-Repo-Board/7-Repo-Board.canvas"
Write-Host "  2. 若 snippet 未生效：设置 → 外观 → CSS 代码片段 → 勾选 7-repo-board"
Write-Host "  3. （可选）安装 Minimal 主题 + Flexoki 配色，更接近原图"
Write-Host ""
Write-Host "说明见: $(Join-Path $destBoard 'START-HERE.md')"
