# 04 · obsidian-sample-plugin
**by obsidianmd** · [github.com/obsidianmd/obsidian-sample-plugin](https://github.com/obsidianmd/obsidian-sample-plugin)

> 官方模板 — 构建你缺失的那块插件。

## `main.ts`（节选）

```ts
export default class SamplePlugin extends Plugin {
  async onload() {
    this.addRibbonIcon("dice", "Sample Plugin", () => {
      new Notice("Hello from your plugin");
    });

    this.addCommand({
      id: "open-sample-modal",
      name: "Open sample modal",
      callback: () => new SampleModal(this.app).open(),
    });
  }
}
```

## Preview

```
┌─ Sample checklist ──────────┐
│ ☑ Scaffold plugin           │
│ ☑ Register command          │
│ ☐ Ship to releases          │
└─────────────────────────────┘
```

Clone → `npm i` → `npm run dev` → 在 vault 的 `.obsidian/plugins` 里热重载。
