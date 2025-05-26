/**
 * HTML渲染器模块
 * 包含全局缓存管理、iframe处理、预加载等功能
 */

const HtmlRenderer = {
    // 全局缓存管理 - 更激进的策略
    GlobalCache: {
        fileContent: new Map(),
        iframeInstances: new Map(),
        blobUrls: new Map(), // 添加blob URL管理
        preloadQueue: [],
        isPreloading: false,
        
        // 配置
        config: {
            maxIframes: 12, // 增加iframe缓存数量
            preloadAll: true, // 预加载所有文件
            instantSwitch: true // 即时切换
        },
        
        // 检查是否已缓存
        hasFile: function(filePath) {
            return this.fileContent.has(filePath);
        },
        
        // 获取缓存的文件内容
        getFile: function(filePath) {
            return this.fileContent.get(filePath);
        },
        
        // 缓存文件内容
        setFile: function(filePath, content) {
            this.fileContent.set(filePath, {
                content: content,
                timestamp: Date.now(),
                size: new Blob([content]).size,
                accessed: Date.now()
            });
        },
        
        // 获取iframe实例
        getIframe: function(filePath) {
            const cached = this.iframeInstances.get(filePath);
            if (cached) {
                cached.lastUsed = Date.now();
                // 检查blob URL是否还有效
                if (cached.blobUrl && this.blobUrls.has(filePath)) {
                    const clonedContainer = cached.container.cloneNode(true);
                    // 确保iframe的src是正确的
                    const iframe = clonedContainer.querySelector('iframe');
                    if (iframe) {
                        iframe.src = cached.blobUrl;
                    }
                    return clonedContainer;
                }
            }
            return null;
        },
        
        // 缓存iframe实例
        setIframe: function(filePath, container, blobUrl) {
            // 清理超出限制的iframe
            if (this.iframeInstances.size >= this.config.maxIframes) {
                const entries = Array.from(this.iframeInstances.entries());
                entries.sort((a, b) => a[1].lastUsed - b[1].lastUsed);
                const toRemove = entries.slice(0, Math.floor(this.config.maxIframes / 3));
                toRemove.forEach(([key, value]) => {
                    // 清理旧的blob URL
                    if (value.blobUrl) {
                        URL.revokeObjectURL(value.blobUrl);
                        this.blobUrls.delete(key);
                    }
                    this.iframeInstances.delete(key);
                });
            }
            
            this.iframeInstances.set(filePath, {
                container: container.cloneNode(true),
                blobUrl: blobUrl, // 保存blob URL引用
                created: Date.now(),
                lastUsed: Date.now()
            });
            
            // 记录blob URL
            if (blobUrl) {
                this.blobUrls.set(filePath, blobUrl);
            }
        },
        
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
            // 清理所有blob URLs
            this.blobUrls.forEach((blobUrl) => {
                URL.revokeObjectURL(blobUrl);
            });
            this.fileContent.clear();
            this.iframeInstances.clear();
            this.blobUrls.clear();
        }
    },

    // 超快速HTML文件加载 - 0延迟版本
    loadCompareHtmlFile: function(filePath) {
        const htmlContent = document.getElementById('compare-html-content');
        
        if (!filePath) {
            htmlContent.innerHTML = `
                <div class="compare-loading">
                    <i class="fas fa-file-code"></i>
                    <div class="compare-loading-text">请选择HTML文件查看</div>
                </div>
            `;
            return;
        }

        // 总是先显示加载状态，即使是缓存
        this.showInstantLoading(htmlContent, filePath);

        // 第一优先级：iframe缓存 - 极速切换但有动画
        const cachedIframe = this.GlobalCache.getIframe(filePath);
        if (cachedIframe) {
            console.log(`🚀 即时切换iframe: ${filePath}`);
            // 短暂延迟以显示切换动画
            setTimeout(() => {
                htmlContent.innerHTML = '';
                htmlContent.appendChild(cachedIframe);
                this.showSwitchSuccess(htmlContent);
            }, 80); // 增加到80ms，让用户能看到切换
            
            // 启动后台预加载下一个文件
            this.backgroundPreloadNext(filePath);
            return;
        }

        // 第二优先级：文件内容缓存 - 快速渲染
        if (this.GlobalCache.hasFile(filePath)) {
            console.log(`⚡ 快速渲染: ${filePath}`);
            const cached = this.GlobalCache.getFile(filePath);
            // 延长缓存渲染的显示时间
            setTimeout(() => {
                this.renderHtmlInstantly(htmlContent, filePath, cached.content);
            }, 120); // 增加到120ms
            return;
        }

        // 第三优先级：网络加载 - 显示加载动画
        console.log(`🌐 网络加载: ${filePath}`);
        setTimeout(() => {
            this.showOptimizedLoading(htmlContent, filePath);
            this.fetchAndRenderHtml(filePath, htmlContent);
        }, 100);
    },

    // 新增：瞬间加载动画
    showInstantLoading: function(container, filePath) {
        const fileName = filePath.split('/').pop();
        container.innerHTML = `
            <div class="instant-loading enhanced">
                <div class="loading-indicator">
                    <div class="indicator-ring"></div>
                    <div class="indicator-pulse"></div>
                    <i class="fas fa-bolt"></i>
                </div>
                <div class="loading-text">正在加载...</div>
                <div class="loading-file">${fileName}</div>
            </div>
        `;
    },

    // 新增：切换成功动画
    showSwitchSuccess: function(container) {
        // 在iframe上添加成功切换的效果
        const iframe = container.querySelector('iframe');
        if (iframe) {
            iframe.style.opacity = '0';
            iframe.style.transform = 'scale(0.95)';
            
            // 淡入动画
            setTimeout(() => {
                iframe.style.transition = 'all 0.2s ease-out';
                iframe.style.opacity = '1';
                iframe.style.transform = 'scale(1)';
            }, 10);
        }
    },

    // 即时渲染HTML - 增强版本
    renderHtmlInstantly: function(container, filePath, content) {
        // 增强的加载提示 - 显示更长时间
        container.innerHTML = `
            <div class="instant-loading cache-loading">
                <div class="cache-indicator">
                    <i class="fas fa-lightning-bolt"></i>
                    <div class="cache-rings">
                        <div class="cache-ring"></div>
                        <div class="cache-ring"></div>
                    </div>
                </div>
                <div class="loading-text">缓存快速加载中...</div>
            </div>
        `;
        
        // 延迟渲染，确保用户能看到加载状态
        setTimeout(() => {
            this.createAndCacheIframe(container, filePath, content);
        }, 80); // 从50ms增加到80ms
    },

    // 创建并缓存iframe
    createAndCacheIframe: function(container, filePath, content) {
        // 创建iframe容器
        const iframeContainer = document.createElement('div');
        iframeContainer.className = 'instant-iframe-container';
        iframeContainer.style.cssText = `
            width: 100%;
            height: 100%;
            position: relative;
            background: #f8fafc;
            border-radius: 8px;
            overflow: hidden;
        `;
        
        // 创建iframe
        const blob = new Blob([content], { type: 'text/html' });
        const blobUrl = URL.createObjectURL(blob);
        
        const iframe = document.createElement('iframe');
        iframe.className = 'instant-html-frame';
        iframe.src = blobUrl;
        iframe.style.cssText = `
            width: 100%;
            height: 100%;
            border: none;
            background: white;
            border-radius: 6px;
            display: block;
            opacity: 1;
        `;
        
        // 立即显示
        iframeContainer.appendChild(iframe);
        container.innerHTML = '';
        container.appendChild(iframeContainer);
        
        // 缓存iframe实例，保存blob URL引用
        this.GlobalCache.setIframe(filePath, iframeContainer, blobUrl);
        
        // iframe加载完成处理
        iframe.onload = function() {
            console.log(`✅ iframe缓存完成: ${filePath}`);
            // 不立即清理blob URL，而是由缓存管理器统一管理
        };
        
        iframe.onerror = function() {
            console.error(`❌ iframe渲染失败: ${filePath}`);
            // 出错时清理blob URL
            URL.revokeObjectURL(blobUrl);
            // 从缓存中移除
            HtmlRenderer.GlobalCache.clearFile(filePath);
        };
    },

    // 网络获取并渲染
    fetchAndRenderHtml: function(filePath, container) {
        fetch(`/api/file_content?path=${encodeURIComponent(filePath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 立即缓存
                    this.GlobalCache.setFile(filePath, data.content);
                    
                    // 立即渲染
                    this.createAndCacheIframe(container, filePath, data.content);
                    
                    console.log(`📦 网络加载完成并缓存: ${filePath}`);
                    
                    // 触发后台预加载
                    this.backgroundPreloadNext(filePath);
                    
                } else {
                    this.showErrorState(container, `加载失败: ${data.error}`, filePath);
                }
            })
            .catch(error => {
                this.showErrorState(container, `网络错误: ${error.message}`, filePath);
            });
    },

    // 优化的加载动画
    showOptimizedLoading: function(container, filePath) {
        container.innerHTML = `
            <div class="optimized-loading">
                <div class="fast-spinner">
                    <div class="fast-ring"></div>
                    <div class="fast-ring"></div>
                    <div class="fast-ring"></div>
                </div>
                <div class="loading-text">正在获取文件...</div>
                <div class="loading-file">${filePath.split('/').pop()}</div>
            </div>
        `;
    },

    // 后台预加载下一个文件
    backgroundPreloadNext: function(currentFilePath) {
        const htmlSelector = document.getElementById('compare-html-selector');
        if (!htmlSelector) return;
        
        const options = Array.from(htmlSelector.options);
        const currentIndex = options.findIndex(opt => opt.value === currentFilePath);
        
        // 预加载下一个和上一个文件
        const filesToPreload = [];
        if (currentIndex > 0) {
            filesToPreload.push(options[currentIndex - 1].value);
        }
        if (currentIndex < options.length - 1) {
            filesToPreload.push(options[currentIndex + 1].value);
        }
        
        filesToPreload.forEach(filePath => {
            if (filePath && !this.GlobalCache.hasFile(filePath)) {
                setTimeout(() => this.preloadSingleFile(filePath), 100);
            }
        });
    },

    // 预加载单个文件
    preloadSingleFile: function(filePath) {
        if (this.GlobalCache.hasFile(filePath)) return;
        
        fetch(`/api/file_content?path=${encodeURIComponent(filePath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.GlobalCache.setFile(filePath, data.content);
                    console.log(`🔄 后台预加载: ${filePath.split('/').pop()}`);
                }
            })
            .catch(error => {
                console.warn(`预加载失败: ${filePath}`, error);
            });
    },

    // 全面预加载所有HTML文件
    preloadAllHtmlFiles: function(files) {
        const htmlFiles = files.filter(file => 
            file.name.toLowerCase().endsWith('.html') || 
            file.name.toLowerCase().endsWith('.htm')
        );
        
        console.log(`🚀 开始预加载 ${htmlFiles.length} 个HTML文件`);
        
        // 立即预加载前3个
        htmlFiles.slice(0, 3).forEach((file, index) => {
            setTimeout(() => {
                if (!this.GlobalCache.hasFile(file.path)) {
                    this.preloadSingleFile(file.path);
                }
            }, index * 100);
        });
        
        // 延迟预加载其余文件
        if (htmlFiles.length > 3) {
            setTimeout(() => {
                htmlFiles.slice(3).forEach((file, index) => {
                    setTimeout(() => {
                        if (!this.GlobalCache.hasFile(file.path)) {
                            this.preloadSingleFile(file.path);
                        }
                    }, index * 200);
                });
            }, 1000);
        }
    },

    // 显示错误状态
    showErrorState: function(container, message, filePath) {
        container.innerHTML = `
            <div class="compare-loading error">
                <i class="fas fa-exclamation-triangle"></i>
                <div class="compare-loading-text">${message}</div>
                <button class="retry-btn" onclick="HtmlRenderer.loadCompareHtmlFile('${filePath}')">
                    <i class="fas fa-redo"></i> 重试
                </button>
            </div>
        `;
    },

    // 从缓存渲染JSON
    renderJsonFromCache: function(container, filePath) {
        const cached = this.GlobalCache.getFile(filePath);
        if (!cached) return;
        
        // 显示简短的缓存加载提示
        container.innerHTML = `
            <div class="instant-loading">
                <div class="instant-dot"></div>
                <span>从缓存快速加载...</span>
            </div>
        `;
        
        // 直接渲染内容
        setTimeout(() => {
            JsonEditor.render(container, cached.content);
        }, 50);
    },

    // 加载JSON文件 - 保持兼容性
    loadCompareJsonFile: function(filePath) {
        const jsonContent = document.getElementById('compare-json-content');
        
        if (!filePath) {
            jsonContent.innerHTML = `
                <div class="compare-loading">
                    <i class="fas fa-file-code"></i>
                    <div class="compare-loading-text">请选择JSON文件查看</div>
                </div>
            `;
            return;
        }

        // 检查全局缓存
        if (this.GlobalCache.hasFile(filePath)) {
            console.log('从缓存加载JSON文件:', filePath);
            this.renderJsonFromCache(jsonContent, filePath);
            return;
        }

        // 显示快速加载动画
        jsonContent.innerHTML = `
            <div class="optimized-loading">
                <div class="fast-spinner">
                    <div class="fast-ring"></div>
                    <div class="fast-ring"></div>
                    <div class="fast-ring"></div>
                </div>
                <div class="loading-text">正在加载JSON文件...</div>
                <div class="loading-file">${filePath.split('/').pop()}</div>
            </div>
        `;

        const startTime = Utils.performance.now();
        
        fetch(`/api/file_content?path=${encodeURIComponent(filePath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 缓存文件内容
                    this.GlobalCache.setFile(filePath, data.content);

                    // 渲染JSON内容
                    JsonEditor.render(jsonContent, data.content);
                    
                    const loadTime = Math.round(Utils.performance.now() - startTime);
                    console.log(`JSON文件加载完成: ${filePath} (${loadTime}ms)`);
                    
                } else {
                    jsonContent.innerHTML = `
                        <div class="compare-loading error">
                            <i class="fas fa-exclamation-triangle"></i>
                            <div class="compare-loading-text">加载失败: ${data.error}</div>
                            <button class="retry-btn" onclick="HtmlRenderer.loadCompareJsonFile('${filePath}')">
                                <i class="fas fa-redo"></i> 重试
                            </button>
                        </div>
                    `;
                }
            })
            .catch(error => {
                jsonContent.innerHTML = `
                    <div class="compare-loading error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <div class="compare-loading-text">网络错误: ${error.message}</div>
                        <button class="retry-btn" onclick="HtmlRenderer.loadCompareJsonFile('${filePath}')">
                            <i class="fas fa-redo"></i> 重试
                        </button>
                    </div>
                `;
            });
    },

    // 调试工具：获取缓存状态
    getCacheStatus: function() {
        return {
            fileContentCount: this.GlobalCache.fileContent.size,
            iframeInstancesCount: this.GlobalCache.iframeInstances.size,
            blobUrlsCount: this.GlobalCache.blobUrls.size,
            cacheDetails: {
                files: Array.from(this.GlobalCache.fileContent.keys()),
                iframes: Array.from(this.GlobalCache.iframeInstances.keys()),
                blobUrls: Array.from(this.GlobalCache.blobUrls.keys())
            }
        };
    },

    // 调试工具：检查特定文件的缓存状态
    checkFileCache: function(filePath) {
        return {
            hasFileContent: this.GlobalCache.hasFile(filePath),
            hasIframeCache: this.GlobalCache.iframeInstances.has(filePath),
            hasBlobUrl: this.GlobalCache.blobUrls.has(filePath),
            blobUrl: this.GlobalCache.blobUrls.get(filePath)
        };
    },

    // 测试函数：验证缓存功能
    testCacheFunction: function() {
        console.group('🧪 HTML渲染器缓存测试');
        console.log('缓存状态:', this.getCacheStatus());
        
        // 测试每个缓存的文件
        this.GlobalCache.fileContent.forEach((value, key) => {
            console.log(`📁 ${key}:`, this.checkFileCache(key));
        });
        
        console.groupEnd();
    },

    // 输出到全局以供调试
    debug: {
        getCacheStatus: function() {
            return HtmlRenderer.getCacheStatus();
        },
        checkFile: function(filePath) {
            return HtmlRenderer.checkFileCache(filePath);
        },
        clearCache: function() {
            HtmlRenderer.GlobalCache.clearAll();
            console.log('✅ 缓存已手动清理');
        },
        testCache: function() {
            HtmlRenderer.testCacheFunction();
        }
    }
};

// 页面卸载时清理所有blob URLs
window.addEventListener('beforeunload', function() {
    if (window.HtmlRenderer && HtmlRenderer.GlobalCache) {
        console.log('清理HTML渲染器缓存...');
        HtmlRenderer.GlobalCache.clearAll();
    }
});

// 导出到全局
window.HtmlRenderer = HtmlRenderer; 