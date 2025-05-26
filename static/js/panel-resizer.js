/**
 * 面板拖拽调整大小功能模块
 * 支持实时拖拽、双击重置、窗口大小响应等功能
 */

const PanelResizer = {
    // 状态变量
    state: {
        isResizing: false,
        startX: 0,
        startLeftWidth: 0,
        startRightWidth: 0,
        resizer: null,
        leftPanel: null,
        rightPanel: null,
        containerWidth: 0
    },

    // 配置选项
    config: {
        minRatio: 0.2, // 最小宽度比例 20%
        maxRatio: 0.8, // 最大宽度比例 80%
        defaultRatio: 0.5, // 默认比例 50:50
        storageKey: 'compare-panel-ratio', // 本地存储键名
        animationDuration: 300 // 动画持续时间
    },

    // 初始化拖拽调整大小功能
    initialize: function() {
        this.state.resizer = document.getElementById('compareResizer');
        if (!this.state.resizer) return;

        const compareContainer = document.querySelector('.compare-main-content');
        const panels = compareContainer.querySelectorAll('.compare-panel');
        this.state.leftPanel = panels[0]; // HTML面板
        this.state.rightPanel = panels[1]; // JSON面板

        // 设置初始宽度比例（从本地存储或默认值）
        const savedRatio = Utils.storage.get(this.config.storageKey, this.config.defaultRatio);
        this.setPanelWidths(savedRatio);

        // 绑定事件
        this.bindEvents();
        
        console.log('PanelResizer: 初始化完成');
    },

    // 绑定所有事件
    bindEvents: function() {
        // 鼠标拖拽事件
        this.state.resizer.addEventListener('mousedown', this.startResize.bind(this));
        document.addEventListener('mousemove', this.doResize.bind(this));
        document.addEventListener('mouseup', this.stopResize.bind(this));
        
        // 双击重置为50:50
        this.state.resizer.addEventListener('dblclick', this.resetPanelWidths.bind(this));
        
        // 窗口大小改变时重新计算
        window.addEventListener('resize', Utils.debounce(this.handleWindowResize.bind(this), 250));

        // 触摸事件支持（移动端）
        this.state.resizer.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
    },

    // 开始拖拽
    startResize: function(e) {
        if (!e.target.closest('.compare-resizer')) return;

        this.state.isResizing = true;
        this.state.startX = e.clientX;
        
        const compareContainer = document.querySelector('.compare-main-content');
        this.state.containerWidth = compareContainer.offsetWidth;
        this.state.startLeftWidth = this.state.leftPanel.offsetWidth;
        this.state.startRightWidth = this.state.rightPanel.offsetWidth;
        
        // 添加拖拽状态样式
        document.body.classList.add('resizing');
        this.state.resizer.classList.add('dragging');
        
        // 防止选择文本
        e.preventDefault();
        
        // 显示拖拽指示器
        this.showResizeIndicator();
        
        console.log('开始调整面板大小');
    },

    // 执行拖拽
    doResize: function(e) {
        if (!this.state.isResizing) return;
        
        const deltaX = e.clientX - this.state.startX;
        const newLeftWidth = this.state.startLeftWidth + deltaX;
        const newRightWidth = this.state.startRightWidth - deltaX;
        
        // 计算新的比例
        const leftRatio = newLeftWidth / this.state.containerWidth;
        
        // 限制最小和最大宽度
        if (leftRatio >= this.config.minRatio && leftRatio <= this.config.maxRatio) {
            // 实时更新面板宽度
            this.setPanelWidths(leftRatio);
            
            // 更新拖拽指示器
            this.updateResizeIndicator(leftRatio);
        }
    },

    // 停止拖拽
    stopResize: function(e) {
        if (!this.state.isResizing) return;
        
        this.state.isResizing = false;
        
        // 移除拖拽状态样式
        document.body.classList.remove('resizing');
        this.state.resizer.classList.remove('dragging');
        
        // 保存用户偏好的比例
        const leftRatio = this.state.leftPanel.offsetWidth / this.state.containerWidth;
        Utils.storage.set(this.config.storageKey, leftRatio);
        
        console.log(`面板大小调整完成: ${Math.round(leftRatio * 100)}% : ${Math.round((1 - leftRatio) * 100)}%`);
        
        // 隐藏指示器并显示完成提示
        this.hideResizeIndicator();
        this.showResizeCompleteIndicator(leftRatio);
    },

    // 触摸开始处理
    handleTouchStart: function(e) {
        if (!e.target.closest('.compare-resizer')) return;
        
        const touch = e.touches[0];
        this.startResize({ 
            clientX: touch.clientX, 
            target: e.target,
            preventDefault: () => e.preventDefault()
        });
    },

    // 触摸移动处理
    handleTouchMove: function(e) {
        if (!this.state.isResizing) return;
        
        const touch = e.touches[0];
        this.doResize({ clientX: touch.clientX });
        e.preventDefault();
    },

    // 触摸结束处理
    handleTouchEnd: function(e) {
        if (!this.state.isResizing) return;
        this.stopResize(e);
    },

    // 设置面板宽度比例
    setPanelWidths: function(leftRatio) {
        if (!this.state.leftPanel || !this.state.rightPanel) return;
        
        const rightRatio = 1 - leftRatio;
        this.state.leftPanel.style.flex = `0 0 ${leftRatio * 100}%`;
        this.state.rightPanel.style.flex = `0 0 ${rightRatio * 100}%`;
    },

    // 重置为默认比例（50:50）
    resetPanelWidths: function() {
        const defaultRatio = this.config.defaultRatio;
        
        // 添加过渡动画
        this.state.leftPanel.style.transition = `flex ${this.config.animationDuration}ms ease`;
        this.state.rightPanel.style.transition = `flex ${this.config.animationDuration}ms ease`;
        
        this.setPanelWidths(defaultRatio);
        Utils.storage.set(this.config.storageKey, defaultRatio);
        
        // 显示重置提示
        Utils.showNotification('面板大小已重置为 50:50', 'info');
        
        // 移除过渡动画
        setTimeout(() => {
            this.state.leftPanel.style.transition = '';
            this.state.rightPanel.style.transition = '';
        }, this.config.animationDuration);
        
        console.log('面板比例已重置为 50:50');
    },

    // 窗口大小改变处理
    handleWindowResize: function() {
        if (!this.state.leftPanel || !this.state.rightPanel) return;
        
        // 重新计算容器宽度
        const compareContainer = document.querySelector('.compare-main-content');
        this.state.containerWidth = compareContainer.offsetWidth;
        
        // 保持当前比例
        const currentRatio = Utils.storage.get(this.config.storageKey, this.config.defaultRatio);
        this.setPanelWidths(currentRatio);
        
        console.log('窗口大小改变，重新调整面板比例');
    },

    // 显示拖拽指示器
    showResizeIndicator: function() {
        let indicator = document.querySelector('.resize-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'resize-indicator';
            document.body.appendChild(indicator);
        }
        indicator.style.display = 'block';
    },

    // 更新拖拽指示器
    updateResizeIndicator: function(leftRatio) {
        const percentage = Math.round(leftRatio * 100);
        const indicator = document.querySelector('.resize-indicator');
        
        if (indicator) {
            indicator.textContent = `${percentage}% : ${100 - percentage}%`;
            
            // 计算指示器位置
            const compareContainer = document.querySelector('.compare-main-content');
            const containerRect = compareContainer.getBoundingClientRect();
            const resizerRect = this.state.resizer.getBoundingClientRect();
            
            indicator.style.left = (resizerRect.left + resizerRect.width / 2) + 'px';
            indicator.style.top = (containerRect.top + containerRect.height / 2) + 'px';
        }
    },

    // 隐藏拖拽指示器
    hideResizeIndicator: function() {
        const indicator = document.querySelector('.resize-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    },

    // 显示调整完成指示器
    showResizeCompleteIndicator: function(leftRatio) {
        const percentage = Math.round(leftRatio * 100);
        Utils.showNotification(`面板比例调整为: ${percentage}% : ${100 - percentage}%`, 'success');
    },

    // 获取当前面板比例
    getCurrentRatio: function() {
        if (!this.state.leftPanel || !this.state.containerWidth) return this.config.defaultRatio;
        return this.state.leftPanel.offsetWidth / this.state.containerWidth;
    },

    // 设置面板比例（动画版本）
    setRatioAnimated: function(ratio, duration = this.config.animationDuration) {
        if (ratio < this.config.minRatio || ratio > this.config.maxRatio) {
            console.warn('PanelResizer: 比例超出范围，使用默认值');
            ratio = this.config.defaultRatio;
        }

        // 添加过渡动画
        this.state.leftPanel.style.transition = `flex ${duration}ms ease`;
        this.state.rightPanel.style.transition = `flex ${duration}ms ease`;
        
        this.setPanelWidths(ratio);
        Utils.storage.set(this.config.storageKey, ratio);
        
        // 移除过渡动画
        setTimeout(() => {
            this.state.leftPanel.style.transition = '';
            this.state.rightPanel.style.transition = '';
        }, duration);
    },

    // 清理功能
    cleanup: function() {
        if (this.state.resizer) {
            this.state.resizer.removeEventListener('mousedown', this.startResize);
            this.state.resizer.removeEventListener('dblclick', this.resetPanelWidths);
            this.state.resizer.removeEventListener('touchstart', this.handleTouchStart);
        }
        
        document.removeEventListener('mousemove', this.doResize);
        document.removeEventListener('mouseup', this.stopResize);
        document.removeEventListener('touchmove', this.handleTouchMove);
        document.removeEventListener('touchend', this.handleTouchEnd);
        window.removeEventListener('resize', this.handleWindowResize);
        
        // 清理拖拽状态
        document.body.classList.remove('resizing');
        if (this.state.resizer) {
            this.state.resizer.classList.remove('dragging');
        }
        
        // 清理指示器
        this.hideResizeIndicator();
        const indicator = document.querySelector('.resize-indicator');
        if (indicator) {
            indicator.remove();
        }
        
        // 重置状态
        this.state.isResizing = false;
        this.state.resizer = null;
        this.state.leftPanel = null;
        this.state.rightPanel = null;
        
        console.log('PanelResizer: 清理完成');
    }
};

// 导出到全局
window.PanelResizer = PanelResizer; 