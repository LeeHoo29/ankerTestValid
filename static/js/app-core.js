/**
 * 核心应用逻辑模块
 * 包含表单处理、任务状态管理、侧边栏功能等
 */

const AppCore = {
    // 应用状态
    state: {
        currentTaskId: null,
        statusInterval: null,
        isSidebarCollapsed: false,
        isMobile: false
    },

    // DOM元素引用
    elements: {},

    // 初始化应用
    initialize: function() {
        console.log('AppCore: 开始初始化应用');
        
        // 缓存DOM元素
        this.cacheElements();
        
        // 初始化侧边栏
        this.initializeSidebar();
        
        // 初始化表单
        this.initializeForm();
        
        // 初始化任务相关功能
        this.initializeTasks();
        
        // 初始化响应式处理
        this.initializeResponsive();
        
        // 初始化其他模块
        this.initializeModules();
        
        console.log('AppCore: 应用初始化完成');
    },

    // 缓存DOM元素
    cacheElements: function() {
        this.elements = {
            // 表单元素
            form: document.getElementById('commandForm'),
            taskTypeSelect: document.getElementById('task_type'),
            taskIdInput: document.getElementById('task_id'),
            outputTypeSelect: document.getElementById('output_type'),
            useParseCheckbox: document.getElementById('use_parse'),
            previewText: document.getElementById('preview-text'),
            submitButton: document.querySelector('.submit-btn'),

            // 结果显示元素
            resultContainer: document.getElementById('result-container'),
            resultTaskId: document.getElementById('result-task-id'),
            resultStatus: document.getElementById('result-status'),
            resultDuration: document.getElementById('result-duration'),
            commandOutput: document.getElementById('command-output'),

            // 侧边栏元素
            sidebar: document.getElementById('sidebar'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sidebarOverlay: document.getElementById('sidebarOverlay'),
            mainContent: document.querySelector('.main-content'),
            taskCountBadge: document.getElementById('taskCountBadge'),
            refreshBtn: document.getElementById('refresh-completed-btn')
        };
    },

    // 初始化侧边栏功能
    initializeSidebar: function() {
        // 更新任务数量
        this.updateTaskCount();
        
        // 绑定侧边栏切换事件
        this.elements.sidebarToggle.addEventListener('click', () => {
            if (this.state.isMobile) {
                this.toggleSidebarMobile();
            } else {
                this.toggleSidebarDesktop();
            }
        });

        // 绑定侧边栏覆盖层事件
        this.elements.sidebarOverlay.addEventListener('click', () => {
            this.closeSidebarMobile();
        });

        // 绑定刷新按钮
        this.elements.refreshBtn.addEventListener('click', () => {
            location.reload();
        });
    },

    // 初始化表单功能
    initializeForm: function() {
        // 绑定表单事件监听器
        this.elements.taskTypeSelect.addEventListener('change', Utils.updateCommandPreview);
        this.elements.taskIdInput.addEventListener('input', Utils.updateCommandPreview);
        this.elements.outputTypeSelect.addEventListener('change', Utils.updateCommandPreview);
        this.elements.useParseCheckbox.addEventListener('change', Utils.updateCommandPreview);

        // 绑定表单提交
        this.elements.form.addEventListener('submit', this.handleFormSubmit.bind(this));

        // 初始化命令预览
        Utils.updateCommandPreview();

        // 初始化提交按钮状态
        this.updateSubmitButtonState();
    },

    // 初始化任务相关功能
    initializeTasks: function() {
        // 绑定重新运行按钮
        document.querySelectorAll('.rerun-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskType = e.target.getAttribute('data-task-type');
                const jobId = e.target.getAttribute('data-job-id');
                
                // 填充表单
                this.elements.taskTypeSelect.value = taskType;
                this.elements.taskIdInput.value = jobId;
                Utils.updateCommandPreview();
                
                // 在移动端关闭侧边栏
                if (this.state.isMobile) {
                    this.closeSidebarMobile();
                }
                
                Utils.showNotification(`已填充任务 ${jobId}，请检查参数后提交`, 'info');
            });
        });
    },

    // 初始化响应式处理
    initializeResponsive: function() {
        // 窗口大小改变处理
        window.addEventListener('resize', Utils.debounce(() => {
            this.handleResize();
        }, 250));
        
        // 初始检查
        this.handleResize();
    },

    // 初始化其他模块
    initializeModules: function() {
        // 初始化文件管理器
        FileManager.initialize();
        
        console.log('AppCore: 所有模块初始化完成');
    },

    // 检查是否有任务正在执行
    isTaskRunning: function() {
        return !!this.state.statusInterval && !!this.state.currentTaskId;
    },

    // 更新提交按钮状态
    updateSubmitButtonState: function() {
        if (!this.elements.submitButton) return;

        const isRunning = this.isTaskRunning();
        
        if (isRunning) {
            // 禁用提交按钮
            this.elements.submitButton.disabled = true;
            this.elements.submitButton.classList.add('disabled');
            this.elements.submitButton.innerHTML = '<i class="fas fa-hourglass-half fa-spin"></i> 任务执行中...';
            this.elements.submitButton.title = '当前有任务正在执行，请等待完成后再提交新任务';
        } else {
            // 启用提交按钮
            this.elements.submitButton.disabled = false;
            this.elements.submitButton.classList.remove('disabled');
            this.elements.submitButton.innerHTML = '<i class="fas fa-rocket"></i> 执行命令';
            this.elements.submitButton.title = '提交新任务';
        }
    },

    // 表单提交处理
    handleFormSubmit: function(e) {
        e.preventDefault();
        
        // 检查是否有任务正在执行
        if (this.isTaskRunning()) {
            Utils.showNotification('当前有任务正在执行，请等待完成后再提交新任务', 'warning');
            console.warn('AppCore: 尝试在任务执行中提交新任务，已阻止');
            return;
        }
        
        // 获取任务ID
        const taskId = this.elements.taskIdInput.value.trim();
        if (!taskId) {
            Utils.showNotification('请输入任务ID', 'warning');
            return;
        }
        
        // 先检查任务是否已存在
        this.checkTaskExists(taskId)
            .then(result => {
                if (result.exists) {
                    // 任务已存在，显示确认对话框
                    this.showTaskExistsConfirmDialog(result, () => {
                        // 用户确认继续执行
                        this.submitForm();
                    });
                } else {
                    // 任务不存在，直接提交
                    this.submitForm();
                }
            })
            .catch(error => {
                console.error('检查任务存在性失败:', error);
                Utils.showNotification('检查任务状态失败，请重试', 'error');
            });
    },

    // 检查任务是否已存在
    checkTaskExists: function(taskId) {
        return fetch(`/api/check_task_exists?task_id=${encodeURIComponent(taskId)}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || '检查失败');
                }
                return data;
            });
    },

    // 显示任务已存在的确认对话框
    showTaskExistsConfirmDialog: function(taskInfo, onConfirm) {
        const taskId = taskInfo.task_id;
        const info = taskInfo.task_info;
        const taskType = info.task_type || '未知';
        const lastUpdated = info.last_updated || '未知时间';
        
        // 创建确认对话框
        const dialogHTML = `
            <div id="task-exists-dialog" class="task-exists-overlay">
                <div class="task-exists-dialog">
                    <div class="dialog-header">
                        <h3><i class="fas fa-exclamation-triangle"></i> 任务已存在</h3>
                    </div>
                    <div class="dialog-content">
                        <p>任务ID <strong>${taskId}</strong> 已经被执行过：</p>
                        <div class="task-exists-info">
                            <div class="info-row">
                                <span class="label">任务类型:</span>
                                <span class="value">${taskType}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">上次执行:</span>
                                <span class="value">${lastUpdated}</span>
                            </div>
                        </div>
                        <p class="warning-text">
                            <i class="fas fa-info-circle"></i> 
                            重新执行会覆盖已有的结果文件
                        </p>
                    </div>
                    <div class="dialog-actions">
                        <button type="button" class="dialog-btn cancel-btn" onclick="AppCore.closeTaskExistsDialog()">
                            <i class="fas fa-times"></i> 取消
                        </button>
                        <button type="button" class="dialog-btn confirm-btn" onclick="AppCore.confirmTaskReexecution()">
                            <i class="fas fa-check"></i> 继续执行
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        
        // 保存确认回调
        this._taskExistsConfirmCallback = onConfirm;
        
        // 显示对话框
        setTimeout(() => {
            document.getElementById('task-exists-dialog').classList.add('show');
        }, 10);
    },

    // 关闭任务存在确认对话框
    closeTaskExistsDialog: function() {
        const dialog = document.getElementById('task-exists-dialog');
        if (dialog) {
            dialog.classList.remove('show');
            setTimeout(() => {
                dialog.remove();
            }, 300);
        }
        this._taskExistsConfirmCallback = null;
    },

    // 确认重新执行任务
    confirmTaskReexecution: function() {
        if (this._taskExistsConfirmCallback) {
            this._taskExistsConfirmCallback();
        }
        this.closeTaskExistsDialog();
    },

    // 实际提交表单
    submitForm: function() {
        const formData = new FormData(this.elements.form);
        
        // 更新提交按钮状态
        this.updateSubmitButtonState();
        
        // 显示加载状态
        Utils.updateStatus('pending');
        this.elements.resultContainer.style.display = 'block';
        this.elements.commandOutput.textContent = '正在提交任务...';
        
        fetch('/submit', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.state.currentTaskId = data.task_id;
                this.elements.resultTaskId.textContent = data.task_id;
                
                // 开始轮询状态
                this.startStatusPolling();
                
                // 更新提交按钮状态
                this.updateSubmitButtonState();
                
                Utils.showNotification('任务已提交，正在执行...', 'info');
            } else {
                Utils.updateStatus('error');
                this.elements.commandOutput.textContent = '错误: ' + data.error;
                Utils.showNotification(data.error, 'error');
                
                // 重置提交按钮状态
                this.updateSubmitButtonState();
            }
        })
        .catch(error => {
            Utils.updateStatus('error');
            this.elements.commandOutput.textContent = '提交失败: ' + error.message;
            Utils.showNotification('提交失败', 'error');
            
            // 重置提交按钮状态
            this.updateSubmitButtonState();
        });
    },

    // 开始状态轮询
    startStatusPolling: function() {
        if (this.state.statusInterval) {
            clearInterval(this.state.statusInterval);
        }
        
        this.state.statusInterval = setInterval(() => {
            this.checkTaskStatus();
        }, 1000);
        
        // 更新提交按钮状态
        this.updateSubmitButtonState();
    },

    // 停止状态轮询
    stopStatusPolling: function() {
        if (this.state.statusInterval) {
            clearInterval(this.state.statusInterval);
            this.state.statusInterval = null;
        }
        
        // 清除当前任务ID
        this.state.currentTaskId = null;
        
        // 更新提交按钮状态
        this.updateSubmitButtonState();
    },

    // 检查任务状态
    checkTaskStatus: function() {
        if (!this.state.currentTaskId) return;
        
        fetch(`/status/${this.state.currentTaskId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Utils.updateStatus(data.status);
                    this.elements.resultDuration.textContent = data.duration || '计算中...';
                    
                    // 更新输出
                    this.elements.commandOutput.textContent = data.output;
                    this.elements.commandOutput.scrollTop = this.elements.commandOutput.scrollHeight;
                    
                    // 如果任务完成，停止轮询
                    if (['completed', 'failed', 'error'].includes(data.status)) {
                        this.stopStatusPolling();
                        
                        if (data.status === 'completed') {
                            Utils.showNotification('任务执行成功！', 'success');
                            // 任务完成后刷新侧边栏
                            setTimeout(() => {
                                location.reload();
                            }, 1000);
                        } else {
                            Utils.showNotification('任务执行失败', 'error');
                        }
                    }
                }
            })
            .catch(error => {
                console.error('获取状态失败:', error);
            });
    },

    // 更新任务数量
    updateTaskCount: function() {
        const taskCards = document.querySelectorAll('.completed-task-card');
        const count = taskCards.length;
        this.elements.taskCountBadge.textContent = count > 99 ? '99+' : count.toString();
    },

    // 桌面端侧边栏切换
    toggleSidebarDesktop: function() {
        this.state.isSidebarCollapsed = !this.state.isSidebarCollapsed;
        
        this.elements.sidebar.classList.toggle('collapsed');
        this.elements.mainContent.classList.toggle('sidebar-collapsed');
        
        const icon = this.elements.sidebarToggle.querySelector('i');
        if (this.state.isSidebarCollapsed) {
            icon.className = 'fas fa-chevron-right';
        } else {
            icon.className = 'fas fa-chevron-left';
        }
        
        // 保存状态
        Utils.storage.set('sidebar-collapsed', this.state.isSidebarCollapsed);
    },

    // 移动端侧边栏切换
    toggleSidebarMobile: function() {
        if (this.elements.sidebar.classList.contains('open')) {
            this.closeSidebarMobile();
        } else {
            this.openSidebarMobile();
        }
    },

    // 打开移动端侧边栏
    openSidebarMobile: function() {
        this.elements.sidebar.classList.add('open');
        this.elements.sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    },

    // 关闭移动端侧边栏
    closeSidebarMobile: function() {
        this.elements.sidebar.classList.remove('open');
        this.elements.sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    },

    // 响应式处理
    handleResize: function() {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile !== this.state.isMobile) {
            this.state.isMobile = isMobile;
            
            if (isMobile) {
                // 切换到移动端模式
                this.elements.sidebar.classList.remove('open', 'collapsed');
                this.elements.sidebarOverlay.classList.remove('active');
                this.elements.mainContent.classList.remove('sidebar-collapsed');
                document.body.style.overflow = '';
            } else {
                // 切换到桌面端模式
                this.elements.sidebar.classList.remove('open');
                this.elements.sidebarOverlay.classList.remove('active');
                document.body.style.overflow = '';
                
                // 恢复桌面端侧边栏状态
                const savedCollapsed = Utils.storage.get('sidebar-collapsed', false);
                if (savedCollapsed) {
                    this.elements.sidebar.classList.add('collapsed');
                    this.elements.mainContent.classList.add('sidebar-collapsed');
                    this.state.isSidebarCollapsed = true;
                }
            }
        }
    },

    // 获取应用状态
    getState: function() {
        return {
            currentTaskId: this.state.currentTaskId,
            isSidebarCollapsed: this.state.isSidebarCollapsed,
            isMobile: this.state.isMobile,
            hasActivePolling: !!this.state.statusInterval
        };
    },

    // 清理资源
    cleanup: function() {
        // 停止状态轮询
        this.stopStatusPolling();
        
        // 清理文件管理器
        if (window.FileManager && FileManager.state.isCompareViewOpen) {
            FileManager.closeCompareView();
        }
        
        // 清理面板调整器
        if (window.PanelResizer) {
            PanelResizer.cleanup();
        }
        
        console.log('AppCore: 资源清理完成');
    }
};

// 页面加载时初始化应用
document.addEventListener('DOMContentLoaded', function() {
    AppCore.initialize();
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', function() {
    AppCore.cleanup();
});

// 导出到全局
window.AppCore = AppCore; 