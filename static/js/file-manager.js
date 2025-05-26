/**
 * 文件管理模块
 * 包含对比查看界面、文件选择器、自动选择等功能
 */

const FileManager = {
    // 当前状态
    state: {
        currentTaskPath: null,
        currentHtmlFile: null,
        currentJsonFile: null,
        isCompareViewOpen: false
    },

    // 配置选项
    config: {
        autoSelectFirst: true, // 自动选择第一个文件
        preferParseResult: true, // 优先选择parse_result.json
        preloadOnOpen: true // 打开时预加载文件
    },

    // 打开对比查看界面
    openCompareView: function(taskPath) {
        // 显示加载状态
        const overlay = document.getElementById('compareViewOverlay');
        overlay.style.display = 'block';
        
        // 记录当前任务路径
        this.state.currentTaskPath = taskPath;
        this.state.isCompareViewOpen = true;
        
        // 高亮当前查看的任务
        this.highlightCurrentTask(taskPath);
        
        // 获取任务信息并更新标题
        this.updateCompareViewTitle(taskPath);
        
        // 获取文件列表并初始化选择器
        this.initializeCompareView(taskPath);
        
        console.log(`打开对比查看界面: ${taskPath}`);
    },

    // 关闭对比查看界面
    closeCompareView: function() {
        const overlay = document.getElementById('compareViewOverlay');
        overlay.style.display = 'none';
        
        // 清除任务高亮
        document.querySelectorAll('.completed-task-card').forEach(card => {
            card.classList.remove('active-task');
        });
        
        // 清理拖拽功能
        PanelResizer.cleanup();
        
        // 清理HTML渲染器缓存
        if (window.HtmlRenderer && HtmlRenderer.GlobalCache) {
            console.log('清理对比查看相关的HTML渲染器缓存...');
            HtmlRenderer.GlobalCache.clearAll();
        }
        
        // 重置状态
        this.state.currentTaskPath = null;
        this.state.currentHtmlFile = null;
        this.state.currentJsonFile = null;
        this.state.isCompareViewOpen = false;
        
        console.log('对比查看界面已关闭，缓存已清理');
    },

    // 高亮当前查看的任务
    highlightCurrentTask: function(taskPath) {
        // 清除之前的高亮
        document.querySelectorAll('.completed-task-card').forEach(card => {
            card.classList.remove('active-task');
        });
        
        // 高亮当前任务
        document.querySelectorAll('.view-files-btn').forEach(btn => {
            if (btn.getAttribute('data-path') === taskPath) {
                btn.closest('.completed-task-card').classList.add('active-task');
            }
        });
    },

    // 更新对比查看界面标题
    updateCompareViewTitle: function(taskPath) {
        const pathParts = taskPath.split('/');
        const taskType = pathParts[pathParts.length - 2]; // 倒数第二个部分是任务类型
        const taskId = pathParts[pathParts.length - 1]; // 最后一个部分是任务ID
        
        const titleElement = document.getElementById('compareViewTaskTitle');
        titleElement.textContent = `对比查看 - ${taskType} (${taskId})`;
    },

    // 初始化对比查看界面
    initializeCompareView: function(taskPath) {
        fetch(`/api/list_files?path=${encodeURIComponent(taskPath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.populateFileSelectors(data.files);
                    
                    // 自动选择文件
                    if (this.config.autoSelectFirst) {
                        this.autoSelectFiles();
                    }
                    
                    // 初始化面板拖拽功能
                    setTimeout(() => {
                        PanelResizer.initialize();
                    }, 100);
                    
                    Utils.showNotification('对比查看界面已加载', 'success');
                } else {
                    Utils.showNotification('获取文件列表失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                Utils.showNotification('获取文件列表失败: ' + error.message, 'error');
            });
    },

    // 填充文件选择器
    populateFileSelectors: function(files) {
        const htmlSelector = document.getElementById('compare-html-selector');
        const jsonSelector = document.getElementById('compare-json-selector');
        
        // 清空选择器
        htmlSelector.innerHTML = '<option value="">请选择HTML文件</option>';
        jsonSelector.innerHTML = '<option value="">请选择JSON文件</option>';
        
        // 分类文件
        const htmlFiles = [];
        const jsonFiles = [];
        
        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.path;
            option.textContent = file.name;
            
            if (file.name.toLowerCase().endsWith('.html') || file.name.toLowerCase().endsWith('.htm')) {
                htmlSelector.appendChild(option);
                htmlFiles.push(file);
            } else if (file.name.toLowerCase().endsWith('.json')) {
                jsonSelector.appendChild(option);
                jsonFiles.push(file);
            }
        });
        
        // 立即开始全面预加载
        if (this.config.preloadOnOpen) {
            HtmlRenderer.preloadAllHtmlFiles(htmlFiles);
        }
        
        // 绑定增强的事件处理
        this.enhanceFileSelectors();
        
        console.log(`📁 文件列表: ${htmlFiles.length} HTML, ${jsonFiles.length} JSON`);
    },

    // 绑定文件选择器事件
    enhanceFileSelectors: function() {
        const htmlSelector = document.getElementById('compare-html-selector');
        const jsonSelector = document.getElementById('compare-json-selector');
        
        // 移除之前的事件监听器（如果存在）
        htmlSelector.removeEventListener('change', this.handleHtmlFileChange.bind(this));
        jsonSelector.removeEventListener('change', this.handleJsonFileChange.bind(this));
        
        // 绑定新的事件监听器
        htmlSelector.addEventListener('change', this.handleHtmlFileChange.bind(this));
        jsonSelector.addEventListener('change', this.handleJsonFileChange.bind(this));
    },

    // HTML文件选择器事件处理
    handleHtmlFileChange: function(event) {
        const filePath = event.target.value;
        this.state.currentHtmlFile = filePath;
        HtmlRenderer.loadCompareHtmlFile(filePath);
    },

    // JSON文件选择器事件处理
    handleJsonFileChange: function(event) {
        const filePath = event.target.value;
        this.state.currentJsonFile = filePath;
        HtmlRenderer.loadCompareJsonFile(filePath);
    },

    // 自动选择文件
    autoSelectFiles: function() {
        const htmlSelector = document.getElementById('compare-html-selector');
        const jsonSelector = document.getElementById('compare-json-selector');
        
        // 自动选择第一个HTML文件
        if (htmlSelector.options.length > 1) {
            htmlSelector.selectedIndex = 1;
            this.state.currentHtmlFile = htmlSelector.value;
            HtmlRenderer.loadCompareHtmlFile(htmlSelector.value);
        }
        
        // 优先选择parse_result.json
        let selectedJsonIndex = -1;
        if (this.config.preferParseResult) {
            for (let i = 1; i < jsonSelector.options.length; i++) {
                if (jsonSelector.options[i].textContent.toLowerCase().includes('parse_result')) {
                    selectedJsonIndex = i;
                    break;
                }
            }
        }
        
        if (selectedJsonIndex > 0) {
            jsonSelector.selectedIndex = selectedJsonIndex;
        } else if (jsonSelector.options.length > 1) {
            jsonSelector.selectedIndex = 1;
        }
        
        if (jsonSelector.selectedIndex > 0) {
            this.state.currentJsonFile = jsonSelector.value;
            HtmlRenderer.loadCompareJsonFile(jsonSelector.value);
        }
    },

    // 刷新文件列表
    refreshFileList: function() {
        if (!this.state.currentTaskPath) return;
        
        // 重新初始化
        this.initializeCompareView(this.state.currentTaskPath);
        Utils.showNotification('文件列表已刷新', 'info');
    },

    // 切换到下一个HTML文件
    nextHtmlFile: function() {
        const htmlSelector = document.getElementById('compare-html-selector');
        const currentIndex = htmlSelector.selectedIndex;
        
        if (currentIndex < htmlSelector.options.length - 1) {
            htmlSelector.selectedIndex = currentIndex + 1;
            this.handleHtmlFileChange({ target: htmlSelector });
            return true;
        }
        return false;
    },

    // 切换到上一个HTML文件
    prevHtmlFile: function() {
        const htmlSelector = document.getElementById('compare-html-selector');
        const currentIndex = htmlSelector.selectedIndex;
        
        if (currentIndex > 1) {
            htmlSelector.selectedIndex = currentIndex - 1;
            this.handleHtmlFileChange({ target: htmlSelector });
            return true;
        }
        return false;
    },

    // 切换到下一个JSON文件
    nextJsonFile: function() {
        const jsonSelector = document.getElementById('compare-json-selector');
        const currentIndex = jsonSelector.selectedIndex;
        
        if (currentIndex < jsonSelector.options.length - 1) {
            jsonSelector.selectedIndex = currentIndex + 1;
            this.handleJsonFileChange({ target: jsonSelector });
            return true;
        }
        return false;
    },

    // 切换到上一个JSON文件
    prevJsonFile: function() {
        const jsonSelector = document.getElementById('compare-json-selector');
        const currentIndex = jsonSelector.selectedIndex;
        
        if (currentIndex > 1) {
            jsonSelector.selectedIndex = currentIndex - 1;
            this.handleJsonFileChange({ target: jsonSelector });
            return true;
        }
        return false;
    },

    // 获取当前文件信息
    getCurrentFileInfo: function() {
        return {
            taskPath: this.state.currentTaskPath,
            htmlFile: this.state.currentHtmlFile,
            jsonFile: this.state.currentJsonFile,
            isOpen: this.state.isCompareViewOpen
        };
    },

    // 键盘快捷键支持
    initKeyboardShortcuts: function() {
        document.addEventListener('keydown', (e) => {
            if (!this.state.isCompareViewOpen) return;
            
            // 只在对比查看界面开启时响应快捷键
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'ArrowLeft':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.prevJsonFile();
                        } else {
                            this.prevHtmlFile();
                        }
                        break;
                        
                    case 'ArrowRight':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.nextJsonFile();
                        } else {
                            this.nextHtmlFile();
                        }
                        break;
                        
                    case 'r':
                        e.preventDefault();
                        this.refreshFileList();
                        break;
                        
                    case 'Escape':
                        e.preventDefault();
                        this.closeCompareView();
                        break;
                }
            }
        });
    },

    // 初始化模块
    initialize: function() {
        // 绑定查看文件按钮
        document.querySelectorAll('.view-files-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filePath = e.target.closest('.view-files-btn').getAttribute('data-path');
                this.openCompareView(filePath);
            });
        });

        // 绑定关闭按钮
        window.closeCompareView = this.closeCompareView.bind(this);
        
        // 初始化键盘快捷键
        this.initKeyboardShortcuts();
        
        console.log('FileManager: 初始化完成');
    }
};

// 导出到全局
window.FileManager = FileManager; 