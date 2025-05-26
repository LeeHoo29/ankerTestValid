# JavaScript 模块化架构文档

## 概述

为了提高代码的可维护性和避免编辑时出现问题，我们将原本在 `index.html` 中的1776行JavaScript代码进行了模块化拆分。现在的架构更加清晰，便于维护和扩展。

## 模块结构

```
static/js/
├── utils.js           # 通用工具函数模块
├── json-editor.js     # JSON编辑器模块
├── html-renderer.js   # HTML渲染器模块
├── panel-resizer.js   # 面板拖拽调整模块
├── file-manager.js    # 文件管理模块
├── app-core.js        # 核心应用逻辑模块
└── README.md          # 本文档
```

## 各模块详细说明

### 1. utils.js - 通用工具函数模块

**功能**: 提供应用全局使用的工具函数

**主要功能**:
- `showNotification(message, type)` - 显示通知消息
- `updateCommandPreview()` - 更新命令预览
- `updateStatus(status)` - 更新任务状态显示
- `formatFileSize(bytes)` - 格式化文件大小
- `generateId(prefix)` - 生成唯一ID
- `debounce(func, wait)` - 防抖函数
- `throttle(func, limit)` - 节流函数
- `deepClone(obj)` - 深拷贝
- `parseUrlParams(url)` - 解析URL参数
- `storage` - 本地存储封装
- `performance` - 性能监控工具

**使用示例**:
```javascript
Utils.showNotification('操作成功', 'success');
const id = Utils.generateId('task');
Utils.storage.set('key', value);
```

### 2. json-editor.js - JSON编辑器模块

**功能**: 提供强大的JSON查看和编辑功能

**主要功能**:
- `render(container, content)` - 渲染JSON内容
- `expandAll(button)` - 全部展开节点
- `collapseAll(button)` - 全部收缩节点
- `search(searchTerm, container)` - 搜索JSON内容
- `copyContent(button)` - 复制JSON内容
- `toggleNode(toggleElement)` - 切换节点展开/收缩

**特性**:
- VSCode风格深色主题
- 语法高亮显示
- 交互式节点展开/收缩
- 实时搜索功能
- 复制功能
- 完全样式隔离

**使用示例**:
```javascript
JsonEditor.render(container, jsonString);
```

### 3. html-renderer.js - HTML渲染器模块

**功能**: 高性能HTML文件渲染和缓存管理

**主要功能**:
- `loadCompareHtmlFile(filePath)` - 加载HTML文件
- `loadCompareJsonFile(filePath)` - 加载JSON文件
- `GlobalCache` - 全局缓存管理
- `preloadAllHtmlFiles(files)` - 预加载HTML文件
- `backgroundPreloadNext(currentFilePath)` - 后台预加载

**特性**:
- 三层优先级加载策略
- iframe缓存系统
- 智能预加载
- 0延迟切换体验
- 优化的加载动画

**缓存策略**:
1. iframe缓存 (0延迟瞬间切换)
2. 文件内容缓存 (50ms快速渲染)
3. 网络加载 (显示优化动画)

### 4. panel-resizer.js - 面板拖拽调整模块

**功能**: 支持实时拖拽调整面板大小

**主要功能**:
- `initialize()` - 初始化拖拽功能
- `setPanelWidths(leftRatio)` - 设置面板宽度比例
- `resetPanelWidths()` - 重置为默认比例
- `setRatioAnimated(ratio, duration)` - 动画设置比例
- `cleanup()` - 清理功能

**特性**:
- 实时拖拽调整
- 双击重置为50:50
- 窗口大小响应
- 触摸设备支持
- 本地存储偏好设置
- 拖拽指示器

**配置**:
- 最小宽度比例: 20%
- 最大宽度比例: 80%
- 默认比例: 50:50

### 5. file-manager.js - 文件管理模块

**功能**: 管理对比查看界面和文件操作

**主要功能**:
- `openCompareView(taskPath)` - 打开对比查看界面
- `closeCompareView()` - 关闭对比查看界面
- `populateFileSelectors(files)` - 填充文件选择器
- `autoSelectFiles()` - 自动选择文件
- `nextHtmlFile()` / `prevHtmlFile()` - 切换HTML文件
- `nextJsonFile()` / `prevJsonFile()` - 切换JSON文件

**特性**:
- 自动文件选择
- 键盘快捷键支持
- 任务高亮显示
- 文件预加载
- 智能文件优先级

**键盘快捷键**:
- `Ctrl/Cmd + ←/→` - 切换HTML文件
- `Ctrl/Cmd + Shift + ←/→` - 切换JSON文件
- `Ctrl/Cmd + R` - 刷新文件列表
- `Escape` - 关闭对比查看

### 6. app-core.js - 核心应用逻辑模块

**功能**: 应用的核心逻辑和状态管理

**主要功能**:
- `initialize()` - 初始化应用
- `handleFormSubmit(e)` - 表单提交处理
- `startStatusPolling()` - 开始状态轮询
- `checkTaskStatus()` - 检查任务状态
- `toggleSidebarDesktop()` / `toggleSidebarMobile()` - 侧边栏切换
- `handleResize()` - 响应式处理

**状态管理**:
- 当前任务ID
- 侧边栏状态
- 移动端检测
- 状态轮询间隔

**特性**:
- 完整的表单处理
- 实时任务状态更新
- 响应式设计支持
- 资源自动清理

## 模块依赖关系

```
app-core.js
├── utils.js (工具函数)
├── file-manager.js (文件管理)
│   ├── html-renderer.js (渲染器)
│   │   ├── json-editor.js (JSON编辑)
│   │   └── utils.js
│   └── panel-resizer.js (面板调整)
│       └── utils.js
└── utils.js
```

## 加载顺序

在 `index.html` 中按以下顺序加载模块：

```html
<script src="js/utils.js"></script>
<script src="js/json-editor.js"></script>
<script src="js/html-renderer.js"></script>
<script src="js/panel-resizer.js"></script>
<script src="js/file-manager.js"></script>
<script src="js/app-core.js"></script>
```

## 全局对象

每个模块都导出到全局命名空间：

- `window.Utils`
- `window.JsonEditor`
- `window.HtmlRenderer`
- `window.PanelResizer`
- `window.FileManager`
- `window.AppCore`

## 配置选项

每个模块都有自己的配置对象，可以根据需要调整：

```javascript
// 示例：调整JSON编辑器配置
JsonEditor.config.maxCacheSize = 100 * 1024 * 1024; // 100MB

// 示例：调整面板调整器配置
PanelResizer.config.defaultRatio = 0.6; // 60:40比例
```

## 性能优化

1. **缓存策略**: HTML渲染器使用三层缓存提升性能
2. **预加载**: 智能预加载相邻文件
3. **防抖节流**: 关键操作使用防抖节流优化
4. **资源清理**: 自动清理不需要的资源
5. **模块化加载**: 按需初始化模块

## 维护指南

### 添加新功能

1. 确定功能属于哪个模块
2. 在对应模块中添加方法
3. 更新模块文档
4. 测试功能完整性

### 修改现有功能

1. 定位到具体模块和方法
2. 进行修改
3. 确保不影响其他模块
4. 更新相关文档

### 调试建议

1. 使用浏览器开发者工具
2. 检查控制台日志（每个模块都有详细日志）
3. 使用性能面板监控性能
4. 检查网络面板查看文件加载

## 兼容性

- 所有模块都提供向后兼容的全局函数
- 支持现代浏览器（ES6+）
- 移动端友好设计
- 触摸设备支持

## 未来扩展

1. **国际化支持**: 可以在utils.js中添加多语言支持
2. **主题系统**: 可以扩展样式配置
3. **插件系统**: 可以添加插件机制
4. **离线支持**: 可以添加Service Worker支持
5. **实时同步**: 可以添加WebSocket支持

---

**注意**: 修改模块代码时，请确保保持API的向后兼容性，避免破坏现有功能。 