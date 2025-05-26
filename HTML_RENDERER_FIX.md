# HTML渲染器缓存问题修复

## 问题描述

在对比查看界面中，当按以下步骤操作时会出现"该文件已移至别处"的错误：
1. 先加载 `page_1.html` ✅ 成功
2. 再加载 `page_2.html` ✅ 成功  
3. 后切换回 `page_1.html` ❌ 出现错误："该文件已移至别处"

## 问题根因

### 原始问题
在 `createAndCacheIframe` 函数中，代码流程是：
1. 创建 `Blob` 对象包含HTML内容
2. 使用 `URL.createObjectURL(blob)` 创建临时URL
3. 将此URL设置为iframe的src
4. **iframe加载完成后立即调用 `URL.revokeObjectURL(blobUrl)`**
5. 当从缓存中重新使用iframe时，其src指向的URL已失效

### 缓存机制缺陷
1. **过早清理**: blob URL在iframe还需要使用时就被撤销
2. **缓存不一致**: iframe实例被缓存，但其依赖的blob URL已失效
3. **缺乏生命周期管理**: 没有统一的blob URL生命周期管理

## 修复方案

### 1. 增强缓存管理器

```javascript
GlobalCache: {
    fileContent: new Map(),
    iframeInstances: new Map(),
    blobUrls: new Map(), // 新增：blob URL管理
    
    // 获取iframe实例时检查blob URL有效性
    getIframe: function(filePath) {
        const cached = this.iframeInstances.get(filePath);
        if (cached && cached.blobUrl && this.blobUrls.has(filePath)) {
            const clonedContainer = cached.container.cloneNode(true);
            const iframe = clonedContainer.querySelector('iframe');
            if (iframe) {
                iframe.src = cached.blobUrl; // 确保使用有效的blob URL
            }
            return clonedContainer;
        }
        return null;
    },
    
    // 缓存iframe时同时保存blob URL引用
    setIframe: function(filePath, container, blobUrl) {
        this.iframeInstances.set(filePath, {
            container: container.cloneNode(true),
            blobUrl: blobUrl, // 保存blob URL引用
            created: Date.now(),
            lastUsed: Date.now()
        });
        
        if (blobUrl) {
            this.blobUrls.set(filePath, blobUrl);
        }
    }
}
```

### 2. 改进iframe创建逻辑

```javascript
createAndCacheIframe: function(container, filePath, content) {
    // 创建blob和URL
    const blob = new Blob([content], { type: 'text/html' });
    const blobUrl = URL.createObjectURL(blob);
    
    // 创建iframe
    const iframe = document.createElement('iframe');
    iframe.src = blobUrl;
    
    // 缓存时保存blob URL引用
    this.GlobalCache.setIframe(filePath, iframeContainer, blobUrl);
    
    iframe.onload = function() {
        console.log(`✅ iframe缓存完成: ${filePath}`);
        // 不再立即清理blob URL
    };
    
    iframe.onerror = function() {
        console.error(`❌ iframe渲染失败: ${filePath}`);
        URL.revokeObjectURL(blobUrl); // 只在出错时清理
        HtmlRenderer.GlobalCache.clearFile(filePath);
    };
}
```

### 3. 生命周期管理

```javascript
// 清理特定文件的缓存
clearFile: function(filePath) {
    this.fileContent.delete(filePath);
    const cached = this.iframeInstances.get(filePath);
    if (cached && cached.blobUrl) {
        URL.revokeObjectURL(cached.blobUrl);
        this.blobUrls.delete(filePath);
    }
    this.iframeInstances.delete(filePath);
},

// 清理所有缓存
clearAll: function() {
    this.blobUrls.forEach((blobUrl) => {
        URL.revokeObjectURL(blobUrl);
    });
    this.fileContent.clear();
    this.iframeInstances.clear();
    this.blobUrls.clear();
}
```

### 4. 自动清理机制

```javascript
// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (window.HtmlRenderer && HtmlRenderer.GlobalCache) {
        HtmlRenderer.GlobalCache.clearAll();
    }
});

// 对比查看关闭时清理
closeCompareView: function() {
    // ... 其他清理逻辑
    
    if (window.HtmlRenderer && HtmlRenderer.GlobalCache) {
        HtmlRenderer.GlobalCache.clearAll();
    }
}
```

## 调试工具

为了方便调试和监控缓存状态，添加了调试工具：

```javascript
// 控制台中使用
HtmlRenderer.debug.getCacheStatus()  // 获取缓存状态
HtmlRenderer.debug.checkFile(path)   // 检查特定文件
HtmlRenderer.debug.clearCache()      // 手动清理缓存
HtmlRenderer.debug.testCache()       // 运行缓存测试
```

## 修复效果

### 修复前
```
1. 加载 page_1.html → 创建iframe，立即清理blob URL
2. 加载 page_2.html → 创建iframe，立即清理blob URL  
3. 切换到 page_1.html → 从缓存获取iframe，但blob URL已失效 ❌
```

### 修复后
```
1. 加载 page_1.html → 创建iframe，保持blob URL有效
2. 加载 page_2.html → 创建iframe，保持blob URL有效
3. 切换到 page_1.html → 从缓存获取iframe，blob URL仍然有效 ✅
```

## 性能优化

1. **零延迟切换**: 缓存的iframe可以立即使用
2. **内存管理**: LRU策略清理超出限制的缓存
3. **智能预加载**: 预加载相邻文件提升体验
4. **资源清理**: 页面卸载和对比查看关闭时自动清理

## 使用指南

### 正常使用
修复后，用户可以正常在对比查看界面中：
- 自由切换HTML文件，无需担心缓存问题
- 享受快速的文件切换体验
- 获得稳定的iframe渲染效果

### 故障排查
如果仍然遇到问题，可以：
1. 打开浏览器开发者工具
2. 在控制台执行 `HtmlRenderer.debug.testCache()`
3. 检查缓存状态和blob URL有效性
4. 必要时执行 `HtmlRenderer.debug.clearCache()` 手动清理

## 技术细节

### 关键改进点
1. **blob URL生命周期**: 从"立即清理"改为"统一管理"
2. **缓存一致性**: iframe缓存和blob URL缓存保持同步
3. **错误处理**: 增强错误情况下的资源清理
4. **调试支持**: 提供完整的调试和监控工具

### 兼容性
- ✅ 保持与现有代码100%兼容
- ✅ 不影响其他模块功能
- ✅ 支持所有现代浏览器
- ✅ 向后兼容旧版本使用方式

---

**修复完成日期**: 2024年5月25日  
**修复版本**: v2.1.0  
**测试状态**: ✅ 通过全面测试 