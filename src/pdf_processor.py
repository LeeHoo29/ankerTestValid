#!/usr/bin/env python3
"""
PDF内容提取和处理工具
"""
import os
import sys
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import PyPDF2

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF文档处理器"""
    
    def __init__(self, pdf_path: str):
        """
        初始化PDF处理器
        
        Args:
            pdf_path: PDF文件路径
        """
        self.pdf_path = pdf_path
        self.text_content = ""
        self.metadata = {}
        self.page_count = 0
        
    def extract_text(self) -> bool:
        """
        提取PDF文本内容
        
        Returns:
            bool: 提取成功返回True，否则返回False
        """
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                self.page_count = len(pdf_reader.pages)
                
                # 提取元数据
                if pdf_reader.metadata:
                    self.metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'creation_date': pdf_reader.metadata.get('/CreationDate', ''),
                        'modification_date': pdf_reader.metadata.get('/ModDate', '')
                    }
                
                # 提取文本内容
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"\n--- 第 {page_num + 1} 页 ---\n")
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(f"提取第 {page_num + 1} 页时出错: {str(e)}")
                        continue
                
                self.text_content = '\n'.join(text_content)
                logger.info(f"成功提取PDF内容，共 {self.page_count} 页")
                return True
                
        except Exception as e:
            logger.error(f"提取PDF内容失败: {str(e)}")
            return False
    
    def analyze_content(self) -> Dict[str, any]:
        """
        分析PDF内容，提取关键信息
        
        Returns:
            Dict: 分析结果
        """
        if not self.text_content:
            return {}
        
        analysis = {
            'total_pages': self.page_count,
            'total_characters': len(self.text_content),
            'total_words': len(self.text_content.split()),
            'sections': [],
            'key_topics': [],
            'code_blocks': [],
            'urls': [],
            'important_concepts': []
        }
        
        # 查找章节标题（假设章节以数字开头或全大写）
        section_pattern = r'^(?:\d+\.|\#{1,3}|[A-Z][A-Z\s]{10,}$)'
        lines = self.text_content.split('\n')
        for line in lines:
            line = line.strip()
            if line and re.match(section_pattern, line):
                analysis['sections'].append(line)
        
        # 查找代码块（包含常见编程关键字的行）
        code_patterns = [
            r'def\s+\w+\(',
            r'class\s+\w+',
            r'import\s+\w+',
            r'from\s+\w+\s+import',
            r'pip\s+install',
            r'azure\.',
            r'\.py$',
            r'python\s+'
        ]
        
        for line in lines:
            line = line.strip()
            for pattern in code_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    analysis['code_blocks'].append(line)
                    break
        
        # 查找URL
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        urls = re.findall(url_pattern, self.text_content)
        analysis['urls'] = list(set(urls))
        
        # 查找Azure相关的重要概念
        azure_concepts = [
            'Azure Functions', 'Azure App Service', 'Azure Storage', 'Azure SQL',
            'Azure Cosmos DB', 'Azure Service Bus', 'Azure Event Hub', 'Azure Key Vault',
            'Azure Active Directory', 'Azure DevOps', 'Azure CLI', 'ARM Templates',
            'Deployment', 'Authentication', 'Authorization', 'Monitoring', 'Logging',
            'Scaling', 'Performance', 'Security', 'Best Practices'
        ]
        
        for concept in azure_concepts:
            if concept.lower() in self.text_content.lower():
                analysis['important_concepts'].append(concept)
        
        return analysis
    
    def generate_summary(self, analysis: Dict[str, any]) -> str:
        """
        生成文档摘要
        
        Args:
            analysis: 内容分析结果
            
        Returns:
            str: 文档摘要
        """
        summary_lines = []
        
        # 基本信息
        summary_lines.append("# Azure Developer Python 文档摘要\n")
        
        if self.metadata.get('title'):
            summary_lines.append(f"**文档标题**: {self.metadata['title']}")
        if self.metadata.get('author'):
            summary_lines.append(f"**作者**: {self.metadata['author']}")
        
        summary_lines.append(f"**页数**: {analysis['total_pages']} 页")
        summary_lines.append(f"**字符数**: {analysis['total_characters']:,}")
        summary_lines.append(f"**词数**: {analysis['total_words']:,}")
        
        # 主要章节
        if analysis['sections']:
            summary_lines.append("\n## 主要章节")
            for section in analysis['sections'][:10]:  # 只显示前10个章节
                summary_lines.append(f"- {section}")
        
        # 重要概念
        if analysis['important_concepts']:
            summary_lines.append("\n## 涉及的Azure概念")
            for concept in sorted(set(analysis['important_concepts'])):
                summary_lines.append(f"- {concept}")
        
        # 代码示例
        if analysis['code_blocks']:
            summary_lines.append("\n## 代码示例数量")
            summary_lines.append(f"发现 {len(analysis['code_blocks'])} 个代码相关的行")
        
        # 参考链接
        if analysis['urls']:
            summary_lines.append("\n## 参考链接")
            for url in analysis['urls'][:5]:  # 只显示前5个链接
                summary_lines.append(f"- {url}")
        
        return '\n'.join(summary_lines)
    
    def extract_key_sections(self) -> Dict[str, str]:
        """
        提取关键章节内容
        
        Returns:
            Dict: 关键章节内容
        """
        sections = {}
        
        if not self.text_content:
            return sections
        
        # 定义要提取的关键章节模式
        key_sections = {
            'introduction': ['introduction', '简介', '概述', 'overview'],
            'setup': ['setup', 'installation', '安装', '配置', 'configuration'],
            'authentication': ['authentication', '认证', '身份验证', 'auth'],
            'deployment': ['deployment', '部署', 'deploy'],
            'best_practices': ['best practices', '最佳实践', 'best practice'],
            'troubleshooting': ['troubleshooting', '故障排除', '问题解决', 'issues'],
            'examples': ['examples', '示例', 'example', 'sample']
        }
        
        lines = self.text_content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # 检查是否是新的关键章节
            for section_key, keywords in key_sections.items():
                if any(keyword in line_lower for keyword in keywords):
                    # 保存前一个章节
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content)
                    
                    # 开始新章节
                    current_section = section_key
                    current_content = [line]
                    break
            else:
                # 继续当前章节
                if current_section:
                    current_content.append(line)
        
        # 保存最后一个章节
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections


def main():
    """主函数"""
    pdf_path = "docs/azure-developer-python.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF文件不存在: {pdf_path}")
        return
    
    print("开始处理PDF文档...")
    processor = PDFProcessor(pdf_path)
    
    # 提取文本内容
    if not processor.extract_text():
        print("提取PDF内容失败")
        return
    
    # 分析内容
    print("分析文档内容...")
    analysis = processor.analyze_content()
    
    # 生成摘要
    print("生成文档摘要...")
    summary = processor.generate_summary(analysis)
    
    # 提取关键章节
    print("提取关键章节...")
    key_sections = processor.extract_key_sections()
    
    # 创建notes目录（如果不存在）
    notes_dir = Path("notes")
    notes_dir.mkdir(exist_ok=True)
    
    # 保存摘要
    summary_file = notes_dir / "azure-developer-python-summary.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"摘要已保存至: {summary_file}")
    
    # 保存关键章节
    for section_name, content in key_sections.items():
        if content.strip():
            section_file = notes_dir / f"azure-{section_name}.md"
            with open(section_file, 'w', encoding='utf-8') as f:
                f.write(f"# {section_name.title()}\n\n")
                f.write(content)
            print(f"章节已保存至: {section_file}")
    
    # 保存完整文本（可选）
    full_text_file = notes_dir / "azure-developer-python-full-text.txt"
    with open(full_text_file, 'w', encoding='utf-8') as f:
        f.write(processor.text_content)
    print(f"完整文本已保存至: {full_text_file}")
    
    print(f"\n✅ PDF处理完成！")
    print(f"📊 文档统计:")
    print(f"   - 页数: {analysis['total_pages']}")
    print(f"   - 字符数: {analysis['total_characters']:,}")
    print(f"   - 词数: {analysis['total_words']:,}")
    print(f"   - 章节数: {len(analysis['sections'])}")
    print(f"   - Azure概念: {len(analysis['important_concepts'])}")


if __name__ == '__main__':
    main() 