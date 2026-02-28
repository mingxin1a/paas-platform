# 前端 UI 设计规范

## 设计令牌（Design Tokens）

- 所有颜色、圆角、间距均使用 `src/index.css` 中定义的 CSS 变量：
  - `--color-primary`、`--color-bg`、`--color-surface`、`--color-border`、`--color-text`、`--color-text-secondary`、`--color-error` 等
  - `--radius-sm` / `--radius-md` / `--radius-lg`
  - `--space-unit`、`--sidebar-width`、`--header-height`
- 深色主题通过 `[data-theme="dark"]` 覆盖上述变量，无需在组件内写死颜色。

## 组件复用

- 列表/详情/空态：统一使用 `CellList.module.css`、`CellDetail.module.css` 中的 `.page`、`.header`、`.table`、`.empty`、`.loading`、`.error` 等类名。
- 按钮：主操作使用 `.exportBtn` 风格（边框+主题色），与设计系统一致。
- 表单：输入框统一 `border: 1px solid var(--color-border)`、`border-radius: var(--radius-sm)`，错误态使用 `var(--color-error)`。

## 交互与权限

- 无权限的细胞不在侧栏展示（由 `useAllowedCells` 过滤）。
- 无权限访问具体细胞时展示「无权限访问该细胞」并提供返回入口。
- 有 `createFields` 的细胞在列表页展示「新建」按钮；新建页根据 `createFields` 渲染表单并做必填校验。

## 规范检查

- 新页面需通过 `npm run lint`（ESLint）。
- 关键逻辑与组件需补充单元测试，目标覆盖率 ≥60%。
