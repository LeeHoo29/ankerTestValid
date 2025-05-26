# Troubleshooting

logging.DEBUG 通常用于故障排除的详细信息，其中包括异常的堆栈跟踪。  调试级别会自
动启用信息、警告和错误级别。  注意：如果还设置了
logging_enable=True ，则调试级别将包括敏感信息，如标头中的帐户密钥
和其他凭据。  确保保护这些日志，以避免危及安全性。import logging
# Set the logging level for all azure-storage-* libraries
logger = logging.getLogger( 'azure.storage' )
logger.setLevel(logging.INFO)
# Set the logging level for all azure-* libraries
logger = logging.getLogger( 'azure')
logger.setLevel(logging.ERROR)
print(
    f"Logger enabled for ERROR= {logger.isEnabledFor(logging.ERROR)} , "
    f"WARNING= {logger.isEnabledFor(logging.WARNING)} , "
    f"INFO={logger.isEnabledFor(logging.INFO)} , "
    f"DEBUG= {logger.isEnabledFor(logging.DEBUG)} "
)
ﾉ 展开表

--- 第 485 页 ---

日志记录级别 典型用法
logging.NO TSET 禁用所有日志记录。
每个级别的确切日志记录行为取决于相关的库。  有些库（如  azure.eventhub ）会执行大
量日志记录，而其他库则较少。
要检查某个库的确切日志记录，最好的方法是在 用于 Python 的  Azure SDK 源代码 中搜
索日志记录级别：
1. 在存储库文件夹中，导航到 “sdk” 文件夹 ，然后导航到所需特定服务的文件夹。
2. 在该文件夹中，搜索以下任何字符串：
_LOGGER.error
_LOGGER.warning
_LOGGER.info
_LOGGER.debug
要捕获日志记录输出，必须在代码中注册至少一个日志流处理程序：
Python