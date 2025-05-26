/**
 * JSON编辑器独立模块 v2.0
 * 完全封装，防止与其他功能冲突
 */

const JsonEditor = {
    // 缓存管理
    cache: new Map(),
    
    // 配置选项
    config: {
        maxCacheSize: 50 * 1024 * 1024, // 50MB
        cacheExpireTime: 30 * 60 * 1000, // 30分钟
        animationDuration: 200
    },
    
    // 渲染JSON内容的主函数
    render: function(container, content) {
        try {
            // 解析JSON
            const jsonObj = JSON.parse(content);
            
            // 创建JSON编辑器容器
            const jsonEditor = document.createElement('div');
            jsonEditor.className = 'json-editor';
            
            // 头部工具栏
            const toolbar = document.createElement('div');
            toolbar.className = 'json-toolbar';
            toolbar.innerHTML = `
                <div class="json-toolbar-left">
                    <span class="json-title">
                        <i class="fas fa-code"></i>
                        JSON 数据查看器
                    </span>
                </div>
                <div class="json-toolbar-right">
                    <input type="text" class="json-search" placeholder="搜索..." />
                    <button class="json-btn expand-all" onclick="JsonEditor.expandAll(this)">
                        <i class="fas fa-expand-arrows-alt"></i>
                        全部展开
                    </button>
                    <button class="json-btn collapse-all" onclick="JsonEditor.collapseAll(this)" style="display:none;">
                        <i class="fas fa-compress-arrows-alt"></i>
                        全部收缩
                    </button>
                    <button class="json-btn copy" onclick="JsonEditor.copyContent(this)">
                        <i class="fas fa-copy"></i>
                        复制
                    </button>
                </div>
            `;
            
            // JSON内容区域
            const jsonContent = document.createElement('div');
            jsonContent.className = 'json-content';
            
            // 渲染JSON树
            const jsonTree = this.renderNode(jsonObj, 0, 'root');
            jsonContent.innerHTML = jsonTree;
            
            // 状态栏
            const statusBar = document.createElement('div');
            statusBar.className = 'json-status';
            const stats = this.getStats(jsonObj);
            statusBar.innerHTML = `
                <span>类型: ${stats.type}</span>
                <span>大小: ${stats.size} 字符</span>
                <span>行数: ${stats.lines}</span>
            `;
            
            // 组装编辑器
            jsonEditor.appendChild(toolbar);
            jsonEditor.appendChild(jsonContent);
            jsonEditor.appendChild(statusBar);
            
            // 清空容器并添加编辑器
            container.innerHTML = '';
            container.appendChild(jsonEditor);
            
            // 绑定搜索功能
            const searchInput = toolbar.querySelector('.json-search');
            searchInput.addEventListener('input', function() {
                JsonEditor.search(this.value, jsonContent);
            });
            
            // 绑定节点点击事件
            this.bindNodeEvents(jsonContent);
            
            console.log('JsonEditor: 渲染完成');
            
        } catch (error) {
            console.error('JsonEditor: JSON解析失败:', error);
            container.innerHTML = `
                <div class="json-editor">
                    <div class="json-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <div class="error-message">JSON格式错误</div>
                        <div class="error-detail">${error.message}</div>
                    </div>
                </div>
            `;
        }
    },
    
    // 渲染JSON节点
    renderNode: function(obj, level, key = null) {
        const indent = '  '.repeat(level);
        let html = '';
        
        if (obj === null) {
            return `<span class="json-null">null</span>`;
        }
        
        if (typeof obj === 'string') {
            return `<span class="json-string">"${this.escapeString(obj)}"</span>`;
        }
        
        if (typeof obj === 'number') {
            return `<span class="json-number">${obj}</span>`;
        }
        
        if (typeof obj === 'boolean') {
            return `<span class="json-boolean">${obj}</span>`;
        }
        
        // 处理对象和数组
        const isArray = Array.isArray(obj);
        const entries = isArray ? obj.map((val, idx) => [idx, val]) : Object.entries(obj);
        const isEmpty = entries.length === 0;
        
        if (isEmpty) {
            return `<span class="json-bracket">${isArray ? '[]' : '{}'}</span>`;
        }
        
        const nodeId = Utils.generateId('json_node');
        const openBracket = isArray ? '[' : '{';
        const closeBracket = isArray ? ']' : '}';
        
        html += `<div class="json-node">`;
        html += `<span class="json-toggle" data-node-id="${nodeId}" data-expanded="true">`;
        html += `<i class="fas fa-chevron-down"></i>`;
        html += `</span>`;
        html += `<span class="json-bracket">${openBracket}</span>`;
        html += `<span class="json-count">${entries.length} ${isArray ? 'items' : 'properties'}</span>`;
        
        html += `<div class="json-children" id="${nodeId}">`;
        entries.forEach(([k, v], index) => {
            const isLast = index === entries.length - 1;
            html += `<div class="json-line">`;
            
            if (!isArray) {
                html += `<span class="json-key">"${this.escapeString(k)}"</span>`;
                html += `<span class="json-colon">: </span>`;
            }
            
            if (v && typeof v === 'object') {
                html += this.renderNode(v, level + 1, k);
            } else {
                html += this.renderNode(v, level + 1, k);
            }
            
            if (!isLast) {
                html += `<span class="json-comma">,</span>`;
            }
            html += `</div>`;
        });
        html += `</div>`;
        
        html += `<div class="json-close">`;
        html += `<span class="json-bracket">${closeBracket}</span>`;
        html += `</div>`;
        html += `</div>`;
        
        return html;
    },
    
    // 绑定节点事件
    bindNodeEvents: function(container) {
        const toggles = container.querySelectorAll('.json-toggle');
        toggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                JsonEditor.toggleNode(this);
            });
        });
    },
    
    // 切换节点展开/收缩
    toggleNode: function(toggleElement) {
        const nodeId = toggleElement.getAttribute('data-node-id');
        const isExpanded = toggleElement.getAttribute('data-expanded') === 'true';
        const childrenContainer = document.getElementById(nodeId);
        const icon = toggleElement.querySelector('i');
        
        if (isExpanded) {
            // 收缩
            childrenContainer.style.display = 'none';
            icon.className = 'fas fa-chevron-right';
            toggleElement.setAttribute('data-expanded', 'false');
        } else {
            // 展开
            childrenContainer.style.display = 'block';
            icon.className = 'fas fa-chevron-down';
            toggleElement.setAttribute('data-expanded', 'true');
        }
    },
    
    // 全部展开
    expandAll: function(button) {
        const editor = button.closest('.json-editor');
        const toggles = editor.querySelectorAll('.json-toggle');
        
        toggles.forEach(toggle => {
            const nodeId = toggle.getAttribute('data-node-id');
            const childrenContainer = document.getElementById(nodeId);
            const icon = toggle.querySelector('i');
            
            childrenContainer.style.display = 'block';
            icon.className = 'fas fa-chevron-down';
            toggle.setAttribute('data-expanded', 'true');
        });
        
        // 切换按钮显示
        button.style.display = 'none';
        button.parentNode.querySelector('.collapse-all').style.display = 'inline-flex';
    },
    
    // 全部收缩
    collapseAll: function(button) {
        const editor = button.closest('.json-editor');
        const toggles = editor.querySelectorAll('.json-toggle');
        
        toggles.forEach(toggle => {
            const nodeId = toggle.getAttribute('data-node-id');
            const childrenContainer = document.getElementById(nodeId);
            const icon = toggle.querySelector('i');
            
            childrenContainer.style.display = 'none';
            icon.className = 'fas fa-chevron-right';
            toggle.setAttribute('data-expanded', 'false');
        });
        
        // 切换按钮显示
        button.style.display = 'none';
        button.parentNode.querySelector('.expand-all').style.display = 'inline-flex';
    },
    
    // JSON搜索
    search: function(searchTerm, container) {
        const lines = container.querySelectorAll('.json-line, .json-node');
        
        // 清除之前的高亮
        lines.forEach(line => {
            line.classList.remove('json-search-highlight');
        });
        
        if (!searchTerm.trim()) return;
        
        let firstMatch = null;
        lines.forEach(line => {
            const text = line.textContent.toLowerCase();
            if (text.includes(searchTerm.toLowerCase())) {
                line.classList.add('json-search-highlight');
                if (!firstMatch) {
                    firstMatch = line;
                }
                
                // 确保父节点展开
                let parent = line.closest('.json-children');
                while (parent) {
                    parent.style.display = 'block';
                    const parentToggle = document.querySelector(`[data-node-id="${parent.id}"]`);
                    if (parentToggle) {
                        parentToggle.setAttribute('data-expanded', 'true');
                        parentToggle.querySelector('i').className = 'fas fa-chevron-down';
                    }
                    parent = parent.parentElement.closest('.json-children');
                }
            }
        });
        
        // 滚动到第一个匹配项
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },
    
    // 复制JSON内容
    copyContent: function(button) {
        const editor = button.closest('.json-editor');
        const content = editor.querySelector('.json-content');
        const jsonText = this.extractText(content);
        
        navigator.clipboard.writeText(jsonText).then(() => {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i> 已复制';
            button.classList.add('success');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('success');
            }, 2000);
        }).catch(err => {
            console.error('JsonEditor: 复制失败:', err);
            Utils.showNotification('复制失败', 'error');
        });
    },
    
    // 提取JSON文本
    extractText: function(container) {
        const clonedContainer = container.cloneNode(true);
        
        // 移除所有按钮和图标
        clonedContainer.querySelectorAll('.json-toggle, .json-count').forEach(el => el.remove());
        
        return clonedContainer.textContent.replace(/\s+/g, ' ').trim();
    },
    
    // 获取JSON统计信息
    getStats: function(obj) {
        const jsonString = JSON.stringify(obj, null, 2);
        return {
            type: Array.isArray(obj) ? 'Array' : (obj === null ? 'null' : typeof obj),
            size: jsonString.length,
            lines: jsonString.split('\n').length
        };
    },
    
    // JSON字符串转义
    escapeString: function(str) {
        return String(str)
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r')
            .replace(/\t/g, '\\t');
    }
};

// 导出到全局
window.JsonEditor = JsonEditor; 