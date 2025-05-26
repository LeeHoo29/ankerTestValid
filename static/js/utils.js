/**
 * 通用工具函数模块
 * 提供应用全局使用的工具函数
 */

const Utils = {
    // 显示通知
    showNotification: function(message, type = 'info') {
        // 简单的通知实现
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    },

    // 更新命令预览
    updateCommandPreview: function() {
        const taskTypeSelect = document.getElementById('task_type');
        const taskIdInput = document.getElementById('task_id');
        const outputTypeSelect = document.getElementById('output_type');
        const useParseCheckbox = document.getElementById('use_parse');
        const previewText = document.getElementById('preview-text');
        
        const taskType = taskTypeSelect.value || '[任务类型]';
        const taskId = taskIdInput.value || '[任务ID]';
        const outputType = outputTypeSelect.value;
        const withParse = useParseCheckbox.checked ? ' --with-parse' : '';
        
        const command = `python3 src/azure_resource_reader.py ${taskType} ${taskId} ${outputType}${withParse}`;
        previewText.textContent = command;
    },

    // 更新状态显示
    updateStatus: function(status) {
        const resultStatus = document.getElementById('result-status');
        resultStatus.textContent = status;
        resultStatus.className = `status ${status}`;
    },

    // 格式化文件大小
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 生成唯一ID
    generateId: function(prefix = 'id') {
        return prefix + '_' + Math.random().toString(36).substr(2, 9);
    },

    // 防抖函数
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流函数
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // 深拷贝
    deepClone: function(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    },

    // 解析URL参数
    parseUrlParams: function(url = window.location.href) {
        const params = {};
        const urlObj = new URL(url);
        for (const [key, value] of urlObj.searchParams) {
            params[key] = value;
        }
        return params;
    },

    // 本地存储封装
    storage: {
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.error('localStorage.setItem error:', e);
                return false;
            }
        },

        get: function(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.error('localStorage.getItem error:', e);
                return defaultValue;
            }
        },

        remove: function(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (e) {
                console.error('localStorage.removeItem error:', e);
                return false;
            }
        },

        clear: function() {
            try {
                localStorage.clear();
                return true;
            } catch (e) {
                console.error('localStorage.clear error:', e);
                return false;
            }
        }
    },

    // 性能监控
    performance: {
        mark: function(name) {
            if (window.performance && window.performance.mark) {
                window.performance.mark(name);
            }
        },

        measure: function(name, startMark, endMark) {
            if (window.performance && window.performance.measure) {
                try {
                    window.performance.measure(name, startMark, endMark);
                    const measures = window.performance.getEntriesByName(name);
                    return measures.length > 0 ? measures[measures.length - 1].duration : 0;
                } catch (e) {
                    console.warn('Performance measurement error:', e);
                    return 0;
                }
            }
            return 0;
        },

        now: function() {
            return window.performance && window.performance.now ? 
                window.performance.now() : Date.now();
        }
    }
};

// 导出到全局
window.Utils = Utils; 